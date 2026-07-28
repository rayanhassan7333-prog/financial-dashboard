import argparse
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
from tabulate import tabulate
from config import fetch_table_df

def get_net_worth_trends(export_chart: bool = False) -> dict:
    wallets_df = fetch_table_df("wallet_balances_vw")
    liquid_cash = 0.0
    if not wallets_df.empty:
        wallets_df['balance'] = pd.to_numeric(wallets_df['balance'], errors='coerce').fillna(0)
        liquid_cash = float(wallets_df['balance'].sum())

    loans_df = fetch_table_df("loans_receivable_v")
    total_receivables = 0.0
    if not loans_df.empty:
        loans_df['outstanding'] = pd.to_numeric(loans_df['outstanding'], errors='coerce').fillna(0)
        total_receivables = float(loans_df['outstanding'].sum())

    invest_df = fetch_table_df("investment_summary_v")
    total_investments = 0.0
    if not invest_df.empty:
        if 'outstanding' in invest_df.columns:
            invest_df['outstanding'] = pd.to_numeric(invest_df['outstanding'], errors='coerce').fillna(0)
            total_investments = float(invest_df['outstanding'].sum())
        elif 'invested' in invest_df.columns:
            invest_df['invested'] = pd.to_numeric(invest_df['invested'], errors='coerce').fillna(0)
            total_investments = float(invest_df['invested'].sum())

    total_net_worth = liquid_cash + total_receivables + total_investments

    # Routine monthly expenses (excluding extraordinary capital items > 10k or Loans & Debt)
    df = fetch_table_df("unified_register_v")
    routine_monthly_expense_avg = 0.0
    if not df.empty:
        df['date'] = pd.to_datetime(df['date'])
        df['amount'] = pd.to_numeric(df['amount'], errors='coerce').fillna(0)
        cutoff = datetime.now() - timedelta(days=60)
        recent_expenses = df[(df['date'] >= cutoff) & (df['type'] == 'Expense')]
        
        def is_routine(row):
            cat = str(row.get('category', ''))
            tags = row.get('tags')
            tags_list = tags if isinstance(tags, list) else []
            amt = float(row.get('amount', 0))
            if cat == 'Loans & Debt' or 'DevicesBuy' in tags_list or (cat == 'General Shop' and amt > 10000):
                return False
            return True

        routine = recent_expenses[recent_expenses.apply(is_routine, axis=1)]
        routine_monthly_expense_avg = float((routine['amount'].sum() / 60.0) * 30.0)

    liquidity_runway_months = (liquid_cash / routine_monthly_expense_avg) if routine_monthly_expense_avg > 0 else 0.0

    health_status = "✅ Strong Liquidity (> 3 Months)" if liquidity_runway_months >= 3.0 else (
        "⚠️ Moderate Buffer (1-3 Months)" if liquidity_runway_months >= 1.0 else "🚨 Tight Liquidity (< 1 Month)"
    )

    chart_path = None
    if export_chart:
        try:
            import matplotlib.pyplot as plt
            charts_dir = Path(__file__).resolve().parent / "charts"
            charts_dir.mkdir(exist_ok=True)

            fig, ax = plt.subplots(figsize=(7, 5))
            labels = ['Liquid Cash', 'Receivables', 'Investments']
            values = [liquid_cash, total_receivables, total_investments]
            
            labels = [l for l, v in zip(labels, values) if v > 0]
            values = [v for v in values if v > 0]

            if values:
                ax.pie(values, labels=labels, autopct='%1.1f%%', startangle=140, colors=['#2ecc71', '#f39c12', '#3498db'])
                ax.set_title("Net Worth Asset Allocation")
                plt.tight_layout()
                chart_file = charts_dir / "net_worth_allocation.png"
                plt.savefig(chart_file, dpi=200)
                plt.close()
                chart_path = str(chart_file)
        except Exception as e:
            print(f"Failed to generate chart: {e}")

    return {
        "liquid_cash": liquid_cash,
        "total_receivables": total_receivables,
        "total_investments": total_investments,
        "total_net_worth": total_net_worth,
        "monthly_expense_avg": routine_monthly_expense_avg,
        "liquidity_runway_months": liquidity_runway_months,
        "health_status": health_status,
        "wallets_df": wallets_df,
        "chart_path": chart_path
    }

def run_net_worth_trends(export_chart: bool = False):
    print(f"\n=========================================")
    print(f"   NET WORTH TRAJECTORY & LIQUIDITY HEALTH")
    print(f"=========================================\n")

    res = get_net_worth_trends(export_chart=export_chart)
    liquid_cash = res['liquid_cash']
    total_receivables = res['total_receivables']
    total_investments = res['total_investments']
    total_net_worth = res['total_net_worth']

    asset_alloc_table = [
        ["Liquid Cash & Bank Wallets", f"{liquid_cash:,.2f} BDT", f"{(liquid_cash/total_net_worth*100):.1f}%" if total_net_worth > 0 else "0%"],
        ["Outstanding Receivables (Loans)", f"{total_receivables:,.2f} BDT", f"{(total_receivables/total_net_worth*100):.1f}%" if total_net_worth > 0 else "0%"],
        ["Investments Portfolio", f"{total_investments:,.2f} BDT", f"{(total_investments/total_net_worth*100):.1f}%" if total_net_worth > 0 else "0%"],
        ["---------------------------------", "--------------------", "----------"],
        ["TOTAL NET WORTH", f"{total_net_worth:,.2f} BDT", "100.0%"]
    ]

    print("--- Current Asset Distribution & Net Worth ---")
    print(tabulate(asset_alloc_table, headers=["Asset Class", "Value (BDT)", "Allocation %"], tablefmt="fancy_grid"))
    print("\n")

    health_table = [
        ["Liquid Cash Balance", f"{liquid_cash:,.2f} BDT"],
        ["Avg Routine Monthly Living Expense", f"{res['monthly_expense_avg']:,.2f} BDT/month"],
        ["Liquidity Buffer Runway", f"{res['liquidity_runway_months']:.1f} Months"],
        ["Liquidity Health Rating", res['health_status']]
    ]

    print("--- Liquidity Health & Buffer Analysis ---")
    print(tabulate(health_table, headers=["Metric", "Value"], tablefmt="fancy_grid"))
    print("\n")

    if res['chart_path']:
        print(f"📊 Saved chart to: {res['chart_path']}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Net Worth Trajectory & Liquidity Health")
    parser.add_argument("--chart", action="store_true", help="Export PNG charts")
    args = parser.parse_args()

    run_net_worth_trends(export_chart=args.chart)
