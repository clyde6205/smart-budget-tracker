"""
Annual Smart Budget Tracker — Commercial Edition
A self-contained, single-file Streamlit personal finance app.

Persistence: everything is saved to CSV/JSON files in ./data — no database
required. Data survives page refreshes, browser restarts, and redeploys as
long as the ./data folder is kept (or backed up).
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date
import os
import json
import io

# ---------------------------------------------------------------------------
# PAGE CONFIG
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Annual Smart Budget Tracker",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)

PALETTE = {
    "navy": "#1A2530",
    "card_bg": "#F8F9FA",
    "border": "#E2E8F0",
    "green": "#137333",
    "green_bg": "#E6F4EA",
    "red": "#C5221F",
    "red_bg": "#FCE8E6",
    "blue": "#1A73E8",
}

st.markdown(
    f"""
    <style>
        .main {{ background-color: #FFFFFF; }}
        div[data-testid="stMetric"] {{
            background-color: {PALETTE['card_bg']};
            border: 1px solid {PALETTE['border']};
            border-radius: 10px;
            padding: 14px 16px;
        }}
        div[data-testid="stMetricLabel"] {{ font-size: 12px; color: #4A5568; }}
        h1, h2, h3 {{ color: {PALETTE['navy']}; }}
        .stTabs [data-baseweb="tab"] {{ font-weight: 600; }}
        .app-header {{
            background-color: {PALETTE['navy']};
            color: white;
            padding: 18px 24px;
            border-radius: 10px;
            margin-bottom: 18px;
        }}
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# DATA FILES
# ---------------------------------------------------------------------------
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

TXN_FILE = os.path.join(DATA_DIR, "transactions.csv")
DEBT_FILE = os.path.join(DATA_DIR, "debts.csv")
ASSET_FILE = os.path.join(DATA_DIR, "assets.csv")
LIAB_FILE = os.path.join(DATA_DIR, "liabilities.csv")
TARGETS_FILE = os.path.join(DATA_DIR, "targets.csv")
NW_HISTORY_FILE = os.path.join(DATA_DIR, "networth_history.csv")
SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")
CATEGORIES_FILE = os.path.join(DATA_DIR, "categories.json")

MONTH_ORDER = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

DEFAULT_CATEGORIES = {
    "income": ["Salary / Wages", "Freelance / Side Hustle", "Investment Returns", "Refunds / Gifts"],
    "expense": {
        "Rent / Mortgage": "Needs (50%)",
        "Utilities & Internet": "Needs (50%)",
        "Groceries": "Needs (50%)",
        "Insurance & Healthcare": "Needs (50%)",
        "Dining & Takeout": "Wants (30%)",
        "Entertainment & Streaming": "Wants (30%)",
        "Shopping & Apparel": "Wants (30%)",
        "Emergency Fund": "Savings/Debt (20%)",
        "Investment / Retirement": "Savings/Debt (20%)",
        "Debt Service / Credit Card": "Savings/Debt (20%)",
    },
}

DEFAULT_SETTINGS = {
    "currency": "$",
    "starting_balance": 1000.00,
    "payday": "1st of the Month",
    "budget_year": datetime.now().year,
}


# ---------------------------------------------------------------------------
# PERSISTENCE HELPERS
# ---------------------------------------------------------------------------
def load_csv(path: str, default_df: pd.DataFrame) -> pd.DataFrame:
    if os.path.exists(path):
        try:
            return pd.read_csv(path)
        except pd.errors.EmptyDataError:
            return default_df.copy()
    default_df.to_csv(path, index=False)
    return default_df.copy()


def save_csv(df: pd.DataFrame, path: str) -> None:
    df.to_csv(path, index=False)


def load_json(path: str, default: dict) -> dict:
    if os.path.exists(path):
        with open(path, "r") as f:
            data = json.load(f)
        merged = {**default, **data}
        return merged
    save_json(default, path)
    return default.copy()


def save_json(data: dict, path: str) -> None:
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def default_transactions() -> pd.DataFrame:
    year = datetime.now().year
    return pd.DataFrame([
        {"Date": f"{year}-01-01", "Description": "Monthly Salary", "Type": "Income",
         "Amount": 5000.00, "Group": "N/A", "Category": "Salary / Wages"},
        {"Date": f"{year}-01-02", "Description": "Apartment Rent", "Type": "Expense",
         "Amount": 1500.00, "Group": "Needs (50%)", "Category": "Rent / Mortgage"},
        {"Date": f"{year}-01-05", "Description": "Grocery Store", "Type": "Expense",
         "Amount": 250.00, "Group": "Needs (50%)", "Category": "Groceries"},
        {"Date": f"{year}-01-10", "Description": "Streaming Services", "Type": "Expense",
         "Amount": 45.00, "Group": "Wants (30%)", "Category": "Entertainment & Streaming"},
    ])


def default_debts() -> pd.DataFrame:
    return pd.DataFrame([
        {"Debt Name": "Credit Card A", "Balance": 5000.00, "APR (%)": 19.99, "Min Payment": 150.00},
        {"Debt Name": "Auto Loan", "Balance": 12000.00, "APR (%)": 5.49, "Min Payment": 250.00},
    ])


def default_assets() -> pd.DataFrame:
    return pd.DataFrame([
        {"Asset": "Checking & Savings", "Category": "Liquid Cash", "Value": 8500.00},
        {"Asset": "Investment / 401(k)", "Category": "Retirement", "Value": 24000.00},
        {"Asset": "Primary Residence", "Category": "Real Estate", "Value": 350000.00},
    ])


def default_liabilities() -> pd.DataFrame:
    return pd.DataFrame([
        {"Liability": "Mortgage Balance", "Category": "Real Estate Debt", "Value": 210000.00},
        {"Liability": "Auto Loan", "Category": "Vehicle Debt", "Value": 12000.00},
        {"Liability": "Credit Card Balance", "Category": "Revolving Debt", "Value": 5000.00},
    ])


def default_targets(categories: dict) -> pd.DataFrame:
    rows = [{"Category": cat, "Annual Target": 0.0} for cat in categories["expense"].keys()]
    return pd.DataFrame(rows)


def default_nw_history() -> pd.DataFrame:
    return pd.DataFrame(columns=["Date", "Total Assets", "Total Liabilities", "Net Worth"])


# ---------------------------------------------------------------------------
# LOAD STATE (runs every rerun, cheap — CSV/JSON files are tiny)
# ---------------------------------------------------------------------------
settings = load_json(SETTINGS_FILE, DEFAULT_SETTINGS)
categories = load_json(CATEGORIES_FILE, DEFAULT_CATEGORIES)

df_txn = load_csv(TXN_FILE, default_transactions())
df_debts = load_csv(DEBT_FILE, default_debts())
df_assets = load_csv(ASSET_FILE, default_assets())
df_liab = load_csv(LIAB_FILE, default_liabilities())
df_targets = load_csv(TARGETS_FILE, default_targets(categories))
df_nw_hist = load_csv(NW_HISTORY_FILE, default_nw_history())

currency = settings["currency"]
starting_balance = float(settings["starting_balance"])
budget_year = int(settings["budget_year"])


def fmt(amount) -> str:
    try:
        return f"{currency}{amount:,.2f}"
    except (TypeError, ValueError):
        return f"{currency}0.00"


# ---------------------------------------------------------------------------
# HEADER
# ---------------------------------------------------------------------------
st.markdown(
    f"""<div class="app-header">
        <h2 style="color:white;margin:0;">💰 Annual Smart Budget Tracker</h2>
        <p style="margin:4px 0 0 0;opacity:0.85;">Budget Year {budget_year} &nbsp;·&nbsp; Payday: {settings['payday']}</p>
    </div>""",
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("### 💰 Smart Budget Tracker")
    st.caption("All changes save automatically to the `data/` folder — nothing is lost on refresh.")
    st.metric("Current Balance", fmt(starting_balance + df_txn.loc[df_txn['Type'] == 'Income', 'Amount'].sum()
                                      - df_txn.loc[df_txn['Type'] == 'Expense', 'Amount'].sum()))
    st.divider()
    st.caption("Need the full settings? Head to **⚙️ Setup & Categories**.")

# ---------------------------------------------------------------------------
# TABS
# ---------------------------------------------------------------------------
tab_dash, tab_txn, tab_budget, tab_debt, tab_nw, tab_setup = st.tabs(
    ["📊 Dashboard", "💳 Transactions Log", "📅 Monthly Budget",
     "🧊 Debt Calculator", "📈 Net Worth", "⚙️ Setup & Categories"]
)

# ---------------------------------------------------------------------------
# TAB 1: DASHBOARD
# ---------------------------------------------------------------------------
with tab_dash:
    total_income = df_txn.loc[df_txn["Type"] == "Income", "Amount"].sum()
    total_expenses = df_txn.loc[df_txn["Type"] == "Expense", "Amount"].sum()
    total_savings = df_txn.loc[
        (df_txn["Type"] == "Expense") & (df_txn["Group"] == "Savings/Debt (20%)"), "Amount"
    ].sum()
    net_cashflow = starting_balance + total_income - total_expenses

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Starting Balance", fmt(starting_balance))
    c2.metric("Total Income", fmt(total_income))
    c3.metric("Total Expenses", fmt(total_expenses))
    c4.metric("Total Savings", fmt(total_savings))
    c5.metric("Net Cashflow", fmt(net_cashflow), delta=fmt(total_income - total_expenses))

    st.markdown("---")
    st.subheader("🎯 50/30/20 Budget Breakdown")

    needs_actual = df_txn.loc[df_txn["Group"] == "Needs (50%)", "Amount"].sum()
    wants_actual = df_txn.loc[df_txn["Group"] == "Wants (30%)", "Amount"].sum()
    savings_actual = df_txn.loc[df_txn["Group"] == "Savings/Debt (20%)", "Amount"].sum()

    # Guard against a zero-income divide-by-zero / nonsense-percentage display
    safe_income = total_income if total_income > 0 else 0.0

    breakdown_df = pd.DataFrame([
        {"Group": "Needs (50%)", "Target %": "50%",
         "Target Amount": safe_income * 0.50, "Actual Spent": needs_actual,
         "Variance": (safe_income * 0.50) - needs_actual},
        {"Group": "Wants (30%)", "Target %": "30%",
         "Target Amount": safe_income * 0.30, "Actual Spent": wants_actual,
         "Variance": (safe_income * 0.30) - wants_actual},
        {"Group": "Savings/Debt (20%)", "Target %": "20%",
         "Target Amount": safe_income * 0.20, "Actual Spent": savings_actual,
         "Variance": savings_actual - (safe_income * 0.20)},
    ])

    col_table, col_chart = st.columns([3, 2])
    with col_table:
        def _style_variance(v):
            return f"color: {PALETTE['green']};" if v >= 0 else f"color: {PALETTE['red']};"

        styled = breakdown_df.style.format(
            {"Target Amount": lambda v: fmt(v), "Actual Spent": lambda v: fmt(v), "Variance": lambda v: fmt(v)}
        ).map(_style_variance, subset=["Variance"])
        st.dataframe(styled, use_container_width=True, hide_index=True)
        if total_income == 0:
            st.caption("⚠️ No income logged yet — targets will populate once income transactions are added.")

    with col_chart:
        if breakdown_df["Actual Spent"].sum() > 0:
            fig = px.pie(breakdown_df, values="Actual Spent", names="Group",
                         title="Actual Spending Distribution", hole=0.45,
                         color_discrete_sequence=[PALETTE["blue"], "#F9AB00", PALETTE["green"]])
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Add expense transactions to see your spending distribution.")

    st.markdown("---")
    st.subheader("📈 Cashflow Trend")
    if not df_txn.empty:
        trend_df = df_txn.copy()
        trend_df["Date"] = pd.to_datetime(trend_df["Date"], errors="coerce")
        trend_df = trend_df.dropna(subset=["Date"]).sort_values("Date")
        trend_df["Signed"] = trend_df.apply(
            lambda r: r["Amount"] if r["Type"] == "Income" else -r["Amount"], axis=1
        )
        trend_df["Running Balance"] = starting_balance + trend_df["Signed"].cumsum()
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=trend_df["Date"], y=trend_df["Running Balance"],
                                   mode="lines+markers", line=dict(color=PALETTE["blue"])))
        fig2.update_layout(margin=dict(t=10, b=10), yaxis_title=f"Balance ({currency})")
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("No transactions yet.")

# ---------------------------------------------------------------------------
# TAB 2: TRANSACTIONS LOG
# ---------------------------------------------------------------------------
with tab_txn:
    st.subheader("➕ Add New Transaction")
    with st.form("add_txn_form", clear_on_submit=True):
        col1, col2, col3, col4 = st.columns(4)
        txn_date = col1.date_input("Date", datetime.now())
        txn_type = col2.selectbox("Type", ["Expense", "Income"])
        txn_desc = col3.text_input("Description")
        txn_amount = col4.number_input("Amount", min_value=0.01, step=10.00)

        if txn_type == "Expense":
            expense_cats = list(categories["expense"].keys()) or ["Uncategorized"]
            cat = st.selectbox("Category", expense_cats)
            group = categories["expense"].get(cat, "N/A")
        else:
            income_cats = categories["income"] or ["Uncategorized"]
            cat = st.selectbox("Category", income_cats)
            group = "N/A"

        submitted = st.form_submit_button("Save Transaction", use_container_width=True)
        if submitted:
            if not txn_desc.strip():
                st.warning("Please enter a description before saving.")
            else:
                new_row = pd.DataFrame([{
                    "Date": str(txn_date), "Description": txn_desc, "Type": txn_type,
                    "Amount": txn_amount, "Group": group, "Category": cat,
                }])
                df_txn = pd.concat([df_txn, new_row], ignore_index=True)
                save_csv(df_txn, TXN_FILE)
                st.success("Transaction saved.")
                st.rerun()

    st.markdown("---")
    st.subheader("📒 Transaction Ledger")
    st.caption("Edit any cell directly, or use the trash icon on a row to delete it. Changes save automatically.")

    edited_txn = st.data_editor(
        df_txn,
        use_container_width=True,
        num_rows="dynamic",
        hide_index=True,
        column_config={
            "Amount": st.column_config.NumberColumn(format="%.2f"),
            "Type": st.column_config.SelectboxColumn(options=["Income", "Expense"]),
        },
        key="txn_editor",
    )
    if not edited_txn.equals(df_txn):
        save_csv(edited_txn, TXN_FILE)
        df_txn = edited_txn
        st.rerun()

    csv_buf = io.StringIO()
    df_txn.to_csv(csv_buf, index=False)
    st.download_button("⬇️ Export Transactions CSV", csv_buf.getvalue(),
                        file_name="transactions_export.csv", mime="text/csv")

# ---------------------------------------------------------------------------
# TAB 3: MONTHLY BUDGET
# ---------------------------------------------------------------------------
with tab_budget:
    st.subheader(f"📅 {budget_year} Monthly Expense Aggregation")

    df_exp = df_txn[df_txn["Type"] == "Expense"].copy()
    if not df_exp.empty:
        df_exp["Date"] = pd.to_datetime(df_exp["Date"], errors="coerce")
        df_exp = df_exp.dropna(subset=["Date"])
        df_exp = df_exp[df_exp["Date"].dt.year == budget_year]

    if not df_exp.empty:
        df_exp["Month"] = df_exp["Date"].dt.strftime("%b")
        pivot = df_exp.pivot_table(index=["Category", "Group"], columns="Month",
                                    values="Amount", aggfunc="sum", fill_value=0)
        for m in MONTH_ORDER:
            if m not in pivot.columns:
                pivot[m] = 0.0
        pivot = pivot[MONTH_ORDER]
        pivot["Annual Total"] = pivot.sum(axis=1)
        pivot = pivot.reset_index()

        targets_map = dict(zip(df_targets["Category"], df_targets["Annual Target"]))
        pivot["Annual Target"] = pivot["Category"].map(targets_map).fillna(0.0)
        pivot["Remaining"] = pivot["Annual Target"] - pivot["Annual Total"]

        fmt_cols = MONTH_ORDER + ["Annual Total", "Annual Target", "Remaining"]
        st.dataframe(
            pivot.style.format({c: (lambda v: fmt(v)) for c in fmt_cols}),
            use_container_width=True, hide_index=True,
        )
    else:
        st.info(f"No expense transactions logged for {budget_year} yet.")

    st.markdown("---")
    st.subheader("🎯 Annual Category Targets")
    st.caption("Set an annual spending target per category — used above to track Remaining budget.")
    edited_targets = st.data_editor(
        df_targets, use_container_width=True, num_rows="dynamic", hide_index=True,
        column_config={"Annual Target": st.column_config.NumberColumn(format="%.2f")},
        key="targets_editor",
    )
    if not edited_targets.equals(df_targets):
        save_csv(edited_targets, TARGETS_FILE)
        st.rerun()

# ---------------------------------------------------------------------------
# TAB 4: DEBT CALCULATOR
# ---------------------------------------------------------------------------
with tab_debt:
    st.subheader("🧊 Debt Payoff Estimator")
    strategy = st.radio(
        "Payoff Strategy", ["Avalanche (Highest APR First)", "Snowball (Lowest Balance First)"],
        horizontal=True,
    )

    st.caption("Edit balances, APR, or minimum payments below — deletions and additions save automatically.")
    edited_debts = st.data_editor(
        df_debts, use_container_width=True, num_rows="dynamic", hide_index=True,
        column_config={
            "Balance": st.column_config.NumberColumn(format="%.2f"),
            "APR (%)": st.column_config.NumberColumn(format="%.2f"),
            "Min Payment": st.column_config.NumberColumn(format="%.2f"),
        },
        key="debt_editor",
    )
    if not edited_debts.equals(df_debts):
        save_csv(edited_debts, DEBT_FILE)
        df_debts = edited_debts
        st.rerun()

    def calculate_payoff(row):
        balance, apr, pmt = row["Balance"], row["APR (%)"] / 100, row["Min Payment"]
        monthly_rate = apr / 12
        # Guard: payment must exceed the monthly interest accrual, or this never pays off
        if balance <= 0:
            return 0.0, 0.0
        if pmt <= balance * monthly_rate:
            return "Payment Too Low", "N/A"
        months = balance / (pmt - (balance * monthly_rate))
        total_paid = months * pmt
        total_interest = total_paid - balance
        return round(months, 1), round(total_interest, 2)

    if not df_debts.empty:
        results = df_debts.apply(calculate_payoff, axis=1, result_type="expand")
        results.columns = ["Est. Payoff (Months)", "Total Interest"]
        df_debt_view = pd.concat([df_debts, results], axis=1)

        if strategy.startswith("Avalanche"):
            df_debt_view = df_debt_view.sort_values("APR (%)", ascending=False)
        else:
            df_debt_view = df_debt_view.sort_values("Balance", ascending=True)
        df_debt_view.insert(0, "Priority", range(1, len(df_debt_view) + 1))

        st.markdown("---")
        st.subheader("📋 Payoff Priority Order")
        st.dataframe(
            df_debt_view.style.format({
                "Balance": lambda v: fmt(v), "Min Payment": lambda v: fmt(v),
                "APR (%)": "{:.2f}%",
                "Total Interest": lambda v: fmt(v) if isinstance(v, (int, float)) else v,
            }),
            use_container_width=True, hide_index=True,
        )

        total_balance = df_debts["Balance"].sum()
        total_min_pmt = df_debts["Min Payment"].sum()
        numeric_interest = pd.to_numeric(df_debt_view["Total Interest"], errors="coerce")
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Debt Balance", fmt(total_balance))
        c2.metric("Total Minimum Payments", fmt(total_min_pmt))
        c3.metric("Est. Total Interest (at minimums)", fmt(numeric_interest.sum(skipna=True)))
    else:
        st.info("No debts logged. Add one in the table above.")

# ---------------------------------------------------------------------------
# TAB 5: NET WORTH TRACKER
# ---------------------------------------------------------------------------
with tab_nw:
    st.subheader("📈 Net Worth Overview")

    col_a, col_l = st.columns(2)
    with col_a:
        st.markdown("**Assets (What You Own)**")
        edited_assets = st.data_editor(
            df_assets, use_container_width=True, num_rows="dynamic", hide_index=True,
            column_config={"Value": st.column_config.NumberColumn(format="%.2f")},
            key="asset_editor",
        )
        if not edited_assets.equals(df_assets):
            save_csv(edited_assets, ASSET_FILE)
            df_assets = edited_assets
            st.rerun()

    with col_l:
        st.markdown("**Liabilities (What You Owe)**")
        edited_liab = st.data_editor(
            df_liab, use_container_width=True, num_rows="dynamic", hide_index=True,
            column_config={"Value": st.column_config.NumberColumn(format="%.2f")},
            key="liab_editor",
        )
        if not edited_liab.equals(df_liab):
            save_csv(edited_liab, LIAB_FILE)
            df_liab = edited_liab
            st.rerun()

    tot_assets = df_assets["Value"].sum()
    tot_liab = df_liab["Value"].sum()
    net_worth = tot_assets - tot_liab

    st.markdown("---")
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Assets", fmt(tot_assets))
    c2.metric("Total Liabilities", fmt(tot_liab))
    c3.metric("Current Net Worth", fmt(net_worth))

    if st.button("📌 Save Snapshot to History", use_container_width=True):
        snap = pd.DataFrame([{
            "Date": str(date.today()), "Total Assets": tot_assets,
            "Total Liabilities": tot_liab, "Net Worth": net_worth,
        }])
        df_nw_hist = pd.concat([df_nw_hist, snap], ignore_index=True)
        save_csv(df_nw_hist, NW_HISTORY_FILE)
        st.success("Snapshot saved.")
        st.rerun()

    if not df_nw_hist.empty:
        st.markdown("---")
        st.subheader("Net Worth Trend")
        hist = df_nw_hist.copy()
        hist["Date"] = pd.to_datetime(hist["Date"], errors="coerce")
        hist = hist.dropna(subset=["Date"]).sort_values("Date")
        fig3 = px.line(hist, x="Date", y="Net Worth", markers=True)
        fig3.update_traces(line_color=PALETTE["blue"])
        st.plotly_chart(fig3, use_container_width=True)
        st.dataframe(
            df_nw_hist.style.format({
                "Total Assets": lambda v: fmt(v), "Total Liabilities": lambda v: fmt(v),
                "Net Worth": lambda v: fmt(v),
            }),
            use_container_width=True, hide_index=True,
        )

# ---------------------------------------------------------------------------
# TAB 6: SETUP & CATEGORIES
# ---------------------------------------------------------------------------
with tab_setup:
    st.subheader("⚙️ System Configuration")
    with st.form("settings_form"):
        col1, col2 = st.columns(2)
        new_currency = col1.selectbox(
            "Currency Symbol", ["$", "€", "£", "CA$", "A$", "¥", "CHF"],
            index=["$", "€", "£", "CA$", "A$", "¥", "CHF"].index(settings["currency"])
            if settings["currency"] in ["$", "€", "£", "CA$", "A$", "¥", "CHF"] else 0,
        )
        new_balance = col2.number_input("Starting Account Balance", value=float(settings["starting_balance"]), step=100.0)
        col3, col4 = st.columns(2)
        new_payday = col3.selectbox(
            "Payday Cycle", ["1st of the Month", "15th of the Month",
                              "Every 2 Weeks (Bi-Weekly)", "Last Day of Month"],
            index=["1st of the Month", "15th of the Month", "Every 2 Weeks (Bi-Weekly)",
                   "Last Day of Month"].index(settings["payday"])
            if settings["payday"] in ["1st of the Month", "15th of the Month",
                                       "Every 2 Weeks (Bi-Weekly)", "Last Day of Month"] else 0,
        )
        new_year = col4.number_input("Active Budget Year", value=int(settings["budget_year"]), step=1, format="%d")

        if st.form_submit_button("💾 Save Settings", use_container_width=True):
            settings.update({
                "currency": new_currency, "starting_balance": new_balance,
                "payday": new_payday, "budget_year": int(new_year),
            })
            save_json(settings, SETTINGS_FILE)
            st.success("Settings saved.")
            st.rerun()

    st.markdown("---")
    st.subheader("🏷️ Income Categories")
    income_text = st.text_area(
        "One category per line", value="\n".join(categories["income"]), height=120,
    )
    st.markdown("---")
    st.subheader("🏷️ Expense Categories & 50/30/20 Group")
    st.caption("Format: `Category Name | Group` — Group must be one of: Needs (50%), Wants (30%), Savings/Debt (20%)")
    expense_lines = "\n".join(f"{k} | {v}" for k, v in categories["expense"].items())
    expense_text = st.text_area("Expense categories", value=expense_lines, height=220)

    if st.button("💾 Save Categories", use_container_width=True):
        new_income = [line.strip() for line in income_text.splitlines() if line.strip()]
        new_expense = {}
        valid_groups = {"Needs (50%)", "Wants (30%)", "Savings/Debt (20%)"}
        malformed = []
        for line in expense_text.splitlines():
            if not line.strip():
                continue
            parts = [p.strip() for p in line.split("|")]
            if len(parts) == 2 and parts[1] in valid_groups:
                new_expense[parts[0]] = parts[1]
            else:
                malformed.append(line)
        if malformed:
            st.error("These lines couldn't be saved (check the `Name | Group` format and group spelling): "
                      + "; ".join(malformed))
        else:
            categories["income"] = new_income
            categories["expense"] = new_expense
            save_json(categories, CATEGORIES_FILE)
            st.success("Categories saved.")
            st.rerun()

    st.markdown("---")
    st.subheader("🗄️ Data Management")
    col1, col2 = st.columns(2)
    with col1:
        st.caption("Your data lives in the `data/` folder as plain CSV/JSON files — back it up by copying that folder.")
        all_buf = io.StringIO()
        df_txn.to_csv(all_buf, index=False)
        st.download_button("⬇️ Download Transactions Backup", all_buf.getvalue(),
                            file_name=f"transactions_backup_{date.today()}.csv", mime="text/csv")
    with col2:
        st.warning("Resetting clears all transactions, debts, assets, and liabilities. This cannot be undone.")
        confirm = st.checkbox("I understand this will erase all data")
        if st.button("🗑️ Reset All Data", disabled=not confirm, use_container_width=True):
            save_csv(default_transactions(), TXN_FILE)
            save_csv(default_debts(), DEBT_FILE)
            save_csv(default_assets(), ASSET_FILE)
            save_csv(default_liabilities(), LIAB_FILE)
            save_csv(default_nw_history(), NW_HISTORY_FILE)
            st.success("All data reset to defaults.")
            st.rerun()
