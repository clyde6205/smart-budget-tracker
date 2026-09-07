import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# Page Configuration
st.set_page_config(page_title="Annual Smart Budget Engine", page_icon="📊", layout="wide")

# Session State Initialization (Acts as the database)
if 'transactions' not in st.session_state:
    st.session_state.transactions = pd.DataFrame([
        {"Date": "2026-01-01", "Description": "Monthly Salary", "Type": "Income", "Amount": 5000.00, "Group": "N/A", "Category": "Salary / Wages"},
        {"Date": "2026-01-02", "Description": "Apartment Rent", "Type": "Expense", "Amount": 1500.00, "Group": "Needs (50%)", "Category": "Rent / Mortgage"},
        {"Date": "2026-01-05", "Description": "Grocery Store", "Type": "Expense", "Amount": 250.00, "Group": "Needs (50%)", "Category": "Groceries"},
        {"Date": "2026-01-10", "Description": "Streaming Services", "Type": "Expense", "Amount": 45.00, "Group": "Wants (30%)", "Category": "Entertainment & Streaming"}
    ])

if 'debts' not in st.session_state:
    st.session_state.debts = pd.DataFrame([
        {"Debt Name": "Credit Card A", "Balance": 5000.00, "APR (%)": 19.99, "Min Payment": 150.00},
        {"Debt Name": "Auto Loan", "Balance": 12000.00, "APR (%)": 5.49, "Min Payment": 250.00}
    ])

if 'assets' not in st.session_state:
    st.session_state.assets = pd.DataFrame([
        {"Asset": "Checking & Savings", "Category": "Liquid Cash", "Value": 8500.00},
        {"Asset": "Investment / 401(k)", "Category": "Retirement", "Value": 24000.00},
        {"Asset": "Primary Residence", "Category": "Real Estate", "Value": 350000.00}
    ])

if 'liabilities' not in st.session_state:
    st.session_state.liabilities = pd.DataFrame([
        {"Liability": "Mortgage Balance", "Category": "Real Estate Debt", "Value": 210000.00},
        {"Liability": "Auto Loan", "Category": "Vehicle Debt", "Value": 12000.00},
        {"Liability": "Credit Card Balance", "Category": "Revolving Debt", "Value": 5000.00}
    ])

# Sidebar Configuration & Setup
st.sidebar.title("⚙️ System Configuration")
currency = st.sidebar.selectbox("Select Currency", ["$", "€", "£", "CA$", "A$", "¥"], index=0)
starting_balance = st.sidebar.number_input("Starting Account Balance", value=1000.00, step=100.00)

# Categories Mapping
EXPENSE_CATEGORIES = {
    "Rent / Mortgage": "Needs (50%)", "Utilities & Internet": "Needs (50%)",
    "Groceries": "Needs (50%)", "Insurance & Healthcare": "Needs (50%)",
    "Dining & Takeout": "Wants (30%)", "Entertainment & Streaming": "Wants (30%)",
    "Shopping & Apparel": "Wants (30%)", "Emergency Fund": "Savings/Debt (20%)",
    "Investment / Retirement": "Savings/Debt (20%)", "Debt Service": "Savings/Debt (20%)"
}
INCOME_CATEGORIES = ["Salary / Wages", "Freelance / Side Hustle", "Investment Returns", "Refunds / Gifts"]

# App Navigation
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Dashboard", "💳 Transactions Log", "📅 Monthly Budget", "🧊 Debt Calculator", "📈 Net Worth"
])

# -------------------------------------------------------------------
# TAB 1: DASHBOARD
# -------------------------------------------------------------------
with tab1:
    st.title("📊 Financial Dashboard")
    
    df_txn = st.session_state.transactions
    total_income = df_txn[df_txn["Type"] == "Income"]["Amount"].sum()
    total_expenses = df_txn[df_txn["Type"] == "Expense"]["Amount"].sum()
    total_savings = df_txn[(df_txn["Type"] == "Expense") & (df_txn["Group"] == "Savings/Debt (20%)")]["Amount"].sum()
    net_cashflow = starting_balance + total_income - total_expenses

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Starting Balance", f"{currency}{starting_balance:,.2f}")
    c2.metric("Total Income", f"{currency}{total_income:,.2f}")
    c3.metric("Total Expenses", f"{currency}{total_expenses:,.2f}")
    c4.metric("Total Savings", f"{currency}{total_savings:,.2f}")
    c5.metric("Net Cashflow", f"{currency}{net_cashflow:,.2f}", delta=f"{currency}{total_income - total_expenses:,.2f}")

    st.markdown("---")
    st.subheader("🎯 50/30/20 Budget Breakdown")
    
    needs_actual = df_txn[df_txn["Group"] == "Needs (50%)"]["Amount"].sum()
    wants_actual = df_txn[df_txn["Group"] == "Wants (30%)"]["Amount"].sum()
    savings_actual = df_txn[df_txn["Group"] == "Savings/Debt (20%)"]["Amount"].sum()

    breakdown_df = pd.DataFrame([
        {"Group": "Needs (50%)", "Target %": "50%", "Target Amount": total_income * 0.50, "Actual Spent": needs_actual, "Variance": (total_income * 0.50) - needs_actual},
        {"Group": "Wants (30%)", "Target %": "30%", "Target Amount": total_income * 0.30, "Actual Spent": wants_actual, "Variance": (total_income * 0.30) - wants_actual},
        {"Group": "Savings/Debt (20%)", "Target %": "20%", "Target Amount": total_income * 0.20, "Actual Spent": savings_actual, "Variance": savings_actual - (total_income * 0.20)}
    ])
    
    col_table, col_chart = st.columns([3, 2])
    with col_table:
        st.dataframe(breakdown_df.style.format({"Target Amount": f"{currency}{{:,.2f}}", "Actual Spent": f"{currency}{{:,.2f}}", "Variance": f"{currency}{{:,.2f}}"}), use_container_width=True)
    
    with col_chart:
        fig = px.pie(breakdown_df, values="Actual Spent", names="Group", title="Actual Spending Distribution", hole=0.4)
        st.plotly_chart(fig, use_container_width=True)

# -------------------------------------------------------------------
# TAB 2: TRANSACTIONS LOG
# -------------------------------------------------------------------
with tab2:
    st.title("💳 Transactions Manager")
    
    with st.expander("➕ Add New Transaction", expanded=True):
        col1, col2, col3, col4 = st.columns(4)
        txn_date = col1.date_input("Date", datetime.now())
        txn_type = col2.selectbox("Type", ["Expense", "Income"])
        txn_desc = col3.text_input("Description")
        txn_amount = col4.number_input("Amount", min_value=0.01, step=10.00)

        if txn_type == "Expense":
            cat = st.selectbox("Category", list(EXPENSE_CATEGORIES.keys()))
            group = EXPENSE_CATEGORIES[cat]
        else:
            cat = st.selectbox("Category", INCOME_CATEGORIES)
            group = "N/A"

        if st.button("Save Transaction", use_container_width=True):
            new_row = pd.DataFrame([{"Date": str(txn_date), "Description": txn_desc, "Type": txn_type, "Amount": txn_amount, "Group": group, "Category": cat}])
            st.session_state.transactions = pd.concat([st.session_state.transactions, new_row], ignore_index=True)
            st.success("Transaction recorded!")
            st.rerun()

    st.subheader("Transaction Ledger")
    st.dataframe(st.session_state.transactions.style.format({"Amount": f"{currency}{{:,.2f}}"}), use_container_width=True)

# -------------------------------------------------------------------
# TAB 3: MONTHLY BUDGET
# -------------------------------------------------------------------
with tab3:
    st.title("📅 12-Month Expense Aggregator")
    
    df_exp = st.session_state.transactions[st.session_state.transactions["Type"] == "Expense"].copy()
    if not df_exp.empty:
        df_exp["Date"] = pd.to_datetime(df_exp["Date"])
        df_exp["Month"] = df_exp["Date"].dt.strftime('%b')
        
        pivot = df_exp.pivot_table(index=["Category", "Group"], columns="Month", values="Amount", aggfunc="sum", fill_value=0)
        pivot["Annual Total"] = pivot.sum(axis=1)
        st.dataframe(pivot.style.format(f"{currency}{{:,.2f}}"), use_container_width=True)
    else:
        st.info("No expense transactions recorded yet.")

# -------------------------------------------------------------------
# TAB 4: DEBT CALCULATOR
# -------------------------------------------------------------------
with tab4:
    st.title("🧊 Debt Payoff Estimator")
    
    df_debt = st.session_state.debts.copy()
    
    def calculate_payoff(row):
        balance, apr, pmpt = row["Balance"], row["APR (%)"] / 100, row["Min Payment"]
        monthly_rate = apr / 12
        if pmpt <= balance * monthly_rate:
            return "Payment Too Low"
        months = balance / (pmpt - (balance * monthly_rate))
        return round(months, 1)

    df_debt["Est. Payoff (Months)"] = df_debt.apply(calculate_payoff, axis=1)
    st.dataframe(df_debt.style.format({"Balance": f"{currency}{{:,.2f}}", "Min Payment": f"{currency}{{:,.2f}}", "APR (%)": "{:.2f}%"}), use_container_width=True)

# -------------------------------------------------------------------
# TAB 5: NET WORTH TRACKER
# -------------------------------------------------------------------
with tab5:
    st.title("📈 Net Worth Overview")
    
    tot_assets = st.session_state.assets["Value"].sum()
    tot_liab = st.session_state.liabilities["Value"].sum()
    net_worth = tot_assets - tot_liab

    ca, cl = st.columns(2)
    ca.metric("Total Assets", f"{currency}{tot_assets:,.2f}")
    cl.metric("Total Liabilities", f"{currency}{tot_liab:,.2f}")
    st.metric("CURRENT NET WORTH", f"{currency}{net_worth:,.2f}", delta=f"{currency}{net_worth:,.2f}")

    col_a, col_l = st.columns(2)
    with col_a:
        st.subheader("Assets")
        st.dataframe(st.session_state.assets.style.format({"Value": f"{currency}{{:,.2f}}"}), use_container_width=True)
    with col_l:
        st.subheader("Liabilities")
        st.dataframe(st.session_state.liabilities.style.format({"Value": f"{currency}{{:,.2f}}"}), use_container_width=True)
