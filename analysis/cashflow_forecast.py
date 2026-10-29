import argparse
from datetime import datetime, timedelta
import calendar
import re
import pandas as pd
from tabulate import tabulate
from config import fetch_table_df
from receivables_aging import TUITION_CONFIG, get_rate_for_month, get_receivables_aging


def get_end_of_next_month(from_date: datetime) -> datetime:
    """Calculate the last day of the next calendar month."""
    y = from_date.year
    m = from_date.month
    
    # Next month
    if m == 12:
        next_y = y + 1
        next_m = 1
    else:
        next_y = y
        next_m = m + 1

    last_day = calendar.monthrange(next_y, next_m)[1]
    return datetime(next_y, next_m, last_day, 23, 59, 59)


def get_cashflow_forecast(lookback_days: int = 60, target_date: datetime = None) -> dict:
    now = datetime.now()
    
    if target_date is None:
        target_date = get_end_of_next_month(now)

    forecast_days = max(1, (target_date - now).days)
    target_date_str = target_date.strftime("%Y-%m-%d")
    target_label = target_date.strftime("%b %d, %Y")

    # -----------------------------------------------------------------
    # 1. Liquid Assets
    # -----------------------------------------------------------------
    wallets_df = fetch_table_df("wallet_balances_vw")
    if wallets_df.empty:
        return {}

    wallets_df['balance'] = pd.to_numeric(wallets_df['balance'], errors='coerce').fillna(0)
    if 'account_type' in wallets_df.columns:
        current_cash = float(wallets_df[wallets_df['account_type'] == 'personal']['balance'].sum())
    else:
        current_cash = float(wallets_df['balance'].sum())

    # -----------------------------------------------------------------
    # 2. Historical Routine Daily Burn Rate
    # -----------------------------------------------------------------
    df = fetch_table_df("unified_register_v")
    df['date'] = pd.to_datetime(df['date'])
    df['amount'] = pd.to_numeric(df['amount'], errors='coerce').fillna(0)

    cutoff = now - timedelta(days=lookback_days)
    recent_expenses = df[(df['date'] >= cutoff) & (df['type'] == 'Expense')].copy()

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

    # -----------------------------------------------------------------
    # 3. Active Subscriptions Overhead (Normalized to Monthly Rate)
    # -----------------------------------------------------------------
    sub_df = fetch_table_df("active_recur_bills")
    monthly_sub_cost = 0.0
    if not sub_df.empty:
        sub_df['amount'] = pd.to_numeric(sub_df['amount'], errors='coerce').fillna(0)
        for _, row in sub_df.iterrows():
            amt = float(row.get('amount', 0))
            if amt <= 0:
                continue
            dur = str(row.get('duration', '')).lower()
            start_d = pd.to_datetime(row.get('start_date')) if pd.notnull(row.get('start_date')) else None
            end_d = pd.to_datetime(row.get('end_date')) if pd.notnull(row.get('end_date')) else None

            months = 1.0
            if 'year' in dur:
                nums = re.findall(r'\d+', dur)
                months = float(nums[0]) * 12.0 if nums else 12.0
            elif 'month' in dur:
                nums = re.findall(r'\d+', dur)
                months = float(nums[0]) if nums else 1.0
            elif 'day' in dur:
                nums = re.findall(r'\d+', dur)
                days = float(nums[0]) if nums else 30.0
                months = max(1.0, days / 30.0)
            elif start_d and end_d and end_d > start_d:
                months = max(1.0, (end_d - start_d).days / 30.4)

            monthly_sub_cost += (amt / months)

    # -----------------------------------------------------------------
    # 4. Projected Tuition Revenue up to Target End Date
    #    Combines pending YTD tuition + expected upcoming tuition through target_date
    # -----------------------------------------------------------------
    tuition_schedule_detail = []
    projected_tuition_revenue = 0.0

    # Fetch current receivables to get exact pending amounts per student
    receivables_res = get_receivables_aging(export_chart=False)
    tuition_summary = receivables_res.get("tuition_summary", [])

    for key, config in TUITION_CONFIG.items():
        # 1. Outstanding pending tuition up to current month
        pending_amt = 0.0
        for s in tuition_summary:
            if s.get("key") == key and s.get("diff", 0) < 0:
                pending_amt = abs(s.get("diff"))

        # 2. Upcoming tuition between next month start and target_date
        upcoming_amt = 0.0
        month_details = []

        if pending_amt > 0:
            month_details.append(f"Pending:{pending_amt:,.0f}")

        # Check months from current ongoing month (now.month) up to target_date
        check_y = now.year
        check_m = now.month

        while datetime(check_y, check_m, 1) <= target_date:
            rate = get_rate_for_month(config, check_y, check_m)
            if rate > 0:
                upcoming_amt += rate
                m_name = datetime(check_y, check_m, 1).strftime("%b")
                month_details.append(f"{m_name}:{rate:,.0f}")

            if check_m == 12:
                check_y += 1
                check_m = 1
            else:
                check_m += 1

        total_student_projected = pending_amt + upcoming_amt
        projected_tuition_revenue += total_student_projected

        notes = f"Months: {', '.join(month_details)}" if month_details else "No session in window"
        tuition_schedule_detail.append({
            "name": config['name'],
            "rate_30d": total_student_projected,
            "notes": notes
        })

    # -----------------------------------------------------------------
    # 5. Projected Loan Repayments Inflow
    # -----------------------------------------------------------------
    loans_df = fetch_table_df("loans_receivable_v")
    total_receivables = 0.0
    if not loans_df.empty:
        loans_df['outstanding'] = pd.to_numeric(loans_df['outstanding'], errors='coerce').fillna(0)
        total_receivables = float(loans_df['outstanding'].sum())

    waraka_info = receivables_res.get("waraka_analysis", {})
    waraka_outstanding = float(waraka_info.get("outstanding", 0.0))
    avg_repayment = float(waraka_info.get("avg_monthly_repayment", 0.0))

    # Only project loan repayments up to remaining outstanding balance
    projected_loan_revenue = min(avg_repayment, waraka_outstanding) if waraka_outstanding > 0 else 0.0

    # -----------------------------------------------------------------
    # 6. Forecast Calculations
    # -----------------------------------------------------------------
    projected_variable_expenses = daily_burn_rate * forecast_days
    projected_subscriptions = (monthly_sub_cost / 30.0) * forecast_days if monthly_sub_cost > 0 else 0.0

    total_projected_inflows = projected_tuition_revenue + projected_loan_revenue
    total_projected_expenses = projected_variable_expenses + projected_subscriptions
    projected_net_cash_flow = total_projected_inflows - total_projected_expenses
    projected_ending_balance = current_cash + projected_net_cash_flow

    loans_df = fetch_table_df("loans_receivable_v")
    total_receivables = 0.0
    if not loans_df.empty:
        loans_df['outstanding'] = pd.to_numeric(loans_df['outstanding'], errors='coerce').fillna(0)
        total_receivables = float(loans_df['outstanding'].sum())

    is_positive = projected_net_cash_flow >= 0
    net_daily_change = projected_net_cash_flow / forecast_days if forecast_days > 0 else 0
    runway_days = (current_cash / abs(net_daily_change)) if not is_positive and abs(net_daily_change) > 0 else 999.0

    return {
        "lookback_days": lookback_days,
        "forecast_days": forecast_days,
        "target_date_str": target_date_str,
        "target_label": target_label,
        "current_cash": current_cash,
        "daily_burn_rate": daily_burn_rate,
        "monthly_sub_cost": monthly_sub_cost,
        "projected_tuition_revenue": projected_tuition_revenue,
        "projected_loan_revenue": projected_loan_revenue,
        "projected_variable_expenses": projected_variable_expenses,
        "projected_subscriptions": projected_subscriptions,
        "projected_net_cash_flow": projected_net_cash_flow,
        "projected_ending_balance": projected_ending_balance,
        "total_receivables": total_receivables,
        "tuition_schedule": tuition_schedule_detail,
        "is_positive": is_positive,
        "runway_days": runway_days
    }


def run_cashflow_forecast(lookback_days: int = 60):
    now = datetime.now()
    target_date = get_end_of_next_month(now)
    res = get_cashflow_forecast(lookback_days=lookback_days, target_date=target_date)
    if not res:
        print("Error: Could not retrieve wallet balances.")
        return

    print(f"\n=========================================")
    print(f"   CASH FLOW FORECAST (TO {res['target_label'].upper()})")
    print(f"=========================================\n")

    summary_table = [
        ["Current Liquid Assets", f"{res['current_cash']:,.2f} BDT"],
        [f"Routine Daily Burn Rate ({lookback_days}d avg)", f"{res['daily_burn_rate']:,.2f} BDT/day"],
        [f"Projected Tuition Inflow (to {res['target_label']})", f"+{res['projected_tuition_revenue']:,.2f} BDT"],
        [f"Projected Loan Repayments", f"+{res['projected_loan_revenue']:,.2f} BDT" if res['projected_loan_revenue'] > 0 else "0.00 BDT (All loans cleared)"],
        [f"Projected Routine Expenses ({res['forecast_days']}d)", f"-{res['projected_variable_expenses']:,.2f} BDT"],
        [f"Projected Subscriptions ({res['forecast_days']}d)", f"-{res['projected_subscriptions']:,.2f} BDT"],
        ["----------------------------", "--------------------"],
        [f"Projected Net Cash Flow", f"{res['projected_net_cash_flow']:+,.2f} BDT"],
        [f"Projected Ending Balance ({res['target_label']})", f"{res['projected_ending_balance']:,.2f} BDT"],
        ["Outstanding Loan Receivables", f"{res['total_receivables']:,.2f} BDT"]
    ]

    print(f"--- Forecast Model to {res['target_label']} ---")
    print(tabulate(summary_table, headers=["Parameter", "Amount"], tablefmt="fancy_grid"))
    print("\n")

    tuition_table = [[t["name"], f"{t['rate_30d']:,.2f} BDT", t["notes"]] for t in res['tuition_schedule']]
    print(f"--- Expected Tuition Inflow Schedule (to {res['target_label']}) ---")
    print(tabulate(tuition_table, headers=["Tuition", "Expected Inflow", "Notes"], tablefmt="github"))
    print("\n")

    if not res['is_positive']:
        print(f"⚠️ Warning: Net cash flow is negative. Estimated cash runway: ~{int(res['runway_days'])} days.")
    else:
        print(f"✅ Cash Flow Positive: Projected surplus of {res['projected_net_cash_flow']:,.2f} BDT by {res['target_label']}.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cash Flow & Runway Forecast")
    parser.add_argument("--lookback", type=int, default=60, help="Days to calculate burn rate (default 60)")
    args = parser.parse_args()

    run_cashflow_forecast(lookback_days=args.lookback)
