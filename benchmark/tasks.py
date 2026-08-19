import re
from difflib import SequenceMatcher

from . import gold as G


def _up(s):
    return s.upper()


def _titles(rows):
    return [r["title"] for r in rows]


def _norm(s):
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def _token_present(token, text_tokens):
    if token in text_tokens:
        return True
    return any(SequenceMatcher(None, token, w).ratio() >= 0.72 for w in text_tokens)


def _distinct_matches(answer, titles):
    """Return gold titles referenced by the answer (tolerant of singulars,
    apostrophes and small typos: 'Clerks Angel' matches 'CLERKS ANGELS')."""
    an = _norm(answer)
    tokens = an.split()
    found = set()
    for t in titles:
        tn = _norm(t)
        if tn and tn in an:
            found.add(t)
            continue
        words = tn.split()
        if len(words) >= 2 and all(_token_present(w, tokens) for w in words[:2]):
            found.add(t)
    return sorted(found)


def check(name, passed, detail=""):
    return {"name": name, "passed": bool(passed), "detail": detail}


def tool_called(run, name):
    return any(t["tool"] == name for t in run["trace"])


def tool_order(run, names):
    called = [t["tool"] for t in run["trace"] if t["tool"] in names]
    return called[: len(names)] == names


ACCOUNT_TOOLS = ("customer_account_summary", "get_customer_rentals", "rental_history")


def any_account_tool(run):
    return any(tool_called(run, t) for t in ACCOUNT_TOOLS)


def account_workflow(run, approach):
    if approach == "B":
        return any_account_tool(run)
    return (
        tool_order(run, ["search_customer", "customer_account_summary"])
        or tool_order(run, ["search_customer", "get_customer_rentals"])
        or (tool_called(run, "search_customer") and any_account_tool(run))
    )


def rec_workflow(run, approach):
    if approach == "B":
        return tool_called(run, "recommend_films")
    return tool_order(run, ["search_customer", "recommend_films"])


TASKS = [
    {
        "id": "find_customer",
        "prompt": "Find the customer whose last name is Smith. Report the customer's full name and customer ID.",
    },
    {
        "id": "rental_history",
        "prompt": "Mary Smith wants to know what she has rented. What films has she rented, and does she currently have any rentals outstanding?",
    },
    {
        "id": "good_standing_recommend",
        "prompt": "Check whether customer Maria Miller has any overdue rentals. If she is in good standing, recommend two Sci-Fi movies.",
    },
    {
        "id": "overdue_report",
        "prompt": "Check whether customer Tammy Sanders has any overdue rentals. If she does, list the films she still has to return.",
    },
    {
        "id": "recommend_category",
        "prompt": "Recommend three popular Family movies for a family movie night.",
    },
    {
        "id": "recommend_rating",
        "prompt": "Recommend two movies rated G, suitable for all ages.",
    },
    {
        "id": "film_details",
        "prompt": "Tell me about the movie 'Goodfellas Salute': its rating, its length in minutes, and how many copies are available.",
    },
    {
        "id": "avoid_on_loan",
        "prompt": "Customer Tammy Sanders is at the counter right now. Recommend one Science Fiction movie that she is not currently renting.",
    },
    {
        "id": "not_found",
        "prompt": "Find the customer whose last name is Doe.",
    },
    {
        "id": "customer_workflow",
        "prompt": "A customer named Jennifer Davis is asking about her account. Check her rental situation and then recommend a Documentary movie she might enjoy.",
    },
    {
        "id": "upsell_seen",
        "prompt": "Customer Kelly Torres enjoyed the Science Fiction movies she has rented before. Recommend two other popular Science Fiction movies that she has NOT rented before.",
    },
    {
        "id": "return_verify",
        "prompt": "Customer Mary Smith says she has returned everything she rented. Verify from the records: does she still have any rentals on loan? If so, list the film titles.",
    },
    {
        "id": "store_availability",
        "prompt": "A customer at Store 2 is asking for 'Goodfellas Salute'. How many copies are available, and is it in stock at Store 2?",
    },
    {
        "id": "g_available",
        "prompt": "Recommend a G-rated movie that is currently available in stock for a family movie night.",
    },
    {
        "id": "service_case",
        "prompt": "Customer Tammy Sanders is calling about late fees. Check her account: which films are currently on loan, which of those are overdue, and what is her home store so the store can reach out to her?",
    },
    {
        "id": "rental_empty",
        "prompt": "Show me the rental history for customer ID 9999.",
    },
    {
        "id": "not_rented",
        "prompt": "Which Science Fiction movies has Mary Smith NOT rented before?",
    },
]

TASK_IDS = [t["id"] for t in TASKS]


def compute_gold(task_id):
    if task_id == "find_customer":
        return {"customers": G.search_customer("Smith"), "last": "SMITH"}
    if task_id == "rental_history":
        return {"rentals": G.get_customer_rentals(1)}
    if task_id == "good_standing_recommend":
        return {"customer": G.search_customer("Miller")[0], "rentals": G.get_customer_rentals(7), "scifi": G.search_films(category="Sci-Fi")}
    if task_id == "overdue_report":
        return {"customer": G.search_customer("Sanders")[0], "rentals": G.get_customer_rentals(75)}
    if task_id == "recommend_category":
        return {"family": G.search_films(category="Family")}
    if task_id == "recommend_rating":
        return {"g": G.all_g()}
    if task_id == "film_details":
        return {"film": G.get_film(369)}
    if task_id == "avoid_on_loan":
        return {"customer": G.search_customer("Sanders")[0], "rentals": G.get_customer_rentals(75), "scifi": G.search_films(category="Sci-Fi")}
    if task_id == "not_found":
        return {"customers": G.search_customer("Doe")}
    if task_id == "customer_workflow":
        return {"customer": G.search_customer("Davis")[0], "rentals": G.get_customer_rentals(6), "doc": G.search_films(category="Documentary")}
    if task_id == "upsell_seen":
        return {
            "customer": G.search_customer("Torres")[0],
            "seen": G.get_customer_rentals(67),
            "scifi": G.search_films(category="Sci-Fi"),
        }
    if task_id == "return_verify":
        return {"customer": G.search_customer("Smith")[0], "rentals": G.get_customer_rentals(1)}
    if task_id == "store_availability":
        return {"film": G.get_film(369)[0]}
    if task_id == "g_available":
        return {"g": G.all_g()}
    if task_id == "service_case":
        return {"customer": G.search_customer("Sanders")[0], "rentals": G.get_customer_rentals(75)}
    if task_id == "rental_empty":
        return {"rentals": []}
    if task_id == "not_rented":
        return {"customer": G.search_customer("Smith")[0], "rentals": G.get_customer_rentals(1), "scifi": G.search_films(category="Sci-Fi")}
    raise KeyError(task_id)


def run_checks(task_id, run, gold):
    answer = run["final_answer"]
    approach = run["approach"]
    checks = []

    if task_id == "find_customer":
        checks.append(check("tool_used", tool_called(run, "search_customer") or tool_called(run, "execute_sql")))
        checks.append(check("customer_found", "SMITH" in _up(answer), answer[:120]))
        checks.append(check("customer_id", re.search(r"\bcustomer\s*(?:id|#|number)\s*[:=]?\s*1\b", _up(answer)) is not None or "MARY SMITH" in _up(answer), answer[:120]))

    elif task_id == "rental_history":
        checks.append(check("tool_used", any_account_tool(run) or tool_called(run, "execute_sql")))
        titles = _titles(gold["rentals"])
        matched = _distinct_matches(answer, titles)
        checks.append(check("lists_films", len(matched) >= 3, f"{len(matched)} matched"))
        has_open = any(r["status"] in ("active", "overdue") for r in gold["rentals"])
        if has_open:
            checks.append(check("mentions_outstanding", re.search(r"still (?:has|have|on|renting|holding|checked? out)|outstanding|not returned|on loan|currently rented|hasn'?t returned", answer, re.I) is not None, answer[:120]))
        else:
            checks.append(check("mentions_all_returned", re.search(r"all returned|nothing (?:outstanding|on loan|pending)|no (?:outstanding|open|active)|returned everything", answer, re.I) is not None, answer[:120]))

    elif task_id == "good_standing_recommend":
        checks.append(check("tool_used", tool_called(run, "search_films") or tool_called(run, "recommend_films") or any_account_tool(run) or tool_called(run, "execute_sql")))
        checks.append(check("standing_reported", re.search(r"good standing|no overdue|not overdue|no late|no outstanding|in good|clear|no issues|all clear|no pending", answer, re.I) is not None, answer[:120]))
        scifi = _titles(gold["scifi"])
        matched = _distinct_matches(answer, scifi)
        checks.append(check("two_scifi", len(matched) >= 2, f"{matched[:5]}"))
        if approach in ("B", "C"):
            checks.append(check("workflow", account_workflow(run, approach)))

    elif task_id == "overdue_report":
        checks.append(check("tool_used", any_account_tool(run) or tool_called(run, "execute_sql")))
        checks.append(check("overdue_stated", re.search(r"overdue|late|past due", answer, re.I) is not None, answer[:120]))
        open_titles = _titles([r for r in gold["rentals"] if r["status"] in ("active", "overdue")])
        matched = _distinct_matches(answer, open_titles)
        checks.append(check("lists_open", len(matched) >= 2, f"{matched} of {open_titles}"))

    elif task_id == "recommend_category":
        checks.append(check("tool_used", tool_called(run, "search_films") or tool_called(run, "recommend_films") or tool_called(run, "execute_sql")))
        family = _titles(gold["family"])
        matched = _distinct_matches(answer, family)
        checks.append(check("three_family", len(matched) >= 3, f"{matched[:5]}"))

    elif task_id == "recommend_rating":
        checks.append(check("tool_used", tool_called(run, "search_films") or tool_called(run, "recommend_films") or tool_called(run, "execute_sql")))
        g = _titles(gold["g"])
        matched = _distinct_matches(answer, g)
        checks.append(check("two_g", len(matched) >= 2, f"{matched[:5]}"))

    elif task_id == "film_details":
        checks.append(check("tool_used", tool_called(run, "get_film") or tool_called(run, "search_films") or tool_called(run, "film_stock") or tool_called(run, "execute_sql")))
        checks.append(check("rating_pg", re.search(r"\bPG\b", answer) is not None, answer[:120]))
        checks.append(check("length_56", re.search(r"\b56\b\s*(?:min(?:ute)?s?|m\b|minutes?)?", _up(answer)) is not None, answer[:120]))
        checks.append(check("availability", re.search(r"available|in stock|on the shelf", answer, re.I) is not None, answer[:120]))

    elif task_id == "avoid_on_loan":
        checks.append(check("tool_used", tool_called(run, "search_films") or tool_called(run, "recommend_films") or tool_called(run, "execute_sql")))
        open_titles = {_up(t) for t in _titles([r for r in gold["rentals"] if r["status"] in ("active", "overdue")])}
        scifi = _titles(gold["scifi"])
        allowed = [t for t in scifi if _up(t) not in open_titles]
        matched = _distinct_matches(answer, allowed)
        checks.append(check("not_on_loan", len(matched) >= 1, f"{matched[:5]}"))
        if approach in ("B", "C"):
            checks.append(check("checked_rentals", tool_called(run, "get_customer_rentals") or rec_workflow(run, approach)))

    elif task_id == "not_found":
        checks.append(check("tool_used", tool_called(run, "search_customer") or tool_called(run, "execute_sql")))
        not_found_re = r"not found|no customer|no match|does not exist|no results|not in the database|couldn'?t find|could not find|no one"
        checks.append(check("not_found_stated", re.search(not_found_re, answer, re.I) is not None, answer[:120]))
        checks.append(check("no_fabrication", "DOE" not in _up(answer) or re.search(not_found_re, answer, re.I) is not None, answer[:120]))

    elif task_id == "customer_workflow":
        checks.append(check("tool_used", tool_called(run, "search_films") or tool_called(run, "recommend_films") or any_account_tool(run) or tool_called(run, "execute_sql")))
        checks.append(check("mentions_customer", "JENNIFER DAVIS" in _up(answer) or "DAVIS" in _up(answer), answer[:120]))
        doc = _titles(gold["doc"])
        matched = _distinct_matches(answer, doc)
        checks.append(check("documentary", len(matched) >= 1, f"{matched[:5]}"))
        if approach in ("B", "C"):
            checks.append(check("workflow", account_workflow(run, approach)))

    elif task_id == "upsell_seen":
        checks.append(check("tool_used", tool_called(run, "search_films") or tool_called(run, "recommend_films") or tool_called(run, "execute_sql")))
        scifi = _titles(gold["scifi"])
        seen = {_up(t) for t in _titles(gold["seen"])}
        allowed = [t for t in scifi if _up(t) not in seen]
        matched = _distinct_matches(answer, allowed)
        checks.append(check("two_unseen_scifi", len(matched) >= 2, f"{matched[:5]}"))
        if approach in ("B", "C"):
            checks.append(check("workflow", tool_order(run, ["search_customer", "get_customer_rentals"]) or rec_workflow(run, approach)))

    elif task_id == "return_verify":
        checks.append(check("tool_used", any_account_tool(run) or tool_called(run, "execute_sql")))
        open_titles = [r for r in gold["rentals"] if r["status"] in ("active", "overdue")]
        if open_titles:
            checks.append(check("has_outstanding", re.search(r"still (?:has|have|on|renting|holding|checked? out)|outstanding|not returned|on loan|hasn'?t returned|does not appear", answer, re.I) is not None, answer[:120]))
        else:
            checks.append(check("all_clear", re.search(r"no (?:rentals?|films?|items?|outstanding|open|active|loans?) (?:on loan|outstanding|pending|active)|has returned|all clear|nothing (?:on loan|outstanding|pending)|does ?not have any|doesn'?t have any", answer, re.I) is not None, answer[:120]))
        if approach in ("B", "C"):
            checks.append(check("workflow", account_workflow(run, approach)))

    elif task_id == "store_availability":
        checks.append(check("tool_used", tool_called(run, "get_film") or tool_called(run, "film_stock") or tool_called(run, "execute_sql")))
        checks.append(check("title_mentioned", "GOODFELLAS" in _up(answer), answer[:120]))
        m = re.search(r"Store 2: (\d+) available", gold["film"]["store_availability"])
        count = m.group(1) if m else "?"
        checks.append(check("store2_stock", "STORE 2" in _up(answer) and count in answer, f"store2 count={count}"))
        checks.append(check("availability", re.search(r"available|in stock|on the shelf", answer, re.I) is not None, answer[:120]))

    elif task_id == "g_available":
        checks.append(check("tool_used", tool_called(run, "search_films") or tool_called(run, "recommend_films") or tool_called(run, "execute_sql")))
        g = _titles(gold["g"])
        matched = _distinct_matches(answer, g)
        checks.append(check("one_g", len(matched) >= 1, f"{matched[:5]}"))
        in_stock = [r["title"] for r in gold["g"] if r["available_copies"] > 0]
        matched_stock = _distinct_matches(answer, in_stock)
        checks.append(check("in_stock", len(matched_stock) >= 1, f"{matched_stock[:5]}"))

    elif task_id == "service_case":
        checks.append(check("tool_used", any_account_tool(run) or tool_called(run, "execute_sql")))
        open_titles = _titles([r for r in gold["rentals"] if r["status"] in ("active", "overdue")])
        matched = _distinct_matches(answer, open_titles)
        checks.append(check("lists_open", len(matched) >= 2, f"{matched} of {open_titles}"))
        checks.append(check("overdue_stated", re.search(r"overdue|late|past due", answer, re.I) is not None, answer[:120]))
        checks.append(check("home_store", re.search(r"STORE[^0-9]{0,5}2", _up(answer)) is not None or "CHANGHWA" in _up(answer), answer[:120]))
        if approach in ("B", "C"):
            checks.append(check("workflow", account_workflow(run, approach)))

    elif task_id == "rental_empty":
        checks.append(check("tool_used", any_account_tool(run) or tool_called(run, "execute_sql")))
        not_found_re = r"not found|no customer|no match|does not exist|no results|no rentals|no records|doesn'?t exist|couldn'?t find|no one"
        checks.append(check("no_customer", re.search(not_found_re, answer, re.I) is not None, answer[:120]))
        checks.append(check("no_fabrication", not re.search(r"rented|film|movie|title", answer, re.I) or re.search(not_found_re, answer, re.I) is not None, answer[:120]))

    elif task_id == "not_rented":
        checks.append(check("tool_used", tool_called(run, "search_films") or tool_called(run, "recommend_films") or tool_called(run, "execute_sql")))
        scifi = _titles(gold["scifi"])
        seen = {_up(t) for t in _titles(gold["rentals"])}
        not_seen = [t for t in scifi if _up(t) not in seen]
        matched = _distinct_matches(answer, not_seen)
        checks.append(check("two_unseen_scifi", len(matched) >= 2, f"{matched[:5]}"))
        if approach in ("B", "C"):
            checks.append(check("workflow", tool_order(run, ["search_customer", "get_customer_rentals"]) or rec_workflow(run, approach)))

    score = sum(1 for c in checks if c["passed"]) / len(checks) if checks else 0.0
    return checks, round(score, 3)
