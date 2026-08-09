import csv
import json
from collections import defaultdict
from pathlib import Path

from .config import RESULTS_DIR

KEY = ("model", "approach")


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

    def md_table(rows):
        cols = list(rows[0].keys())
        lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
        for row in rows:
            lines.append("| " + " | ".join(str(row[c]) for c in cols) + " |")
        return "\n".join(lines)

    summary = RESULTS_DIR / "summary.md"
    summary.write_text(
        "# Summary\n\n"
        "## Accuracy\n\n" + md_table(acc_rows) + "\n\n"
        "## Tokens\n\n" + md_table(tok_rows) + "\n\n"
        "## Latency / steps\n\n" + md_table(lat_rows) + "\n\n"
        "## Per-task mean score (all approaches)\n\n" + task_table(records) + "\n"
    )
    print(summary)


if __name__ == "__main__":
    main()
