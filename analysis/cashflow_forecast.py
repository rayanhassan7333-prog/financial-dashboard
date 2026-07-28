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

def get_cashflow_forecast(lookback_days: int = 60, forecast_days: int = 30) -> dict:
    wallets_df = fetch_table_df("wallet_balances_vw")
    if wallets_df.empty:
        return {}

    wallets_df['balance'] = pd.to_numeric(wallets_df['balance'], errors='coerce').fillna(0)
    current_cash = float(wallets_df['balance'].sum())

    df = fetch_table_df("unified_register_v")
    df['date'] = pd.to_datetime(df['date'])
    df['amount'] = pd.to_numeric(df['amount'], errors='coerce').fillna(0)

    cutoff = datetime.now() - timedelta(days=lookback_days)
    recent_expenses = df[(df['date'] >= cutoff) & (df['type'] == 'Expense')]
    
    total_recent_expense = float(recent_expenses['amount'].sum())
    daily_burn_rate = total_recent_expense / lookback_days if lookback_days > 0 else 0.0

    sub_df = fetch_table_df("active_recur_bills")
    monthly_sub_cost = 0.0
    if not sub_df.empty:
        sub_df['amount'] = pd.to_numeric(sub_df['amount'], errors='coerce').fillna(0)
        monthly_sub_cost = float(sub_df['amount'].sum())

    monthly_tuition_income = sum(item["monthly_rate"] for item in TUITION_SCHEDULE)
    months_in_forecast = forecast_days / 30.0

    projected_tuition_revenue = monthly_tuition_income * months_in_forecast
    projected_variable_expenses = daily_burn_rate * forecast_days
    projected_subscriptions = (monthly_sub_cost / 30.0) * forecast_days

    total_projected_expenses = projected_variable_expenses + projected_subscriptions
    projected_net_cash_flow = projected_tuition_revenue - total_projected_expenses
    projected_ending_balance = current_cash + projected_net_cash_flow

    loans_df = fetch_table_df("loans_receivable_v")
    total_receivables = 0.0
    if not loans_df.empty:
        loans_df['outstanding'] = pd.to_numeric(loans_df['outstanding'], errors='coerce').fillna(0)
        total_receivables = float(loans_df['outstanding'].sum())

    net_daily_change = (monthly_tuition_income - (monthly_sub_cost + daily_burn_rate * 30)) / 30.0
    is_positive = net_daily_change >= 0
    runway_days = (current_cash / abs(net_daily_change)) if not is_positive and abs(net_daily_change) > 0 else 999.0

    return {
        "lookback_days": lookback_days,
        "forecast_days": forecast_days,
        "current_cash": current_cash,
        "daily_burn_rate": daily_burn_rate,
        "monthly_sub_cost": monthly_sub_cost,
        "monthly_tuition_income": monthly_tuition_income,
        "projected_tuition_revenue": projected_tuition_revenue,
        "projected_variable_expenses": projected_variable_expenses,
        "projected_subscriptions": projected_subscriptions,
        "projected_net_cash_flow": projected_net_cash_flow,
        "projected_ending_balance": projected_ending_balance,
        "total_receivables": total_receivables,
        "tuition_schedule": TUITION_SCHEDULE,
        "is_positive": is_positive,
        "runway_days": runway_days
    }

def run_cashflow_forecast(lookback_days: int = 60, forecast_days: int = 30):
    print(f"\n=========================================")
    print(f"   CASH FLOW & RUNWAY FORECAST ({forecast_days} DAYS)")
    print(f"=========================================\n")

    res = get_cashflow_forecast(lookback_days=lookback_days, forecast_days=forecast_days)
    if not res:
        print("Error: Could not retrieve wallet balances.")
        return

    summary_table = [
        ["Current Liquid Assets", f"{res['current_cash']:,.2f} BDT"],
        [f"Avg Daily Burn Rate (Last {lookback_days}d)", f"{res['daily_burn_rate']:,.2f} BDT/day"],
        [f"Projected Tuition Revenue ({forecast_days}d)", f"+{res['projected_tuition_revenue']:,.2f} BDT"],
        [f"Projected Variable Expenses ({forecast_days}d)", f"-{res['projected_variable_expenses']:,.2f} BDT"],
        [f"Projected Subscription Expenses ({forecast_days}d)", f"-{res['projected_subscriptions']:,.2f} BDT"],
        ["----------------------------", "--------------------"],
        [f"Projected Net Cash Flow", f"{res['projected_net_cash_flow']:+,.2f} BDT"],
        [f"Projected Ending Balance ({forecast_days}d)", f"{res['projected_ending_balance']:,.2f} BDT"],
        ["Outstanding Loan Receivables", f"{res['total_receivables']:,.2f} BDT"]
    ]

    print(f"--- {forecast_days}-Day Forecast Model ---")
    print(tabulate(summary_table, headers=["Parameter", "Amount"], tablefmt="fancy_grid"))
    print("\n")

    tuition_table = [[t["name"], f"{t['monthly_rate']:,.2f} BDT", t["notes"]] for t in TUITION_SCHEDULE]
    print("--- Expected Tuition Income Reference ---")
    print(tabulate(tuition_table, headers=["Tuition", "Monthly Rate", "Schedule"], tablefmt="github"))
    print("\n")

    if not res['is_positive']:
        print(f"⚠️ Warning: Net cash flow is negative. Estimated cash runway: ~{int(res['runway_days'])} days.")
    else:
        print(f"✅ Cash Flow Positive: Projected surplus of {res['projected_net_cash_flow']:,.2f} BDT/{forecast_days}d.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cash Flow & Runway Forecast")
    parser.add_argument("--lookback", type=int, default=60, help="Days to calculate burn rate (default 60)")
    parser.add_argument("--forecast", type=int, default=30, help="Forecast horizon in days (default 30)")
    args = parser.parse_args()

    run_cashflow_forecast(lookback_days=args.lookback, forecast_days=args.forecast)
