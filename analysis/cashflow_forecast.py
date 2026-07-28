import argparse
from datetime import datetime, timedelta
import pandas as pd
from tabulate import tabulate
from config import fetch_table_df

TUITION_FORECAST_SCHEDULE = [
    {"name": "Tuition: Nabiha", "rate_30d": 8000.0, "notes": "Regular monthly payment"},
    {"name": "Tuition: Ayesha", "rate_30d": 0.0, "notes": "All clear (July skipped)"},
    {"name": "Tuition: Mayan",  "rate_30d": 24000.0, "notes": "June + July pending recovery (12k/mo)"}
]

def get_cashflow_forecast(lookback_days: int = 60, forecast_days: int = 30) -> dict:
    # 1. Liquid Assets
    wallets_df = fetch_table_df("wallet_balances_vw")
    if wallets_df.empty:
        return {}

    wallets_df['balance'] = pd.to_numeric(wallets_df['balance'], errors='coerce').fillna(0)
    current_cash = float(wallets_df['balance'].sum())

    # 2. Historical Routine Daily Burn Rate (Excluding one-off extraordinary capital spend & loan repayments)
    df = fetch_table_df("unified_register_v")
    df['date'] = pd.to_datetime(df['date'])
    df['amount'] = pd.to_numeric(df['amount'], errors='coerce').fillna(0)

    cutoff = datetime.now() - timedelta(days=lookback_days)
    recent_expenses = df[(df['date'] >= cutoff) & (df['type'] == 'Expense')].copy()
    
    # Filter out one-off capital purchases (e.g. DevicesBuy > 10,000 BDT) and Loans & Debt repayments
    def is_routine_expense(row):
        cat = str(row.get('category', ''))
        tags = row.get('tags')
        tags_list = tags if isinstance(tags, list) else []
        amt = float(row.get('amount', 0))

        if cat == 'Loans & Debt':
            return False
        if 'DevicesBuy' in tags_list or (cat == 'General Shop' and amt > 10000):
            return False
        return True

    routine_expenses = recent_expenses[recent_expenses.apply(is_routine_expense, axis=1)]
    total_routine_expense = float(routine_expenses['amount'].sum())
    daily_burn_rate = total_routine_expense / lookback_days if lookback_days > 0 else 0.0

    # 3. Active Subscriptions Overhead
    sub_df = fetch_table_df("active_recur_bills")
    monthly_sub_cost = 0.0
    if not sub_df.empty:
        sub_df['amount'] = pd.to_numeric(sub_df['amount'], errors='coerce').fillna(0)
        monthly_sub_cost = float(sub_df['amount'].sum())

    # 4. Projected Tuition Income in 30 Days
    projected_tuition_revenue = sum(item["rate_30d"] for item in TUITION_FORECAST_SCHEDULE)
    months_in_forecast = forecast_days / 30.0

    projected_variable_expenses = daily_burn_rate * forecast_days
    projected_subscriptions = (monthly_sub_cost / 30.0) * forecast_days if monthly_sub_cost > 0 else 334.79

    total_projected_expenses = projected_variable_expenses + projected_subscriptions
    projected_net_cash_flow = projected_tuition_revenue - total_projected_expenses
    projected_ending_balance = current_cash + projected_net_cash_flow

    loans_df = fetch_table_df("loans_receivable_v")
    total_receivables = 0.0
    if not loans_df.empty:
        loans_df['outstanding'] = pd.to_numeric(loans_df['outstanding'], errors='coerce').fillna(0)
        total_receivables = float(loans_df['outstanding'].sum())

    is_positive = projected_net_cash_flow >= 0
    net_daily_change = projected_net_cash_flow / forecast_days
    runway_days = (current_cash / abs(net_daily_change)) if not is_positive and abs(net_daily_change) > 0 else 999.0

    return {
        "lookback_days": lookback_days,
        "forecast_days": forecast_days,
        "current_cash": current_cash,
        "daily_burn_rate": daily_burn_rate,
        "monthly_sub_cost": monthly_sub_cost,
        "projected_tuition_revenue": projected_tuition_revenue,
        "projected_variable_expenses": projected_variable_expenses,
        "projected_subscriptions": projected_subscriptions,
        "projected_net_cash_flow": projected_net_cash_flow,
        "projected_ending_balance": projected_ending_balance,
        "total_receivables": total_receivables,
        "tuition_schedule": TUITION_FORECAST_SCHEDULE,
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
        [f"Routine Daily Burn Rate ({lookback_days}d avg)", f"{res['daily_burn_rate']:,.2f} BDT/day"],
        [f"Projected Tuition Revenue ({forecast_days}d)", f"+{res['projected_tuition_revenue']:,.2f} BDT"],
        [f"Projected Routine Expenses ({forecast_days}d)", f"-{res['projected_variable_expenses']:,.2f} BDT"],
        [f"Projected Subscriptions ({forecast_days}d)", f"-{res['projected_subscriptions']:,.2f} BDT"],
        ["----------------------------", "--------------------"],
        [f"Projected Net Cash Flow", f"{res['projected_net_cash_flow']:+,.2f} BDT"],
        [f"Projected Ending Balance ({forecast_days}d)", f"{res['projected_ending_balance']:,.2f} BDT"],
        ["Outstanding Loan Receivables", f"{res['total_receivables']:,.2f} BDT"]
    ]

    print(f"--- {forecast_days}-Day Forecast Model ---")
    print(tabulate(summary_table, headers=["Parameter", "Amount"], tablefmt="fancy_grid"))
    print("\n")

    tuition_table = [[t["name"], f"{t['rate_30d']:,.2f} BDT", t["notes"]] for t in TUITION_FORECAST_SCHEDULE]
    print("--- Expected 30-Day Tuition Income Schedule ---")
    print(tabulate(tuition_table, headers=["Tuition", "30-Day Expected", "Notes"], tablefmt="github"))
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
