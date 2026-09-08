# 💰 Annual Smart Budget Tracker (Streamlit Edition)

A self-contained personal finance dashboard: transaction tracking, 50/30/20
budgeting, a 12-month expense aggregator, a debt payoff calculator, and a
net worth tracker with history — all in one app, no database setup required.

## Quick Start

1. Install Python 3.9 or newer.
2. Open a terminal in this folder and install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Run the app:
   ```
   streamlit run app.py
   ```
4. Your browser will open automatically to `http://localhost:8501`.

## How Your Data Is Saved

The first time you run the app, it creates a `data/` folder next to `app.py`
containing plain CSV and JSON files (transactions, debts, assets,
liabilities, category settings, net worth history). Every edit — adding a
transaction, editing a table cell, changing your currency — saves to these
files immediately. Closing the browser or restarting the app never loses
your data; only deleting the `data/` folder does.

**To back up your data:** copy the `data/` folder somewhere safe.
**To start fresh:** use the "Reset All Data" button on the Setup &
Categories tab, or delete the `data/` folder and restart the app.

## Features

- **Dashboard** — starting balance, income, expenses, savings, and net
  cashflow at a glance, a live 50/30/20 breakdown chart, and a running
  balance trend line.
- **Transactions Log** — guided add-transaction form plus a fully editable,
  sortable table (add or delete rows directly); one-click CSV export.
- **Monthly Budget** — 12-month expense aggregation per category, with
  editable annual targets and a "Remaining" column.
- **Debt Calculator** — Avalanche or Snowball payoff ordering, estimated
  payoff timeline, and total interest per debt, with a safeguard against
  impossible payment schedules (flags "Payment Too Low" instead of
  crashing or showing negative months).
- **Net Worth Tracker** — editable assets/liabilities tables, one-click
  snapshot logging, and a net worth trend chart over time.
- **Setup & Categories** — change currency, starting balance, payday cycle,
  and budget year; fully customize income and expense categories and their
  50/30/20 group assignments; download a backup or reset all data.

## Deploying Online (Optional)

This app also runs on [Streamlit Community Cloud](https://streamlit.io/cloud)
or any host that supports Streamlit. Keep in mind that on most free hosts
the filesystem is **not persistent** across restarts/redeploys — the CSV
storage here is built for a single local user or a host with a persistent
disk. For a shared multi-user deployment, swap the CSV helpers near the top
of `app.py` for a real database (SQLite is a drop-in first step).

## License / Resale Note

This file is provided to the purchaser for personal or client use as
licensed at the point of sale. Redistribution of the source code itself
(reselling it as-is on another marketplace) is not permitted unless your
license explicitly grants resale rights.
