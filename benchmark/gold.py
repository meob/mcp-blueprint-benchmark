import psycopg
from jinja2 import Template

from .config import ROOT, SAKILA_DSN

# Baseline sakila pack (v1) is frozen inside this repository so approach A/B
# scoring stays reproducible even though the canonical pack in the main repo
# has since been replaced by the verticalized one.
PACK_SQL = ROOT / "packs_baseline" / "sakila" / "sql"


def run_pack_sql(sql_name, params):
    sql = (PACK_SQL / f"{sql_name}.sql").read_text()
    rendered = Template(sql).render({k: v for k, v in params.items() if v is not None})
    with psycopg.connect(SAKILA_DSN) as conn:
        with conn.cursor() as cur:
            cur.execute(rendered, params)
            cols = [d.name for d in cur.description]
            rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    return rows


def search_films(title=None, category=None, rating=None):
    return run_pack_sql(
        "search_films",
        {"title": title, "category": category, "rating": rating},
    )


def search_customer(name):
    return run_pack_sql("search_customer", {"name": name})


def get_customer_rentals(customer_id):
    return run_pack_sql("get_customer_rentals", {"customer_id": customer_id})


def get_film(film_id):
    return run_pack_sql("get_film", {"film_id": film_id})


def all_g():
    """Every G-rated film with its available copies (no popularity limit).

    Used as gold for tasks that accept *any* valid film, e.g. 'recommend a
    G-rated movie that is in stock', so a correct answer outside the
    top-20-by-popularity list is not rejected.
    """
    sql = """
    SELECT f.film_id,
           f.title,
           (SELECT COUNT(DISTINCT inv.inventory_id) FILTER (
                       WHERE NOT EXISTS (
                           SELECT 1
                           FROM rental r
                           WHERE r.inventory_id = inv.inventory_id
                             AND r.return_date IS NULL
                       ))
            FROM inventory inv
            WHERE inv.film_id = f.film_id) AS available_copies
    FROM film f
    WHERE f.rating::text = 'G'
    ORDER BY f.title;
    """
    with psycopg.connect(SAKILA_DSN) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            cols = [d.name for d in cur.description]
            return [dict(zip(cols, r)) for r in cur.fetchall()]
