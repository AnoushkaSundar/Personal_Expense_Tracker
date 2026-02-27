"""
export.py — CSV export helper for the Personal Expense Tracker.
"""

import csv
import os
from datetime import date


EXPORT_DIR = os.path.dirname(__file__)

FIELDNAMES = ["id", "date", "category", "amount", "description", "created_at"]


def export_to_csv(expenses: list, filepath: str | None = None) -> str:
    """
    Write a list of expense dicts to a CSV file.

    Args:
        expenses: list of dicts as returned by database.get_all_expenses()
        filepath:  explicit path; if None a timestamped name is used.

    Returns:
        Absolute path of the written file.
    """
    if filepath is None:
        filename = f"expenses_{date.today().isoformat()}.csv"
        filepath = os.path.join(EXPORT_DIR, filename)

    filepath = os.path.abspath(filepath)

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES, extrasaction="ignore")
        writer.writeheader()
        for expense in expenses:
            writer.writerow(expense)

    return filepath
