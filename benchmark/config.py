import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPO = Path(os.environ.get("MCP_BENCH_REPO", Path.home() / "AI-Projects" / "MCP_Blueprint"))
BLUEPRINT_BIN = str(REPO / ".venv" / "bin" / "blueprint")
SAKILA_DSN = os.environ.get("SAKILA_DSN", "postgresql://localhost:5432/sakila")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434/v1/chat/completions")
OLLAMA_NATIVE_URL = os.environ.get("OLLAMA_NATIVE_URL", "http://localhost:11434/api/chat")
RESULTS_DIR = ROOT / "results"
SCHEMA_DDL = (ROOT / "schema" / "sakila_ddl.sql").read_text()

MODELS = [
    {"name": "llama3.2:3b", "tier": "SLM"},
    {"name": "qwen2.5:3b", "tier": "SLM"},
    {"name": "qwen2.5:7b", "tier": "medium"},
    {"name": "llama3.1:8b", "tier": "medium"},
]

# Excluded local models (no tool-calling support via Ollama):
#   llama3:8b       -> Ollama API returns 400 "does not support tools"
#   qwen2.5-coder:7b -> no tool template; emits the JSON tool call as plain text

# Effective generation context: the /v1/chat/completions endpoint ignores
# options.num_ctx and reloads the model at the Ollama default (4096), which
# is what all cells actually run at. warm_up preloads at the same value so
# no mid-run reload happens.
NUM_CTX = 4096
TEMPERATURE = 0
SEED = 42
MAX_STEPS = 10
RESULT_ROWS = 50

APPROACH_A_SYSTEM = (
    "You are a database assistant for a DVD rental store. "
    "You can query the PostgreSQL 'sakila' database by calling the tool "
    "execute_sql(query), which runs a read-only SQL query and returns the "
    "column names and up to " + str(RESULT_ROWS) + " rows. "
    "Use the schema below to write correct, efficient SQL (join keys are "
    "declared as foreign keys). Return a concise, correct final answer in "
    "plain text.\n\n"
    "--- Database schema (PostgreSQL) ---\n"
    + SCHEMA_DDL
    + "\n\n--- Data notes ---\n"
    "- Names, titles and category names are stored in UPPERCASE in this "
    "database; when matching text that the user provides, compare "
    "case-insensitively (ILIKE or upper()).\n"
    "- Many-to-many relationships are modelled with junction tables: film "
    "and category are linked through the film_category junction table (the "
    "film table has no category_id column).\n"
)

# Prompt revision marker. v2 levels both interfaces with documented
# contracts: approach A gets the data/schema notes above, approach B gets
# the clarified tool descriptions in B_DESC_FIXES.
PROMPT_VERSION = "v2"

APPROACH_B_SYSTEM = (
    "You are a helpful assistant for a DVD rental store. You have access to "
    "tools to search customers, inspect a customer's rentals, search films "
    "and get film details. Use the tools to answer the user's question "
    "accurately. Return a concise, correct final answer in plain text."
)

# Documentation clarifications applied to the tool descriptions that the
# model sees in approach B ("B clarified"). The underlying server and SQL
# are untouched; only the prompt-level tool contract is made explicit, so
# the approach is not penalised by underspecified input semantics.
B_DESC_FIXES = {
    "search_customer": (
        " IMPORTANT: the 'name' parameter must be a single first or last "
        "name (for example 'Smith' or 'Tammy'). Do NOT pass a full name "
        "such as 'Tammy Sanders'."
    ),
    "search_films": (
        " IMPORTANT: 'category' is an exact match on the category name. "
        "Valid values: Action, Animation, Children, Classics, Comedy, "
        "Documentary, Drama, Family, Foreign, Games, Horror, Music, New, "
        "Sci-Fi, Sports, Travel. An unknown category name returns no results."
    ),
}

# Approach "Bv": the verticalized sakila pack (canonical example).  Domain
# logic (entity resolution, account assembly, recommendations, per-store
# stock) is pushed into the tools, which accept names and titles directly,
# so the model picks a tool instead of chaining several generic lookups.
# Approach B loads the frozen v1 baseline from packs_baseline/ instead.
APPROACH_BV_SYSTEM = (
    "You are a helpful assistant for a DVD rental store. You have access to "
    "a small set of domain tools: customer_account_summary(customer_name) "
    "returns a customer's account (contact info, home store, standing, how "
    "many rentals are open or overdue, and the list of films currently on "
    "loan, or 'NONE' if nothing is on loan); rental_history(customer_name) lists "
    "the films a customer has rented in the past with their status; "
    "recommend_films(customer_name, category, rating, count, in_stock_only) "
    "suggests popular films the customer has not already rented, optionally "
    "filtered by category and rating; film_stock(title) reports per-store "
    "availability, rating and length for a film; search_customer(name) finds "
    "customers by name. These tools accept names and titles directly, so you "
    "do not need to look up ids first. Call the most specific tool for the "
    "question and return a concise, correct final answer in plain text."
)

SYSTEM_PROMPTS = {"A": APPROACH_A_SYSTEM, "B": APPROACH_B_SYSTEM, "Bv": APPROACH_BV_SYSTEM}
