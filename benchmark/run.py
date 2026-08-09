import argparse
import asyncio
import json
import subprocess
import time
from datetime import datetime, timezone

import psycopg

from . import gold as G
from .agent_loop import run_agent, warm_up
from .config import (
    APPROACH_A_SYSTEM,
    APPROACH_B_SYSTEM,
    APPROACH_BV_SYSTEM,
    MODELS,
    MAX_STEPS,
    NUM_CTX,
    OLLAMA_URL,
    PROMPT_VERSION,
    REPO,
    RESULTS_DIR,
    SAKILA_DSN,
    SEED,
    TEMPERATURE,
)
from .servers import ApproachAEnv, ApproachBEnv, ApproachBvEnv
from .tasks import TASK_IDS, TASKS, compute_gold, run_checks

ENVS = {"A": ApproachAEnv, "B": ApproachBEnv, "Bv": ApproachBvEnv}
SYSTEMS = {"A": APPROACH_A_SYSTEM, "B": APPROACH_B_SYSTEM, "Bv": APPROACH_BV_SYSTEM}


def db_fingerprint():
    with psycopg.connect(SAKILA_DSN) as conn:
        with conn.cursor() as cur:
            out = {}
            for name, q in {
                "customers": "SELECT count(*) FROM customer",
                "films": "SELECT count(*) FROM film",
                "rentals": "SELECT count(*) FROM rental",
                "max_rental_id": "SELECT max(rental_id) FROM rental",
            }.items():
                cur.execute(q)
                out[name] = cur.fetchone()[0]
    return out


def repo_sha():
    try:
        return subprocess.check_output(
            ["git", "-C", str(REPO), "rev-parse", "HEAD"], text=True
        ).strip()
    except Exception:
        return "n/a"


def ollama_version():
    try:
        return subprocess.check_output(["ollama", "--version"], text=True).strip()
    except Exception:
        return "n/a"


async def main(args):
    models = args.models or [m["name"] for m in MODELS]
    approaches = args.approaches or ["A", "B"]
    tasks = args.tasks or TASK_IDS
    reps = args.runs

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    prev = {}
    if (RESULTS_DIR / "manifest.json").exists():
        prev = json.loads((RESULTS_DIR / "manifest.json").read_text())

    def _union(a, b):
        seen, out = set(), []
        for x in list(a) + list(b):
            if x not in seen:
                seen.add(x)
                out.append(x)
        return out

    manifest = {
        "created": datetime.now(timezone.utc).isoformat(),
        "ollama": ollama_version(),
        "repo_sha": repo_sha(),
        "db_fingerprint": db_fingerprint(),
        "sakila_dsn": SAKILA_DSN,
        "ollama_url": OLLAMA_URL,
        "temperature": TEMPERATURE,
        "seed": SEED,
        "num_ctx": NUM_CTX,
        "max_steps": MAX_STEPS,
        "prompt_version": PROMPT_VERSION,
        "models": _union(prev.get("models", []), models),
        "approaches": _union(prev.get("approaches", []), approaches),
        "tasks": _union(prev.get("tasks", []), tasks),
        "runs_per_cell": reps,
        "task_prompts": {t["id"]: t["prompt"] for t in TASKS},
    }
    (RESULTS_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2))

    golds = {t: compute_gold(t) for t in tasks}

    envs = {}
    for a in approaches:
        env = ENVS[a]()
        env.system_prompt = SYSTEMS[a]
        envs[a] = await env.__aenter__()
        print(f"[env] approach {a}: tools={[t.name for t in envs[a].tools]}")

    counts = {"cells": 0, "errors": 0, "skipped": 0}
    t_start = time.perf_counter()
    try:
        for model in models:
            await warm_up(model)
            for a in approaches:
                env = envs[a]
                for task in tasks:
                    for k in range(1, reps + 1):
                        out_dir = RESULTS_DIR / model / a
                        out_path = out_dir / f"{task}__r{k}.json"
                        if args.resume and out_path.exists():
                            counts["skipped"] += 1
                            print(f"[run] {model} {a} {task} r{k}: skipped (already done)")
                            continue
                        counts["cells"] += 1
                        start = time.perf_counter()
                        record = await run_agent(model, env, next(t for t in TASKS if t["id"] == task)["prompt"])
                        record["run_id"] = f"{model}__{a}__{task}__r{k}"
                        record["timestamp"] = datetime.now(timezone.utc).isoformat()
                        record["model"] = model
                        record["tier"] = next(m["tier"] for m in MODELS if m["name"] == model)
                        record["approach"] = a
                        record["task_id"] = task
                        record["repetition"] = k
                        record["prompt_version"] = PROMPT_VERSION
                        record["desc_fixes"] = list(env.desc_fixes.keys()) if env.desc_fixes else None
                        record["system_prompt"] = env.system_prompt
                        record["user_prompt"] = next(t for t in TASKS if t["id"] == task)["prompt"]
                        record["wall_ms"] = round((time.perf_counter() - start) * 1000, 1)
                        record["checks"], record["score"] = run_checks(task, record, golds[task])
                        if record["score"] < 1.0 or record["error"]:
                            counts["errors"] += 1
                        out_dir = RESULTS_DIR / model / a
                        out_dir.mkdir(parents=True, exist_ok=True)
                        (out_dir / f"{task}__r{k}.json").write_text(json.dumps(record, indent=2, default=str))
                        print(
                            f"[run] {model} {a} {task} r{k}: score={record['score']} steps={record['steps']} "
                            f"tokens={record['tokens']['total']} ms={record['latency_ms']:.0f} err={record['error'] or '-'}"
                        )
    finally:
        for env in envs.values():
            await env.__aexit__(None, None, None)

    elapsed = time.perf_counter() - t_start
    print(
        f"\ndone: {counts['cells']} cells in {elapsed/60:.1f} min, "
        f"{counts['errors']} non-perfect, {counts['skipped']} skipped"
    )


def parse_args():
    p = argparse.ArgumentParser(description="Sakila MCP benchmark")
    p.add_argument("--models", nargs="*", default=None)
    p.add_argument("--approaches", nargs="*", default=None, choices=["A", "B", "Bv"])
    p.add_argument("--tasks", nargs="*", default=None)
    p.add_argument("--runs", type=int, default=3)
    p.add_argument("--resume", action="store_true", help="skip cells already written to results/")
    p.add_argument("--pilot", action="store_true", help="small matrix for a smoke test")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.pilot:
        args.models = args.models or [MODELS[0]["name"], MODELS[-1]["name"]]
        args.approaches = args.approaches or ["A", "B"]
        args.tasks = args.tasks or ["find_customer", "good_standing_recommend", "not_found"]
        args.runs = min(args.runs, 2)
    asyncio.run(main(args))
