import json
import os
import re

import psycopg
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("execute_sql")

DSN = os.environ.get("SAKILA_DSN", "postgresql://localhost:5432/sakila")
MAX_ROWS = int(os.environ.get("SAKILA_MAX_ROWS", "50"))

_START = re.compile(r"^\s*(SELECT|WITH|VALUES)\b", re.IGNORECASE)
_FORBIDDEN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|GRANT|REVOKE|COPY|LOCK|VACUUM|SET|CALL|DO|EXPLAIN|BEGIN|COMMIT)\b",
    re.IGNORECASE,
)


@mcp.tool()
def execute_sql(query: str) -> str:
    if not _START.match(query):
        return json.dumps({"error": "only read-only SELECT / WITH / VALUES queries are allowed"})
    if _FORBIDDEN.search(query):
        return json.dumps({"error": "the query contains a forbidden statement"})
    try:
        with psycopg.connect(DSN) as conn:
            conn.execute("SET default_transaction_read_only = on")
            with conn.cursor() as cur:
                cur.execute(query)
                if cur.description is None:
                    return json.dumps({"error": "query returned no rows"})
                cols = [d.name for d in cur.description]
                rows = [list(r) for r in cur.fetchmany(MAX_ROWS)]
    except Exception as exc:
        return json.dumps({"error": f"{type(exc).__name__}: {exc}"})
    return json.dumps({"columns": cols, "row_count": len(rows), "rows": rows}, default=str)


if __name__ == "__main__":
    mcp.run(transport="stdio")
