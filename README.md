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

## Results

**[Full benchmark results and analysis →](results/summary.md)**

Key findings (609 cells, 4 models × 3 approaches × 17 tasks × 3 reps):

| Approach | Mean Score | Perfect | Tokens | Latency |
| --- | --- | --- | --- | --- |
| **B (Verticalized)** | **93.9%** | 85% | 3,056 | 4.4s |
| A (Raw SQL) | 66.6% | 33% | 4,583 | 17.6s |
| C (Generic) | 60.5% | 31% | 3,287 | 6.4s |

Figures are available in [`figures/`](figures/) (PNG + PDF).

## What it measures

For every (model × approach × task × repetition) cell the harness records:

- **Accuracy** — scored by a per-task rule set (`benchmark/tasks.py`) checked
  against gold answers computed directly from the database (`benchmark/gold.py`)
- **Tokens** — prompt / completion / total per cell
- **Latency** — wall-clock time, number of agent steps, tool calls

Results are written as per-cell JSON under `results/` and aggregated into
`results/summary.md`. A frozen snapshot of an earlier run lives in
`results_as_shipped/`.

## Tasks

17 tasks (`benchmark/tasks.py`) covering the storefront workflow: finding
customers, rental history, overdue reports, good-standing checks,
recommendations by category/rating, per-store film stock, refusal of
non-existent customers, and negative queries.

## Models

### Included (tool-calling support)

| Model | Parameters | Tier | Notes |
| --- | --- | --- | --- |
| `llama3.2:3b` | 3B | SLM | Meta lightweight |
| `qwen2.5:3b` | 3B | SLM | Alibaba lightweight |
| `qwen2.5:7b` | 7B | Medium | Alibaba mid-range |
| `llama3.1:8b` | 8B | Medium | Meta mid-range |

### Excluded (no tool-calling support via Ollama)

| Model | Reason |
| --- | --- |
| `gemma2:2b` | Ollama HTTP 400: "does not support tools" |
| `phi3:mini` | Ollama HTTP 400: "does not support tools" |
| `llama3:8b` | Ollama HTTP 400: "does not support tools" |
| `qwen2.5-coder:7b` | No tool template; emits tool calls as plain text |

## Requirements

- Python ≥ 3.12 with [uv](https://docs.astral.sh/uv/)
- PostgreSQL with the [Sakila](https://www.postgresqltutorial.com/postgresql-sample-database/)
  sample database
- [Ollama](https://ollama.com) running locally with models that support tool
  calling
- The [MCP Blueprint](https://github.com/) server repo (for approaches B and C),
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
| `SAKILA_DSN` | `postgresql://localhost:5432/sakila` | Database connection string |
| `OLLAMA_URL` | `http://localhost:11434/v1/chat/completions` | OpenAI-compatible endpoint |
| `OLLAMA_NATIVE_URL` | `http://localhost:11434/api/chat` | Native endpoint (warm-up) |
| `MCP_BENCH_REPO` | `~/AI-Projects/MCP_Blueprint` | Path to the MCP Blueprint repo (approaches B and C) |

## Usage

```bash
# Smoke test (2 models, 3 tasks, 2 runs)
uv run python -m benchmark.run --pilot

# Full matrix (609 cells: 4 models × 3 approaches × 17 tasks × 3 repetitions)
uv run python -m benchmark.run

# Targeted run, resuming previously completed cells
uv run python -m benchmark.run --models llama3.2:3b --approaches A B --tasks find_customer good_standing_recommend --runs 5 --resume

# Verification and validation
uv run python -m benchmark.verify  # Run verification checklist
uv run python -m benchmark.validate  # Validate results consistency
```

Options: `--models`, `--approaches {A,B,C}`, `--tasks`, `--runs`, `--resume`, `--pilot`.

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
figures/              Charts and figures for the paper (PNG + PDF)
staff/                Internal notes and benchmark plans (git-ignored)
```

## License

Apache License 2.0 — see [LICENSE](LICENSE).
