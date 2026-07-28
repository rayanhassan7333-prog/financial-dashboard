import argparse
from datetime import datetime, timedelta
import pandas as pd
from tabulate import tabulate
from config import fetch_table_df

TUITION_SCHEDULE = [
    {"name": "Tuition: Nabiha", "monthly_rate": 8000.0, "notes": "Expected by end of month"},
    {"name": "Tuition: Ayesha", "monthly_rate": 9000.0, "notes": "Expected by end of month"},
    {"name": "Tuition: Mayan",  "monthly_rate": 8000.0, "notes": "Expected by end of month"}
]

def run_cashflow_forecast(lookback_days: int = 60, forecast_days: int = 30):
    print(f"\n=========================================")
    print(f"   CASH FLOW & RUNWAY FORECAST ({forecast_days} DAYS)")
    print(f"=========================================\n")

    # 1. Get Current Total Liquid Assets
    wallets_df = fetch_table_df("wallet_balances_vw")
    if wallets_df.empty:
        print("Error: Could not retrieve wallet balances.")
        return

    wallets_df['balance'] = pd.to_numeric(wallets_df['balance'], errors='coerce').fillna(0)
    current_cash = wallets_df['balance'].sum()

    # 2. Historical Daily Burn Rate
    df = fetch_table_df("unified_register_v")
    df['date'] = pd.to_datetime(df['date'])
    df['amount'] = pd.to_numeric(df['amount'], errors='coerce').fillna(0)

    cutoff = datetime.now() - timedelta(days=lookback_days)
    recent_expenses = df[(df['date'] >= cutoff) & (df['type'] == 'Expense')]
    
    total_recent_expense = recent_expenses['amount'].sum()
    daily_burn_rate = total_recent_expense / lookback_days if lookback_days > 0 else 0

    # 3. Active Subscriptions Overhead
    sub_df = fetch_table_df("active_recur_bills")
    monthly_sub_cost = 0.0
    if not sub_df.empty:
        sub_df['amount'] = pd.to_numeric(sub_df['amount'], errors='coerce').fillna(0)
        monthly_sub_cost = sub_df['amount'].sum()

    # 4. Expected Tuition Income (Monthly)
    monthly_tuition_income = sum(item["monthly_rate"] for item in TUITION_SCHEDULE)
    months_in_forecast = forecast_days / 30.0

    projected_tuition_revenue = monthly_tuition_income * months_in_forecast
    projected_variable_expenses = daily_burn_rate * forecast_days
    projected_subscriptions = (monthly_sub_cost / 30.0) * forecast_days

    total_projected_expenses = projected_variable_expenses + projected_subscriptions
    projected_net_cash_flow = projected_tuition_revenue - total_projected_expenses
    projected_ending_balance = current_cash + projected_net_cash_flow

    # 5. Loan Recovery Potential
    loans_df = fetch_table_df("loans_receivable_v")
    total_receivables = 0.0
    if not loans_df.empty:
        loans_df['outstanding'] = pd.to_numeric(loans_df['outstanding'], errors='coerce').fillna(0)
        total_receivables = loans_df['outstanding'].sum()

    # Summary Output
    summary_table = [
        ["Current Liquid Assets", f"{current_cash:,.2f} BDT"],
        [f"Avg Daily Burn Rate (Last {lookback_days}d)", f"{daily_burn_rate:,.2f} BDT/day"],
        [f"Projected Tuition Revenue ({forecast_days}d)", f"+{projected_tuition_revenue:,.2f} BDT"],
        [f"Projected Variable Expenses ({forecast_days}d)", f"-{projected_variable_expenses:,.2f} BDT"],
        [f"Projected Subscription Expenses ({forecast_days}d)", f"-{projected_subscriptions:,.2f} BDT"],
        ["----------------------------", "--------------------"],
        [f"Projected Net Cash Flow", f"{projected_net_cash_flow:+,.2f} BDT"],
        [f"Projected Ending Balance ({forecast_days}d)", f"{projected_ending_balance:,.2f} BDT"],
        ["Outstanding Loan Receivables", f"{total_receivables:,.2f} BDT"]
    ]

    print("--- 30-Day Forecast Model ---")
    print(tabulate(summary_table, headers=["Parameter", "Amount"], tablefmt="fancy_grid"))
    print("\n")

    # Tuition breakdown
    tuition_table = [[t["name"], f"{t['monthly_rate']:,.2f} BDT", t["notes"]] for t in TUITION_SCHEDULE]
    print("--- Expected Tuition Income Reference ---")
    print(tabulate(tuition_table, headers=["Tuition", "Monthly Rate", "Schedule"], tablefmt="github"))
    print("\n")

    # Runway calculation
    net_daily_change = (monthly_tuition_income - (monthly_sub_cost + daily_burn_rate * 30)) / 30.0
    if net_daily_change < 0:
        runway_days = current_cash / abs(net_daily_change)
        print(f"⚠️ Warning: Net cash flow is negative. Estimated cash runway: ~{int(runway_days)} days.")
    else:
        print(f"✅ Cash Flow Positive: Projected surplus of {net_daily_change * 30:,.2f} BDT/month.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cash Flow & Runway Forecast")
    parser.add_argument("--lookback", type=int, default=60, help="Days to calculate burn rate (default 60)")
    parser.add_argument("--forecast", type=int, default=30, help="Forecast horizon in days (default 30)")
    args = parser.parse_args()

    run_cashflow_forecast(lookback_days=args.lookback, forecast_days=args.forecast)
