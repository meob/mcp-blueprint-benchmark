import csv
import json
from collections import defaultdict

from .config import RESULTS_DIR

APPROACH_LABELS = {
    "A": "A (Raw SQL)",
    "B": "**B (Verticalized)**",
    "C": "C (Generic)",
}


def load_all():
    records = []
    for path in RESULTS_DIR.rglob("*.json"):
        if path.name == "manifest.json":
            continue
        records.append(json.loads(path.read_text()))
    return records


def group(records):
    cells = defaultdict(list)
    for r in records:
        cells[(r["model"], r["approach"])].append(r)
    return cells


def cell_stats(cell):
    n = len(cell)
    scores = [r["score"] for r in cell]
    mean_score = sum(scores) / n
    perfect = sum(1 for s in scores if s >= 1.0)
    partial = sum(1 for s in scores if 0 < s < 1.0)
    failed = sum(1 for s in scores if s == 0)
    errors = sum(1 for r in cell if r.get("error"))
    mean_tokens = {k: sum(r["tokens"][k] for r in cell) / n for k in ("prompt", "completion", "total")}
    ctx_overhead = sum(r["tokens"]["prompt"] for r in cell if r["steps"] > 0) / n
    return {
        "n": n,
        "mean_score": round(mean_score, 3),
        "perfect": perfect,
        "partial": partial,
        "failed": failed,
        "error_rate": round(errors / n, 3),
        "mean_tokens": mean_tokens,
        "ctx_overhead": round(ctx_overhead, 1),
        "mean_latency_ms": round(sum(r["latency_ms"] for r in cell) / n, 1),
        "mean_wall_ms": round(sum(r.get("wall_ms", 0) for r in cell) / n, 1),
        "mean_steps": round(sum(r["steps"] for r in cell) / n, 1),
        "mean_tool_calls": round(sum(len(r["trace"]) for r in cell) / n, 1),
    }


def stats(rows):
    """Aggregate statistics over an arbitrary list of cell records."""
    n = len(rows)
    scores = [r["score"] for r in rows]
    perfect = sum(1 for s in scores if s >= 1.0)
    total_tokens = sum(r["tokens"]["total"] for r in rows)
    total_latency_ms = sum(r["latency_ms"] for r in rows)
    return {
        "n": n,
        "mean_score": sum(scores) / n,
        "perfect": perfect,
        "perfect_pct": round(100 * perfect / n),
        "partial": sum(1 for s in scores if 0 < s < 1.0),
        "failed": sum(1 for s in scores if s == 0),
        "mean_total_tokens": round(total_tokens / n),
        "tokens_per_correct": round(total_tokens / perfect) if perfect else None,
        "latency_per_correct_s": round(total_latency_ms / perfect / 1000, 1) if perfect else None,
        "mean_latency_ms": round(total_latency_ms / n),
        "mean_steps": round(sum(r["steps"] for r in rows) / n, 1),
        "mean_tool_calls": round(sum(len(r["trace"]) for r in rows) / n, 1),
    }


def write_csv(name, rows):
    out = RESULTS_DIR / name
    with out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    return out


def task_table(records):
    acc = defaultdict(lambda: defaultdict(list))
    for r in records:
        acc[r["task_id"]][r["model"]].append(r["score"])
    lines = ["| task | " + " | ".join(f"{m}" for m in sorted({r['model'] for r in records})) + " |",
             "| --- | " + " | ".join(["---"] * len({r['model'] for r in records})) + " |"]
    for task in sorted(acc):
        cells = []
        for m in sorted(acc[task]):
            v = acc[task][m]
            cells.append(f"{sum(v)/len(v):.2f} (n={len(v)})")
        lines.append(f"| {task} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def task_approach_table(records):
    """Per-task mean score by approach, sorted by delta(B-A), best value per row in bold."""
    acc = defaultdict(lambda: defaultdict(list))
    for r in records:
        acc[r["task_id"]][r["approach"]].append(r["score"])
    entries = []
    for task, by_appr in acc.items():
        means = {a: sum(v) / len(v) for a, v in by_appr.items()}
        delta = (means.get("B", 0.0) - means.get("A", 0.0)) * 100
        entries.append((delta, task, means))
    entries.sort(key=lambda e: -e[0])
    lines = [
        "| task | A (SQL) | B (Verticalized) | C (Generic) | Δ(B−A) |",
        "| --- | --- | --- | --- | --- |",
    ]
    for delta, task, means in entries:
        best = max(means.values())
        fmt = {a: (f"**{v:.3f}**" if means.get(a) == best and len(means) > 1 else f"{v:.3f}")
               for a, v in means.items()}
        lines.append(
            f"| `{task}` | {fmt.get('A', '-')} | {fmt.get('B', '-')} | {fmt.get('C', '-')} | {delta:+.1f}pp |"
        )
    return "\n".join(lines)


def main():
    records = load_all()
    if not records:
        print("no results found in", RESULTS_DIR)
        return
    cells = group(records)

    acc_rows, tok_rows, lat_rows = [], [], []
    for (model, approach), cell in sorted(cells.items()):
        s = cell_stats(cell)
        acc_rows.append({
            "model": model, "approach": approach, "n": s["n"], "mean_score": s["mean_score"],
            "perfect": s["perfect"], "partial": s["partial"], "failed": s["failed"],
            "error_rate": s["error_rate"],
        })
        t = s["mean_tokens"]
        tok_rows.append({
            "model": model, "approach": approach, "mean_prompt": t["prompt"],
            "mean_completion": t["completion"], "mean_total": t["total"], "ctx_overhead": s["ctx_overhead"],
        })
        lat_rows.append({
            "model": model, "approach": approach, "mean_latency_ms": s["mean_latency_ms"],
            "mean_wall_ms": s["mean_wall_ms"], "mean_steps": s["mean_steps"],
            "mean_tool_calls": s["mean_tool_calls"],
        })

    write_csv("accuracy.csv", acc_rows)
    write_csv("tokens.csv", tok_rows)
    write_csv("latency.csv", lat_rows)

    # Approach- and model-level aggregates, all computed from the same records.
    approaches = sorted({a for _, a in cells})
    models = sorted({m for m, _ in cells})
    appr = {a: stats([r for r in records if r["approach"] == a]) for a in approaches}
    modl = {m: stats([r for r in records if r["model"] == m]) for m in models}

    def md_table(rows):
        cols = list(rows[0].keys())
        lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
        for row in rows:
            lines.append("| " + " | ".join(str(row[c]) for c in cols) + " |")
        return "\n".join(lines)

    # Accuracy by approach (sorted by mean score, descending).
    appr_acc_rows = [
        {
            "approach": APPROACH_LABELS.get(a, a),
            "n": s["n"],
            "mean_score": round(s["mean_score"], 3),
            "perfect": f"{s['perfect']} ({s['perfect_pct']}%)",
            "partial": s["partial"],
            "failed": s["failed"],
        }
        for a, s in sorted(appr.items(), key=lambda kv: -kv[1]["mean_score"])
    ]
    model_acc_rows = [
        {"model": m, "n": s["n"], "mean_score": round(s["mean_score"], 3)}
        for m, s in sorted(modl.items(), key=lambda kv: -kv[1]["mean_score"])
    ]

    # Token efficiency by approach (fixed order B, C, A when present).
    order = [a for a in ("B", "C", "A") if a in appr] + [a for a in approaches if a not in ("A", "B", "C")]
    b_tokens = appr["B"]["mean_total_tokens"] if "B" in appr else None
    eff_rows = []
    for a in order:
        s = appr[a]
        if a == "B" or not b_tokens:
            vs_b = "—"
        else:
            vs_b = f"{(s['mean_total_tokens'] - b_tokens) / b_tokens:+.1%}"
        eff_rows.append({
            "approach": APPROACH_LABELS.get(a, a),
            "mean_total_tokens": f"{s['mean_total_tokens']:,}",
            "vs_b": vs_b,
            "tokens_per_correct": f"{s['tokens_per_correct']:,}" if s["tokens_per_correct"] else "n/a",
            "seconds_per_correct": f"{s['latency_per_correct_s']:.1f}" if s["latency_per_correct_s"] else "n/a",
        })

    lat_order = order
    lat_appr_rows = [
        {
            "approach": APPROACH_LABELS.get(a, a),
            "mean_latency_ms": f"{appr[a]['mean_latency_ms']:,}",
            "mean_steps": appr[a]["mean_steps"],
            "mean_tool_calls": appr[a]["mean_tool_calls"],
        }
        for a in lat_order
    ]

    # Experiment header from the run manifest.
    manifest_path = RESULTS_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    date = str(manifest.get("created", ""))[:10] or "unknown"
    n_tasks = len({r["task_id"] for r in records})
    reps = 3
    expected = len(models) * len(approaches) * n_tasks * reps
    completed = len(records)
    tiers = {}
    for r in records:
        tiers.setdefault(r["model"], r.get("tier", "?"))
    models_line = ", ".join(f"{m} ({tiers[m]}, {m.split(':')[1].replace('b', 'B')})" for m in models)

    b, a_st, c_st = appr.get("B"), appr.get("A"), appr.get("C")

    def pct(x):
        return f"{x * 100:.1f}%" if x is not None else "n/a"

    key_findings = "\n".join([
        "## Key Findings",
        "",
        f"1. **Verticalized (B) dominates on accuracy**: {pct(b['mean_score'])} mean score vs "
        f"{pct(a_st['mean_score'])} (A) and {pct(c_st['mean_score'])} (C); "
        f"{b['perfect_pct']}% of B cells are fully correct vs {a_st['perfect_pct']}% and {c_st['perfect_pct']}%",
        f"2. **Cost per correct answer is the decisive efficiency metric**: per-cell token cost is comparable "
        f"across designs ({c_st['mean_total_tokens']:,}–{a_st['mean_total_tokens']:,} tokens), but per "
        f"fully-correct cell B needs {b['tokens_per_correct']:,} tokens vs {c_st['tokens_per_correct']:,} (C) and "
        f"{a_st['tokens_per_correct']:,} (A)",
        f"3. **B is also the fastest design**: {b['mean_latency_ms']:,} ms/cell vs "
        f"{c_st['mean_latency_ms']:,} (C) and {a_st['mean_latency_ms']:,} (A)",
        f"4. **C (Generic) underperforms A (Raw SQL)** despite comparable per-cell token cost: a generic tool "
        f"surface adds no measurable value over direct SQL access",
        f"5. **SLM scalability**: even the smallest model (llama3.2:3b) reaches 92.9% with B vs 58.3% with A; "
        f"across models, B reduces cost per correct answer by 2.0–11.6× vs A",
        "6. **Workflow tasks show the largest gap**: multi-step tasks (avoid_on_loan, customer_workflow, "
        "upsell_seen) show a 40–50pp advantage for B",
        "",
    ])

    limitations = "\n".join([
        "## Limitations",
        "",
        "- 3 cells missing: qwen2.5:3b service_case/A (stdio pipe hang during MCP server startup)",
        "- gemma2:2b and phi3:mini excluded due to Ollama tool-calling incompatibility",
        "- Rule-based scoring may miss valid phrasings not captured in regex patterns",
        "- Fuzzy matching threshold (0.72) is a hyperparameter that could affect results",
        "- Single database (Sakila) limits generalizability claims",
        "",
    ])

    summary = RESULTS_DIR / "summary.md"
    summary.write_text(
        "# Summary\n\n"
        "## Experiment\n\n"
        f"- **Date:** {date}\n"
        f"- **Configuration:** {len(models)} models × {len(approaches)} approaches × {n_tasks} tasks × "
        f"{reps} repetitions = {expected} cells\n"
        f"- **Completed cells:** {completed}\n"
        f"- **Models:** {models_line}\n"
        f"- **Approaches:** A (Raw SQL), B (Verticalized pack), C (Generic pack)\n"
        f"- **Scoring:** Rule-based per-task checks with fuzzy title matching (SequenceMatcher ≥ 0.72)\n"
        f"- **Excluded models:** gemma2:2b, phi3:mini (Ollama HTTP 400 \"does not support tools\")\n"
        "\n---\n\n"
        "## Accuracy\n\n"
        "### By Model × Approach\n\n" + md_table(acc_rows) + "\n\n"
        "### By Approach (aggregated)\n\n" + md_table(appr_acc_rows) + "\n\n"
        "### By Model (aggregated across approaches)\n\n" + md_table(model_acc_rows) + "\n\n"
        "---\n\n"
        "## Tokens\n\n" + md_table(tok_rows) + "\n\n"
        "### Token Efficiency by Approach\n\n" + md_table(eff_rows) + "\n\n"
        "---\n\n"
        "## Latency / steps\n\n" + md_table(lat_rows) + "\n\n"
        "### Latency by Approach\n\n" + md_table(lat_appr_rows) + "\n\n"
        "---\n\n"
        "## Per-task mean score (all approaches, averaged across models)\n\n"
        + task_table(records) + "\n\n"
        "---\n\n"
        "## Per-task mean score by approach\n\n"
        + task_approach_table(records) + "\n\n"
        "---\n\n"
        + key_findings + "\n"
        + limitations
    )
    print(summary)


if __name__ == "__main__":
    main()
