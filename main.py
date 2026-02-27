"""
main.py — Interactive CLI entry point for the Personal Expense Tracker.
Uses the `rich` library for styled terminal output.
"""

from datetime import date, timedelta
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich import box
from rich.text import Text

import database as db
import charts
import budgets
import export

console = Console()


# ── Helpers ──────────────────────────────────────────────────────────────────

CATEGORIES = [
    "Food", "Transport", "Shopping", "Entertainment",
    "Health", "Utilities", "Education", "Rent", "Other",
]


def rule(title: str = ""):
    console.rule(f"[bold #6C63FF]{title}[/]")


def expense_table(expenses: list, title: str = "Expenses", show_id: bool = False) -> Table:
    """Build a rich Table from a list of expense dicts."""
    table = Table(
        title=title,
        box=box.ROUNDED,
        header_style="bold #6C63FF",
        border_style="#45475A",
        show_lines=True,
    )
    table.add_column("#",           style="dim",          justify="right", width=4)
    if show_id:
        table.add_column("DB ID",   style="dim",          justify="right", width=6)
    table.add_column("Date",        style="#FFD166",      justify="center")
    table.add_column("Category",    style="#43D9AD",      justify="left")
    table.add_column("Amount (₹)",  style="bold #FF6584", justify="right")
    table.add_column("Description", style="#CDD6F4",      justify="left")

    for i, e in enumerate(expenses, 1):
        row_data = [str(i)]
        if show_id:
            row_data.append(str(e.get("id", "")))
        row_data += [
            str(e.get("date", "")),
            e.get("category", ""),
            f"₹{float(e.get('amount', 0)):,.2f}",
            e.get("description", "") or "—",
        ]
        table.add_row(*row_data)
    return table


def pick_expense(expenses: list, prompt_text: str) -> dict | None:
    """Show a numbered table and let the user pick one row. Returns the expense dict or None."""
    console.print(expense_table(expenses, show_id=False))
    while True:
        raw = Prompt.ask(prompt_text)
        if raw.strip().lower() in ("", "q", "quit", "cancel"):
            return None
        if raw.isdigit() and 1 <= int(raw) <= len(expenses):
            return expenses[int(raw) - 1]
        console.print(f"[red]Please enter a number between 1 and {len(expenses)}, or press Enter to cancel.[/]")


def ask_amount() -> float | None:
    """Prompt for a positive float amount. Returns None if user cancels."""
    while True:
        raw = Prompt.ask("[bold]New amount (₹)[/] [dim](or Enter to skip)[/]", default="")
        if raw.strip() == "":
            return None
        try:
            val = float(raw.replace(",", ""))
            if val <= 0:
                console.print("[red]Amount must be positive.[/]")
                continue
            return val
        except ValueError:
            console.print("[red]Please enter a valid number.[/]")


def ask_date(prompt: str = "[bold]Date (YYYY-MM-DD)[/]", default: str = "") -> str | None:
    """Prompt for a valid ISO date. Returns None if user skips."""
    raw = Prompt.ask(prompt, default=default)
    if raw.strip() == "":
        return None
    try:
        date.fromisoformat(raw)
        return raw
    except ValueError:
        console.print(f"[red]Invalid date format. Using '{default or 'skipped'}'.[/]")
        return default if default else None


# ── Feature handlers ─────────────────────────────────────────────────────────

def handle_add_expense():
    rule("Add Expense")

    # Amount
    while True:
        try:
            amount = float(Prompt.ask("[bold]Amount (₹)[/]").replace(",", ""))
            if amount <= 0:
                console.print("[red]Amount must be positive.[/]")
                continue
            break
        except ValueError:
            console.print("[red]Please enter a valid number.[/]")

    # Category
    console.print("\n[bold #43D9AD]Available categories:[/]")
    for idx, cat in enumerate(CATEGORIES, 1):
        console.print(f"  [dim]{idx}.[/] {cat}")
    console.print(f"  [dim]{len(CATEGORIES)+1}.[/] [italic]Enter custom category[/]")

    cat_input = Prompt.ask("[bold]Choose category[/] [dim](number or name)[/]")
    if cat_input.isdigit():
        n = int(cat_input)
        if 1 <= n <= len(CATEGORIES):
            category = CATEGORIES[n - 1]
        elif n == len(CATEGORIES) + 1:
            category = Prompt.ask("[bold]Custom category[/]")
        else:
            category = cat_input
    else:
        category = cat_input

    # Description
    description = Prompt.ask("[bold]Description[/] [dim](optional)[/]", default="")

    # Date
    today = date.today().isoformat()
    date_str = Prompt.ask("[bold]Date[/] [dim](YYYY-MM-DD)[/]", default=today)
    try:
        date.fromisoformat(date_str)
    except ValueError:
        console.print(f"[red]Invalid date, using today ({today}).[/]")
        date_str = today

    row = db.add_expense(amount, category, description, date_str)
    if row:
        console.print(
            Panel(
                f"[bold #43D9AD]✔ Expense added![/]\n\n"
                f"  [dim]Category:[/]  [#43D9AD]{row['category']}[/]\n"
                f"  [dim]Amount:[/]    [bold #FF6584]₹{float(row['amount']):,.2f}[/]\n"
                f"  [dim]Date:[/]      [#FFD166]{row['date']}[/]",
                border_style="#6C63FF",
            )
        )
    else:
        console.print("[red]Failed to add expense. Check your connection.[/]")


def handle_view_all():
    rule("All Expenses")
    expenses = db.get_all_expenses()
    if not expenses:
        console.print("[yellow]No expenses found.[/]")
        return
    console.print(expense_table(expenses, f"All Expenses ({len(expenses)} records)"))


def handle_filter_by_category():
    rule("Filter by Category")
    categories = db.get_all_categories()
    if not categories:
        console.print("[yellow]No expenses recorded yet.[/]")
        return

    console.print("[bold #43D9AD]Existing categories:[/] " + ", ".join(categories))
    category = Prompt.ask("[bold]Enter category to filter[/]")
    expenses = db.get_expenses_by_category(category)

    if not expenses:
        console.print(f"[yellow]No expenses found for category '[bold]{category}[/]'.[/]")
        return

    total = round(sum(float(e["amount"]) for e in expenses), 2)
    console.print(expense_table(expenses, f"Category: {category.title()} ({len(expenses)} records)"))
    console.print(f"\n  [dim]Subtotal →[/] [bold #FF6584]₹{total:,.2f}[/]\n")


def handle_total_spending():
    rule("Total Spending")
    total = db.get_total_spending()
    breakdown = db.get_spending_by_category()

    table = Table(
        title="Spending by Category",
        box=box.SIMPLE_HEAVY,
        header_style="bold #6C63FF",
        border_style="#45475A",
    )
    table.add_column("Category",   style="#43D9AD",      justify="left")
    table.add_column("Amount (₹)", style="bold #FF6584", justify="right")

    for b in breakdown:
        table.add_row(b["category"], f"₹{b['total']:,.2f}")

    console.print(table)
    console.print(
        Panel(
            f"[bold]Grand Total:[/]  [bold #FF6584]₹{total:,.2f}[/]",
            border_style="#6C63FF",
            expand=False,
        )
    )


def handle_monthly_summary():
    rule("Monthly Summary")
    summary = db.get_monthly_summary()
    if not summary:
        console.print("[yellow]No expenses recorded yet.[/]")
        return

    table = Table(
        title="Monthly Spending Summary",
        box=box.ROUNDED,
        header_style="bold #6C63FF",
        border_style="#45475A",
        show_lines=True,
    )
    table.add_column("Month",     style="#FFD166",      justify="center")
    table.add_column("Total (₹)", style="bold #FF6584", justify="right")

    grand = 0.0
    for s in summary:
        table.add_row(s["month"], f"₹{s['total']:,.2f}")
        grand += s["total"]

    table.add_section()
    table.add_row("[bold]TOTAL[/]", f"[bold #FF6584]₹{grand:,.2f}[/]")
    console.print(table)


def handle_show_graph():
    rule("Spending Graphs")
    console.print("[dim]Opening charts in separate windows…[/]\n")
    charts.show_graphs()


# ── NEW: Delete ───────────────────────────────────────────────────────────────

def handle_delete_expense():
    rule("Delete Expense")
    expenses = db.get_all_expenses()
    if not expenses:
        console.print("[yellow]No expenses to delete.[/]")
        return

    chosen = pick_expense(expenses, "[bold red]Enter # to delete[/] [dim](or Enter to cancel)[/]")
    if chosen is None:
        console.print("[dim]Cancelled.[/]")
        return

    console.print(
        f"\n  You selected: [#43D9AD]{chosen['category']}[/]  "
        f"[bold #FF6584]₹{float(chosen['amount']):,.2f}[/]  "
        f"[#FFD166]{chosen['date']}[/]\n"
    )
    if not Confirm.ask("[bold red]Are you sure you want to delete this expense?[/]", default=False):
        console.print("[dim]Cancelled — nothing was deleted.[/]")
        return

    ok = db.delete_expense(chosen["id"])
    if ok:
        console.print(
            Panel("[bold #43D9AD]✔ Expense deleted successfully.[/]", border_style="#FF6584")
        )
    else:
        console.print("[red]Failed to delete expense. Check your connection.[/]")


# ── NEW: Edit ─────────────────────────────────────────────────────────────────

def handle_edit_expense():
    rule("Edit Expense")
    expenses = db.get_all_expenses()
    if not expenses:
        console.print("[yellow]No expenses to edit.[/]")
        return

    chosen = pick_expense(expenses, "[bold]Enter # to edit[/] [dim](or Enter to cancel)[/]")
    if chosen is None:
        console.print("[dim]Cancelled.[/]")
        return

    console.print(
        f"\n  Editing: [#43D9AD]{chosen['category']}[/]  "
        f"[bold #FF6584]₹{float(chosen['amount']):,.2f}[/]  "
        f"[#FFD166]{chosen['date']}[/]\n"
    )

    updates: dict = {}

    EDIT_FIELDS = {
        "1": "Amount",
        "2": "Category",
        "3": "Description",
        "4": "Date",
        "0": "Done",
    }

    while True:
        console.print("[bold #43D9AD]What would you like to change?[/]")
        for k, v in EDIT_FIELDS.items():
            style = "bold #FF6584" if k == "0" else "#CDD6F4"
            console.print(f"  [{style}]{k}[/]  {v}")
        field_choice = Prompt.ask("[bold]Choose field[/]", choices=list(EDIT_FIELDS.keys()), show_choices=False)

        if field_choice == "0":
            break
        elif field_choice == "1":
            val = ask_amount()
            if val is not None:
                updates["amount"] = val
                console.print(f"[dim]  ✓ Amount will be updated to ₹{val:,.2f}[/]")
        elif field_choice == "2":
            console.print("[bold #43D9AD]Categories:[/] " + ", ".join(CATEGORIES))
            new_cat = Prompt.ask("[bold]New category[/]", default=chosen["category"])
            if new_cat.strip():
                updates["category"] = new_cat.strip().title()
                console.print(f"[dim]  ✓ Category will be updated to {updates['category']}[/]")
        elif field_choice == "3":
            new_desc = Prompt.ask("[bold]New description[/]", default=chosen.get("description", ""))
            updates["description"] = new_desc.strip()
            console.print(f"[dim]  ✓ Description will be updated.[/]")
        elif field_choice == "4":
            new_date = ask_date("[bold]New date (YYYY-MM-DD)[/]", default=str(chosen["date"]))
            if new_date:
                updates["date"] = new_date
                console.print(f"[dim]  ✓ Date will be updated to {new_date}[/]")
        console.print()

    if not updates:
        console.print("[dim]No changes made.[/]")
        return

    updated = db.update_expense(chosen["id"], updates)
    if updated:
        console.print(
            Panel(
                f"[bold #43D9AD]✔ Expense updated![/]\n\n"
                f"  [dim]Category:[/]  [#43D9AD]{updated.get('category', chosen['category'])}[/]\n"
                f"  [dim]Amount:[/]    [bold #FF6584]₹{float(updated.get('amount', chosen['amount'])):,.2f}[/]\n"
                f"  [dim]Date:[/]      [#FFD166]{updated.get('date', chosen['date'])}[/]",
                border_style="#6C63FF",
            )
        )
    else:
        console.print("[red]Failed to update expense.[/]")


# ── NEW: Date Range Filter ────────────────────────────────────────────────────

def handle_filter_by_date():
    rule("Filter by Date Range")

    today = date.today()
    first_of_month = today.replace(day=1).isoformat()
    today_str = today.isoformat()

    console.print("[dim]Leave blank to use the default value shown.[/]\n")
    start_str = ask_date(
        f"[bold]Start date[/] [dim](YYYY-MM-DD, default: {first_of_month})[/]",
        default=first_of_month,
    ) or first_of_month

    end_str = ask_date(
        f"[bold]End date[/]   [dim](YYYY-MM-DD, default: {today_str})[/]",
        default=today_str,
    ) or today_str

    if start_str > end_str:
        console.print("[red]Start date must be before or equal to end date.[/]")
        return

    expenses = db.get_expenses_by_date_range(start_str, end_str)

    if not expenses:
        console.print(f"[yellow]No expenses found between {start_str} and {end_str}.[/]")
        return

    total = round(sum(float(e["amount"]) for e in expenses), 2)
    console.print(expense_table(
        expenses,
        f"Expenses: {start_str} → {end_str}  ({len(expenses)} records)",
    ))
    console.print(f"\n  [dim]Subtotal →[/] [bold #FF6584]₹{total:,.2f}[/]\n")


# ── NEW: Budgets ──────────────────────────────────────────────────────────────

_STATUS_STYLE = {
    "ok":      ("🟢", "#43D9AD"),
    "warning": ("🟡", "#FFD166"),
    "over":    ("🔴", "#FF6584"),
}


def handle_budgets():
    rule("Budget & Alerts")

    BUDGET_MENU = {
        "1": "Set / Update a Budget",
        "2": "View Budget Report",
        "3": "Remove a Budget",
        "0": "Back to Main Menu",
    }

    while True:
        console.print()
        for k, v in BUDGET_MENU.items():
            style = "bold #FF6584" if k == "0" else "#CDD6F4"
            console.print(f"  [{style}]{k}[/]  {v}")
        console.print()
        choice = Prompt.ask("[bold #6C63FF]Budget option[/]", choices=list(BUDGET_MENU.keys()), show_choices=False)

        if choice == "0":
            break

        elif choice == "1":
            # Set budget
            all_cats = db.get_all_categories() or CATEGORIES
            console.print("[bold #43D9AD]Categories:[/] " + ", ".join(sorted(set(all_cats + CATEGORIES))))
            cat = Prompt.ask("[bold]Category[/]").strip().title()
            if not cat:
                console.print("[red]Category cannot be empty.[/]")
                continue
            while True:
                try:
                    limit = float(Prompt.ask(f"[bold]Monthly budget for {cat} (₹)[/]").replace(",", ""))
                    if limit <= 0:
                        console.print("[red]Budget must be positive.[/]")
                        continue
                    break
                except ValueError:
                    console.print("[red]Please enter a valid number.[/]")
            budgets.save_budget(cat, limit)
            console.print(Panel(
                f"[bold #43D9AD]✔ Budget saved![/]\n\n"
                f"  [dim]Category:[/] [#43D9AD]{cat}[/]\n"
                f"  [dim]Limit:[/]    [bold #FF6584]₹{limit:,.2f}[/] / month",
                border_style="#6C63FF",
            ))

        elif choice == "2":
            # View report
            today_month = date.today().strftime("%Y-%m")
            month_str = Prompt.ask(
                f"[bold]Month (YYYY-MM)[/] [dim](default: {today_month})[/]",
                default=today_month,
            )
            report = budgets.get_budget_vs_actual(month_str)

            if not report:
                console.print("[yellow]No budgets set yet. Choose option 1 to add one.[/]")
                continue

            table = Table(
                title=f"Budget Report — {month_str}",
                box=box.ROUNDED,
                header_style="bold #6C63FF",
                border_style="#45475A",
                show_lines=True,
            )
            table.add_column("Category",   style="#43D9AD",      justify="left")
            table.add_column("Budget (₹)", style="#CDD6F4",       justify="right")
            table.add_column("Actual (₹)", style="bold #FF6584",  justify="right")
            table.add_column("Used %",     style="#FFD166",       justify="right")
            table.add_column("Status",                             justify="center")

            for row in report:
                icon, colour = _STATUS_STYLE[row["status"]]
                table.add_row(
                    row["category"],
                    f"₹{row['budget']:,.2f}",
                    f"[{colour}]₹{row['actual']:,.2f}[/]",
                    f"[{colour}]{row['pct']}%[/]",
                    icon,
                )
            console.print(table)

        elif choice == "3":
            # Remove budget
            current = budgets.load_budgets()
            if not current:
                console.print("[yellow]No budgets set yet.[/]")
                continue
            console.print("[bold #43D9AD]Current budgets:[/] " + ", ".join(sorted(current.keys())))
            cat = Prompt.ask("[bold]Category to remove[/]").strip().title()
            if budgets.delete_budget(cat):
                console.print(f"[bold #43D9AD]✔ Budget for '{cat}' removed.[/]")
            else:
                console.print(f"[yellow]No budget found for '{cat}'.[/]")

        console.print()


# ── NEW: Export CSV ───────────────────────────────────────────────────────────

def handle_export_csv():
    rule("Export to CSV")
    expenses = db.get_all_expenses()
    if not expenses:
        console.print("[yellow]No expenses to export.[/]")
        return

    console.print(f"[dim]Found {len(expenses)} expense(s). Exporting…[/]\n")
    filepath = export.export_to_csv(expenses)
    console.print(
        Panel(
            f"[bold #43D9AD]✔ Export complete![/]\n\n"
            f"  [dim]File:[/]     [bold]{filepath}[/]\n"
            f"  [dim]Records:[/]  {len(expenses)}",
            border_style="#6C63FF",
        )
    )


# ── Menu ─────────────────────────────────────────────────────────────────────

MENU_ITEMS = {
    "1": ("➕  Add Expense",          handle_add_expense),
    "2": ("📋  View All Expenses",    handle_view_all),
    "3": ("🔍  Filter by Category",   handle_filter_by_category),
    "4": ("💰  Total Spending",       handle_total_spending),
    "5": ("📅  Monthly Summary",      handle_monthly_summary),
    "6": ("📊  Show Spending Graph",  handle_show_graph),
    "7": ("🗑️   Delete Expense",      handle_delete_expense),
    "8": ("✏️   Edit Expense",         handle_edit_expense),
    "9": ("📆  Filter by Date Range", handle_filter_by_date),
    "B": ("🎯  Budget & Alerts",      handle_budgets),
    "E": ("📤  Export to CSV",        handle_export_csv),
    "0": ("🚪  Exit",                 None),
}


def print_menu():
    console.print()
    console.print(
        Panel.fit(
            "[bold #6C63FF]💸 Personal Expense Tracker[/]\n"
            "[dim]Powered by Python × Supabase[/]",
            border_style="#6C63FF",
        )
    )
    console.print()
    for key, (label, _) in MENU_ITEMS.items():
        style = "bold #FF6584" if key == "0" else "#CDD6F4"
        console.print(f"  [{style}]{key}[/]  {label}")
    console.print()


def main():
    console.clear()
    while True:
        print_menu()
        choice = Prompt.ask(
            "[bold #6C63FF]Choose an option[/]",
            choices=list(MENU_ITEMS.keys()),
            show_choices=False,
        )

        if choice == "0":
            console.print("\n[bold #6C63FF]Goodbye! 👋[/]\n")
            break

        _, handler = MENU_ITEMS[choice]
        console.print()
        try:
            handler()
        except Exception as exc:
            console.print(f"\n[bold red]Error:[/] {exc}")

        console.print()
        Prompt.ask("[dim]Press Enter to return to menu…[/]", default="")
        console.clear()


if __name__ == "__main__":
    main()
