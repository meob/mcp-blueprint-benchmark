# MCP Blueprint Benchmark

A reproducible benchmark harness that compares **MCP server design approaches**
for LLM agents. The scenario is a DVD rental store (PostgreSQL `sakila`
database) served to local models via [Ollama](https://ollama.com).

The harness evaluates how well an agent answers real storefront questions when
the same backend capability is exposed through different tool designs:

| Approach | Design | Tool surface |
| --- | --- | --- |
| **A** | Raw SQL | A single `execute_sql` tool; the database schema DDL and data notes live in the system prompt |
| **B** | Verticalized pack | The canonical verticalized MCP-Blueprint pack: domain tools that accept names and titles directly (`customer_account_summary`, `recommend_films`, `film_stock`, ...) |
| **C** | Generic pack | A blueprint-pack MCP server exposing anti-pattern generic tools (`search_customer`, `search_films`, `get_customer_rentals`, `get_film`) |

## What it measures

For every (model × approach × task × repetition) cell the harness records:

- **Accuracy** — scored by a per-task rule set (`benchmark/tasks.py`) checked
  against gold answers computed directly from the database (`benchmark/gold.py`)
- **Tokens** — prompt / completion / total per cell
- **Latency** — wall-clock time, number of agent steps, tool calls

Results are written as per-cell JSON under `results/` and aggregated into
`summary.md`, `accuracy.csv`, `tokens.csv` and `latency.csv`. A frozen snapshot
of an earlier run lives in `results_as_shipped/`.

## Tasks

15 tasks (`benchmark/tasks.py`) covering the storefront workflow: finding
customers, rental history, overdue reports, good-standing checks,
recommendations by category/rating, per-store film stock, and refusal of
non-existent customers.

## Requirements

- Python ≥ 3.12 with [uv](https://docs.astral.sh/uv/)
- PostgreSQL with the [Sakila](https://www.postgresqltutorial.com/postgresql-sample-database/)
  sample database
- [Ollama](https://ollama.com) running locally with models that support tool
  calling (defaults: `llama3.2:3b`, `qwen2.5:3b`, `gemma2:2b`, `phi3:mini`,
  `qwen2.5:7b`, `llama3.1:8b`)
- The [MCP Blueprint](https://github.com/) server repo (for approaches B and C),
  built with the `blueprint` CLI on PATH or referenced via `MCP_BENCH_REPO`

## Setup

```bash
uv sync
ollama pull llama3.2:3b
ollama pull qwen2.5:3b
ollama pull gemma2:2b
ollama pull phi3:mini
ollama pull qwen2.5:7b
ollama pull llama3.1:8b
```

Environment variables (all optional, sane defaults in `benchmark/config.py`):

| Variable | Default | Purpose |
| --- | --- | --- |
| `SAKILA_DSN` | `postgresql://localhost:5432/sakila` | Database connection string |
| `OLLAMA_URL` | `http://localhost:11434/v1/chat/completions` | OpenAI-compatible endpoint |
| `OLLAMA_NATIVE_URL` | `http://localhost:11434/api/chat` | Native endpoint (warm-up) |
| `MCP_BENCH_REPO` | `~/AI-Projects/MCP_Blueprint` | Path to the MCP Blueprint repo (approaches B and C) |

## Usage

```bash
# Smoke test (2 models, 3 tasks, 2 runs)
uv run python -m benchmark.run --pilot

# Full matrix (810 cells: 6 models × 3 approaches × 15 tasks × 3 repetitions)
uv run python -m benchmark.run

# Targeted run, resuming previously completed cells
uv run python -m benchmark.run --models llama3.2:3b --approaches A B --tasks find_customer good_standing_recommend --runs 5 --resume

# Verification and validation
uv run python -m benchmark.verify  # Run verification checklist
uv run python -m benchmark.validate  # Validate results consistency
```

Options: `--models`, `--approaches {A,B,C}`, `--tasks`, `--runs`, `--resume`, `--pilot`.

## Benchmark Verification Checklist

Before incorporating results into the paper, complete these verification steps:

1. **Run full benchmark suite** (810 cells) to confirm current results
2. **Verify no regressions** from v0.5.1 changes
3. **Check all 15 tasks** scored correctly (spot-check edge cases)
4. **Validate token counts** are consistent across runs
5. **Confirm latency measurements** are stable
6. **Review results discrepancies** between `results/` and `results_as_shipped/`
7. **Consider additional models** for robustness (e.g., `gemma2:2b`, `phi3:mini`)

## Repository layout

```
benchmark/            Harness: agent loop, tasks, gold answers, report, servers
benchmark/verify.py   Verification checklist implementation
benchmark/validate.py Results validation and consistency checks
config/               Blueprint server config for the frozen baseline pack
packs_baseline/       Frozen v1 sakila pack (SQL + tool contracts) for approach C
schema/               sakila DDL used to seed approach A's system prompt
results/              Generated run output (git-ignored)
results_as_shipped/   Frozen snapshot of an earlier run
```

## License

Apache License 2.0 — see [LICENSE](LICENSE).
