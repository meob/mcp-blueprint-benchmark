# MCP Blueprint Benchmark

A reproducible benchmark harness that compares **MCP server design approaches**
for LLM agents. The scenario is a DVD rental store (PostgreSQL `sakila`
database) served to local models via [Ollama](https://ollama.com).

The harness evaluates how well an agent answers real storefront questions when
the same backend capability is exposed through different tool designs:

| Approach | Design | Tool surface |
| --- | --- | --- |
| **A** | Raw SQL | A single `execute_sql` tool; the database schema DDL and data notes live in the system prompt |
| **B** | Generic pack | A blueprint-pack MCP server exposing generic tools (`search_customer`, `search_films`, `get_customer_rentals`, `get_film`) |
| **Bv** | Verticalized pack | The canonical verticalized pack: domain tools that accept names and titles directly (`customer_account_summary`, `recommend_films`, `film_stock`, ...) |

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
  calling (defaults: `llama3.2:3b`, `qwen2.5:3b`, `qwen2.5:7b`, `llama3.1:8b`)
- The [MCP Blueprint](https://github.com/) server repo (for approaches B and Bv),
  built with the `blueprint` CLI on PATH or referenced via `MCP_BENCH_REPO`

## Setup

```bash
uv sync
ollama pull llama3.2:3b
ollama pull qwen2.5:3b
ollama pull qwen2.5:7b
ollama pull llama3.1:8b
```

Environment variables (all optional, sane defaults in `benchmark/config.py`):

| Variable | Default | Purpose |
| --- | --- | --- |
| `SAKILA_DSN` | `postgresql://meo@localhost:5432/sakila` | Database connection string |
| `OLLAMA_URL` | `http://localhost:11434/v1/chat/completions` | OpenAI-compatible endpoint |
| `OLLAMA_NATIVE_URL` | `http://localhost:11434/api/chat` | Native endpoint (warm-up) |
| `MCP_BENCH_REPO` | `~/AI-Projects/MCP_Blueprint` | Path to the MCP Blueprint repo (B/Bv) |

## Usage

```bash
# Smoke test (2 models, 3 tasks, 2 runs)
uv run python -m benchmark.run --pilot

# Full matrix
uv run python -m benchmark.run

# Targeted run, resuming previously completed cells
uv run python -m benchmark.run --models llama3.2:3b --approaches A B --tasks find_customer good_standing_recommend --runs 5 --resume
```

Options: `--models`, `--approaches {A,B,Bv}`, `--tasks`, `--runs`, `--resume`, `--pilot`.

## Repository layout

```
benchmark/            Harness: agent loop, tasks, gold answers, report, servers
config/               Blueprint server config for the frozen baseline pack
packs_baseline/       Frozen v1 sakila pack (SQL + tool contracts) for approach B
schema/               sakila DDL used to seed approach A's system prompt
results/              Generated run output (git-ignored)
results_as_shipped/   Frozen snapshot of an earlier run
```

## License

Apache License 2.0 — see [LICENSE](LICENSE).
