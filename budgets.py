"""
budgets.py — Local budget management for the Personal Expense Tracker.
Budgets are stored in budgets.json (user preferences, not DB data).
"""

import json
import os
from datetime import date

BUDGETS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "budgets.json")


# ── I/O helpers ──────────────────────────────────────────────────────────────

def load_budgets() -> dict:
    """Return {category: monthly_limit_float} from budgets.json."""
    if not os.path.exists(BUDGETS_FILE):
        return {}
    with open(BUDGETS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(budgets: dict):
    with open(BUDGETS_FILE, "w", encoding="utf-8") as f:
        json.dump(budgets, f, indent=2)


def save_budget(category: str, limit: float):
    """Upsert a monthly budget limit for the given category."""
    budgets = load_budgets()
    budgets[category.strip().title()] = round(limit, 2)
    _save(budgets)


def delete_budget(category: str) -> bool:
    """Remove a budget entry. Returns True if it existed."""
    budgets = load_budgets()
    key = category.strip().title()
    if key in budgets:
        del budgets[key]
        _save(budgets)
        return True
    return False


# ── Report ───────────────────────────────────────────────────────────────────

def _get_monthly_category_totals(month: str) -> dict:
    """Return {category: total} for expenses in the given YYYY-MM month."""
    from config import supabase

    year, mon = int(month[:4]), int(month[5:7])
    start = f"{month}-01"
    if mon == 12:
        end_exclusive = f"{year + 1}-01-01"
    else:
        end_exclusive = f"{year}-{mon + 1:02d}-01"

    response = (
        supabase.table("expenses")
        .select("amount, category")
        .gte("date", start)
        .lt("date", end_exclusive)
        .execute()
    )
    rows = response.data or []
    totals: dict[str, float] = {}
    for row in rows:
        cat = row["category"]
        totals[cat] = totals.get(cat, 0.0) + float(row["amount"])
    return totals


def get_budget_vs_actual(month: str | None = None) -> list[dict]:
    """
    Cross-reference budgets with DB spending for 'month' (YYYY-MM).
    Returns list of dicts: {category, budget, actual, pct, status}
    where status is 'ok' | 'warning' (>=80%) | 'over' (>=100%).
    """
    if month is None:
        month = date.today().strftime("%Y-%m")

    budgets = load_budgets()
    if not budgets:
        return []

    actual_map = _get_monthly_category_totals(month)

    report = []
    for cat, limit in budgets.items():
        actual = actual_map.get(cat, 0.0)
        pct = (actual / limit * 100) if limit > 0 else 0.0
        if pct >= 100:
            status = "over"
        elif pct >= 80:
            status = "warning"
        else:
            status = "ok"
        report.append({
            "category": cat,
            "budget": limit,
            "actual": round(actual, 2),
            "pct": round(pct, 1),
            "status": status,
        })

    return sorted(report, key=lambda x: x["pct"], reverse=True)
