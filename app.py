"""
app.py — Streamlit web interface for the Personal Expense Tracker.
Run with:  streamlit run app.py
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import date, timedelta
import io

import database as db
import budgets
import export as exp

# ── Page config ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="💸 Expense Tracker",
    page_icon="💸",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Theme / CSS ───────────────────────────────────────────────────────────────

st.markdown("""
<style>
/* Dark background */
[data-testid="stAppViewContainer"] {
    background-color: #1E1E2E;
    color: #CDD6F4;
}
[data-testid="stSidebar"] {
    background-color: #181825;
}
/* Metric cards */
[data-testid="metric-container"] {
    background: #2A2A3E;
    border: 1px solid #45475A;
    border-radius: 12px;
    padding: 16px;
}
[data-testid="stMetricLabel"] { color: #A6ADC8 !important; font-size: 13px; }
[data-testid="stMetricValue"] { color: #CDD6F4 !important; }
/* Sidebar radio labels */
[data-testid="stSidebar"] label { font-size: 15px; }
/* Buttons */
.stButton > button {
    background: #6C63FF;
    color: white;
    border: none;
    border-radius: 8px;
    font-weight: 600;
}
.stButton > button:hover { background: #574fd6; color: white; }
/* Form inputs */
.stTextInput input, .stNumberInput input, .stSelectbox select,
.stDateInput input, .stTextArea textarea {
    background: #2A2A3E !important;
    color: #CDD6F4 !important;
    border: 1px solid #45475A !important;
    border-radius: 8px !important;
}
/* Dataframe */
[data-testid="stDataFrame"] { border-radius: 10px; overflow: hidden; }
/* Divider */
hr { border-color: #45475A; }
/* Success / error */
.stSuccess, .stAlert { border-radius: 8px; }
/* Headings */
h1, h2, h3 { color: #CDD6F4 !important; }
</style>
""", unsafe_allow_html=True)

# ── Palette ───────────────────────────────────────────────────────────────────

PALETTE = [
    "#6C63FF", "#FF6584", "#43D9AD", "#FFD166", "#EF8C8C",
    "#56CFE1", "#FF9F1C", "#A8DADC", "#E63946", "#2EC4B6",
]

CATEGORIES = [
    "Food", "Transport", "Shopping", "Entertainment",
    "Health", "Utilities", "Education", "Rent", "Other",
]

# ── Cached data fetchers ──────────────────────────────────────────────────────

@st.cache_data(ttl=5)
def fetch_all():
    return db.get_all_expenses()

@st.cache_data(ttl=5)
def fetch_monthly():
    return db.get_monthly_summary()

@st.cache_data(ttl=5)
def fetch_by_category():
    return db.get_spending_by_category()

@st.cache_data(ttl=5)
def fetch_total():
    return db.get_total_spending()

def clear_cache():
    fetch_all.clear()
    fetch_monthly.clear()
    fetch_by_category.clear()
    fetch_total.clear()

# ── Sidebar navigation ────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown(
        "<h2 style='color:#6C63FF;margin-bottom:4px;'>💸 Expense Tracker</h2>"
        "<p style='color:#585b70;font-size:13px;margin-top:0'>Powered by Python × Supabase</p>",
        unsafe_allow_html=True,
    )
    st.markdown("---")
    page = st.radio(
        "Navigate",
        [
            "🏠  Dashboard",
            "➕  Add Expense",
            "📋  Browse & Filter",
            "📊  Charts",
            "🎯  Budgets",
            "📤  Export",
        ],
        label_visibility="collapsed",
    )

# ── Helper: expenses as DataFrame ────────────────────────────────────────────

def to_df(expenses: list) -> pd.DataFrame:
    if not expenses:
        return pd.DataFrame()
    df = pd.DataFrame(expenses)
    df["amount"] = df["amount"].astype(float)
    df["date"] = pd.to_datetime(df["date"]).dt.date
    cols = [c for c in ["id", "date", "category", "amount", "description"] if c in df.columns]
    return df[cols]

# ─────────────────────────────────────────────────────────────────────────────
# PAGE: Dashboard
# ─────────────────────────────────────────────────────────────────────────────

if page == "🏠  Dashboard":
    st.title("🏠 Dashboard")

    expenses   = fetch_all()
    total      = fetch_total()
    by_cat     = fetch_by_category()

    # This-month total
    this_month = date.today().strftime("%Y-%m")
    month_total = sum(
        float(e["amount"]) for e in expenses
        if str(e["date"])[:7] == this_month
    )

    # Top category
    top_cat = by_cat[0]["category"] if by_cat else "—"

    # ── KPI cards ────────────────────────────────────────────────────────────
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("💰 Grand Total",    f"₹{total:,.2f}")
    k2.metric("📅 This Month",     f"₹{month_total:,.2f}")
    k3.metric("🧾 Total Expenses", str(len(expenses)))
    k4.metric("🏆 Top Category",   top_cat)

    st.markdown("---")

    # ── Recent expenses ───────────────────────────────────────────────────────
    col_l, col_r = st.columns([3, 2])

    with col_l:
        st.subheader("🕐 Recent Expenses")
        recent = expenses[:10]
        if recent:
            df = to_df(recent)
            st.dataframe(
                df.rename(columns={
                    "date": "Date", "category": "Category",
                    "amount": "Amount (₹)", "description": "Description",
                }).drop(columns=["id"], errors="ignore"),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No expenses yet. Head to **Add Expense** to get started!")

    with col_r:
        st.subheader("📊 Category Split")
        if by_cat:
            fig = go.Figure(go.Pie(
                labels=[b["category"] for b in by_cat],
                values=[b["total"] for b in by_cat],
                hole=0.5,
                marker=dict(colors=PALETTE, line=dict(color="#1E1E2E", width=2)),
            ))
            fig.update_layout(
                paper_bgcolor="#2A2A3E", plot_bgcolor="#2A2A3E",
                font_color="#CDD6F4", showlegend=True,
                margin=dict(t=20, b=20, l=20, r=20),
                height=300,
                legend=dict(font=dict(color="#CDD6F4")),
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No data yet.")

# ─────────────────────────────────────────────────────────────────────────────
# PAGE: Add Expense
# ─────────────────────────────────────────────────────────────────────────────

elif page == "➕  Add Expense":
    st.title("➕ Add Expense")

    with st.form("add_expense_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            amount = st.number_input("Amount (₹) *", min_value=0.01,
                                     step=0.01, format="%.2f")
            category = st.selectbox("Category *", CATEGORIES + ["Custom…"])
        with col2:
            expense_date = st.date_input("Date *", value=date.today())
            description  = st.text_input("Description (optional)")

        custom_cat = ""
        if category == "Custom…":
            custom_cat = st.text_input("Custom category name *")

        submitted = st.form_submit_button("💾 Save Expense", use_container_width=True)

    if submitted:
        final_cat = custom_cat.strip().title() if category == "Custom…" else category
        if not final_cat:
            st.error("Please enter a category name.")
        elif amount <= 0:
            st.error("Amount must be greater than ₹0.")
        else:
            row = db.add_expense(amount, final_cat, description, expense_date.isoformat())
            if row:
                clear_cache()
                st.success(
                    f"✅ Added **{final_cat}** — ₹{float(row['amount']):,.2f} on {row['date']}"
                )
            else:
                st.error("❌ Failed to save. Check your Supabase connection.")

# ─────────────────────────────────────────────────────────────────────────────
# PAGE: Browse & Filter
# ─────────────────────────────────────────────────────────────────────────────

elif page == "📋  Browse & Filter":
    st.title("📋 Browse & Filter")

    # ── Filter controls ───────────────────────────────────────────────────────
    filter_mode = st.radio(
        "Filter by",
        ["All", "Category", "Date Range"],
        horizontal=True,
    )

    expenses: list = []

    if filter_mode == "All":
        expenses = fetch_all()

    elif filter_mode == "Category":
        cats = db.get_all_categories() or CATEGORIES
        chosen_cat = st.selectbox("Select category", sorted(set(cats + CATEGORIES)))
        if st.button("🔍 Filter"):
            expenses = db.get_expenses_by_category(chosen_cat)
        else:
            expenses = fetch_all()

    else:  # Date Range
        c1, c2 = st.columns(2)
        start = c1.date_input("Start date", value=date.today().replace(day=1))
        end   = c2.date_input("End date",   value=date.today())
        if start > end:
            st.error("Start date must be before end date.")
        else:
            expenses = db.get_expenses_by_date_range(
                start.isoformat(), end.isoformat()
            )

    st.markdown("---")

    if not expenses:
        st.info("No expenses found.")
    else:
        df = to_df(expenses)
        subtotal = df["amount"].sum()

        col_info, col_total = st.columns([3, 1])
        col_info.markdown(f"**{len(expenses)} record(s)**")
        col_total.markdown(
            f"<div style='text-align:right;color:#FF6584;font-size:18px;font-weight:700'>"
            f"Total: ₹{subtotal:,.2f}</div>",
            unsafe_allow_html=True,
        )

        # Display table
        st.dataframe(
            df.rename(columns={
                "id": "ID", "date": "Date", "category": "Category",
                "amount": "Amount (₹)", "description": "Description",
            }),
            use_container_width=True,
            hide_index=True,
        )

        st.markdown("---")

        # ── Delete ────────────────────────────────────────────────────────────
        with st.expander("🗑️ Delete an Expense"):
            ids   = [e["id"]   for e in expenses]
            descs = [
                f"#{e['id']} | {e['date']} | {e['category']} | ₹{float(e['amount']):,.2f}"
                for e in expenses
            ]
            del_choice = st.selectbox("Choose expense to delete", descs, key="del_sel")
            del_idx    = descs.index(del_choice)
            del_id     = ids[del_idx]

            if st.button("🗑️ Delete selected", key="del_btn"):
                ok = db.delete_expense(del_id)
                if ok:
                    clear_cache()
                    st.success("Expense deleted.")
                    st.rerun()
                else:
                    st.error("Failed to delete.")

        # ── Edit ──────────────────────────────────────────────────────────────
        with st.expander("✏️ Edit an Expense"):
            edit_descs  = [
                f"#{e['id']} | {e['date']} | {e['category']} | ₹{float(e['amount']):,.2f}"
                for e in expenses
            ]
            edit_choice = st.selectbox("Choose expense to edit", edit_descs, key="edit_sel")
            edit_idx    = edit_descs.index(edit_choice)
            edit_exp    = expenses[edit_idx]

            with st.form("edit_form"):
                ec1, ec2 = st.columns(2)
                new_amount = ec1.number_input(
                    "Amount (₹)", value=float(edit_exp["amount"]),
                    min_value=0.01, step=0.01, format="%.2f"
                )
                new_cat = ec2.selectbox(
                    "Category",
                    CATEGORIES + ["Custom…"],
                    index=CATEGORIES.index(edit_exp["category"])
                          if edit_exp["category"] in CATEGORIES else 0,
                )
                new_desc = st.text_input("Description", value=edit_exp.get("description", ""))
                new_date = st.date_input(
                    "Date",
                    value=date.fromisoformat(str(edit_exp["date"])[:10]),
                )
                save_edit = st.form_submit_button("💾 Save Changes", use_container_width=True)

            if save_edit:
                final_cat = new_cat if new_cat != "Custom…" else new_desc
                updated = db.update_expense(edit_exp["id"], {
                    "amount":      new_amount,
                    "category":    final_cat,
                    "description": new_desc,
                    "date":        new_date.isoformat(),
                })
                if updated:
                    clear_cache()
                    st.success("Expense updated!")
                    st.rerun()
                else:
                    st.error("Failed to update.")

# ─────────────────────────────────────────────────────────────────────────────
# PAGE: Charts
# ─────────────────────────────────────────────────────────────────────────────

elif page == "📊  Charts":
    st.title("📊 Spending Charts")

    monthly = fetch_monthly()
    by_cat  = fetch_by_category()

    if not monthly and not by_cat:
        st.info("No expense data yet. Add some expenses first!")
    else:
        tab1, tab2 = st.tabs(["📅 Monthly Spending", "🏷️ By Category"])

        with tab1:
            if monthly:
                months = [m["month"] for m in monthly]
                totals = [m["total"] for m in monthly]
                fig = go.Figure(go.Bar(
                    x=months, y=totals,
                    marker_color=PALETTE[:len(months)],
                    text=[f"₹{t:,.2f}" for t in totals],
                    textposition="outside",
                    textfont=dict(color="#CDD6F4"),
                ))
                fig.update_layout(
                    title="Monthly Spending",
                    paper_bgcolor="#1E1E2E", plot_bgcolor="#2A2A3E",
                    font_color="#CDD6F4",
                    xaxis=dict(title="Month", gridcolor="#45475A"),
                    yaxis=dict(title="Amount (₹)", gridcolor="#45475A",
                               tickprefix="₹"),
                    height=450,
                    margin=dict(t=60, b=60),
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No monthly data yet.")

        with tab2:
            if by_cat:
                cats   = [b["category"] for b in by_cat]
                totals = [b["total"]    for b in by_cat]
                fig = go.Figure(go.Pie(
                    labels=cats, values=totals,
                    hole=0.45,
                    marker=dict(colors=PALETTE[:len(cats)],
                                line=dict(color="#1E1E2E", width=2)),
                    textinfo="label+percent",
                    textfont=dict(color="#CDD6F4"),
                ))
                fig.update_layout(
                    title="Spending by Category",
                    paper_bgcolor="#1E1E2E",
                    font_color="#CDD6F4",
                    legend=dict(font=dict(color="#CDD6F4")),
                    height=450,
                    margin=dict(t=60, b=40),
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No category data yet.")

# ─────────────────────────────────────────────────────────────────────────────
# PAGE: Budgets
# ─────────────────────────────────────────────────────────────────────────────

elif page == "🎯  Budgets":
    st.title("🎯 Budgets")

    tab_report, tab_set, tab_remove = st.tabs(
        ["📈 Budget Report", "💾 Set a Budget", "🗑️ Remove a Budget"]
    )

    # ── Report ────────────────────────────────────────────────────────────────
    with tab_report:
        st.subheader("Budget vs Actual")
        today_month = date.today().strftime("%Y-%m")
        month_str   = st.text_input("Month (YYYY-MM)", value=today_month, key="bud_month")

        if st.button("🔄 Load Report"):
            report = budgets.get_budget_vs_actual(month_str)
            if not report:
                st.info("No budgets set yet. Go to **Set a Budget** to add one.")
            else:
                for row in report:
                    pct  = row["pct"]
                    stat = row["status"]
                    color = {"ok": "#43D9AD", "warning": "#FFD166", "over": "#FF6584"}[stat]
                    icon  = {"ok": "🟢",      "warning": "🟡",       "over": "🔴"}[stat]

                    with st.container():
                        cl, cr = st.columns([3, 1])
                        cl.markdown(
                            f"**{icon} {row['category']}**  "
                            f"<span style='color:#A6ADC8;font-size:13px'>"
                            f"₹{row['actual']:,.2f} / ₹{row['budget']:,.2f}</span>",
                            unsafe_allow_html=True,
                        )
                        cr.markdown(
                            f"<div style='text-align:right;color:{color};font-weight:700'>"
                            f"{pct}%</div>",
                            unsafe_allow_html=True,
                        )
                        st.progress(min(pct / 100.0, 1.0))
                        st.markdown("")

    # ── Set ───────────────────────────────────────────────────────────────────
    with tab_set:
        st.subheader("Set / Update a Budget")
        with st.form("set_budget_form", clear_on_submit=True):
            all_cats = db.get_all_categories() or []
            cat_opts = sorted(set(all_cats + CATEGORIES)) + ["Custom…"]
            bcat = st.selectbox("Category", cat_opts, key="bcat_sel")
            custom_bcat = ""
            if bcat == "Custom…":
                custom_bcat = st.text_input("Custom category name")
            blimit = st.number_input("Monthly limit (₹)", min_value=0.01,
                                     step=100.0, format="%.2f")
            save_b = st.form_submit_button("💾 Save Budget", use_container_width=True)

        if save_b:
            final_bcat = custom_bcat.strip().title() if bcat == "Custom…" else bcat
            if not final_bcat:
                st.error("Category cannot be empty.")
            else:
                budgets.save_budget(final_bcat, blimit)
                st.success(f"✅ Budget set: **{final_bcat}** → ₹{blimit:,.2f}/month")

    # ── Remove ────────────────────────────────────────────────────────────────
    with tab_remove:
        st.subheader("Remove a Budget")
        current = budgets.load_budgets()
        if not current:
            st.info("No budgets set yet.")
        else:
            rm_cat = st.selectbox("Choose budget to remove", sorted(current.keys()))
            if st.button("🗑️ Remove", key="rm_bud"):
                ok = budgets.delete_budget(rm_cat)
                if ok:
                    st.success(f"Budget for **{rm_cat}** removed.")
                    st.rerun()
                else:
                    st.error("Budget not found.")

# ─────────────────────────────────────────────────────────────────────────────
# PAGE: Export
# ─────────────────────────────────────────────────────────────────────────────

elif page == "📤  Export":
    st.title("📤 Export to CSV")
    expenses = fetch_all()

    if not expenses:
        st.info("No expenses to export yet.")
    else:
        st.markdown(f"**{len(expenses)} expense(s)** ready to export.")

        # Build CSV in-memory so user gets a download button
        df = to_df(expenses)
        # Re-add created_at if present
        if expenses and "created_at" in expenses[0]:
            df["created_at"] = [e.get("created_at", "") for e in expenses]

        csv_buf = io.StringIO()
        df.to_csv(csv_buf, index=False)
        csv_bytes = csv_buf.getvalue().encode("utf-8")

        filename = f"expenses_{date.today().isoformat()}.csv"
        st.download_button(
            label="⬇️  Download CSV",
            data=csv_bytes,
            file_name=filename,
            mime="text/csv",
            use_container_width=True,
        )

        st.markdown("---")
        st.subheader("Preview")
        st.dataframe(df.head(20), use_container_width=True, hide_index=True)
