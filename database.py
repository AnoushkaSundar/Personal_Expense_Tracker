"""
database.py — All Supabase data access functions for the expense tracker.
"""

from config import supabase
from datetime import date


TABLE = "expenses"


def add_expense(amount: float, category: str, description: str, expense_date: str) -> dict:
    """Insert a new expense row and return it."""
    data = {
        "amount": amount,
        "category": category.strip().title(),
        "description": description.strip(),
        "date": expense_date,
    }
    response = supabase.table(TABLE).insert(data).execute()
    return response.data[0] if response.data else {}


def get_all_expenses() -> list:
    """Return all expenses ordered by date descending."""
    response = (
        supabase.table(TABLE)
        .select("*")
        .order("date", desc=True)
        .execute()
    )
    return response.data or []


def get_expenses_by_category(category: str) -> list:
    """Return expenses filtered by category (case-insensitive)."""
    response = (
        supabase.table(TABLE)
        .select("*")
        .ilike("category", category.strip())
        .order("date", desc=True)
        .execute()
    )
    return response.data or []


def get_expenses_by_date_range(start: str, end: str) -> list:
    """Return expenses whose date falls between start and end (inclusive, YYYY-MM-DD)."""
    response = (
        supabase.table(TABLE)
        .select("*")
        .gte("date", start)
        .lte("date", end)
        .order("date", desc=True)
        .execute()
    )
    return response.data or []


def get_all_categories() -> list[str]:
    """Return a sorted unique list of all category names."""
    response = supabase.table(TABLE).select("category").execute()
    cats = {row["category"] for row in (response.data or [])}
    return sorted(cats)


def get_total_spending() -> float:
    """Return the sum of all expense amounts."""
    response = supabase.table(TABLE).select("amount").execute()
    rows = response.data or []
    return round(sum(float(r["amount"]) for r in rows), 2)


def get_monthly_summary() -> list[dict]:
    """
    Return a list of dicts: [{month: 'YYYY-MM', total: float}]
    sorted chronologically.
    """
    response = supabase.table(TABLE).select("amount, date").execute()
    rows = response.data or []

    monthly: dict[str, float] = {}
    for row in rows:
        month = str(row["date"])[:7]          # 'YYYY-MM'
        monthly[month] = monthly.get(month, 0) + float(row["amount"])

    summary = [
        {"month": m, "total": round(t, 2)}
        for m, t in sorted(monthly.items())
    ]
    return summary


def get_spending_by_category() -> list[dict]:
    """
    Return a list of dicts: [{category: str, total: float}]
    sorted by total descending.
    """
    response = supabase.table(TABLE).select("amount, category").execute()
    rows = response.data or []

    cat_totals: dict[str, float] = {}
    for row in rows:
        cat = row["category"]
        cat_totals[cat] = cat_totals.get(cat, 0) + float(row["amount"])

    breakdown = [
        {"category": c, "total": round(t, 2)}
        for c, t in sorted(cat_totals.items(), key=lambda x: x[1], reverse=True)
    ]
    return breakdown


def delete_expense(expense_id: int) -> bool:
    """Delete a single expense row by its primary key. Returns True on success."""
    response = (
        supabase.table(TABLE)
        .delete()
        .eq("id", expense_id)
        .execute()
    )
    return bool(response.data)


def update_expense(expense_id: int, fields: dict) -> dict:
    """
    Update only the provided fields on the given expense row.
    Returns the updated row dict, or {} on failure.
    """
    response = (
        supabase.table(TABLE)
        .update(fields)
        .eq("id", expense_id)
        .execute()
    )
    return response.data[0] if response.data else {}
