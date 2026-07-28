import argparse
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
from tabulate import tabulate
from config import fetch_table_df

def run_summary_analysis(period: str = "monthly", days: int = None, export_chart: bool = False):

    print(f"\n=========================================")
    print(f"   FINANCIAL SUMMARY REPORT ({period.upper()})")
    print(f"=========================================\n")
    
    # 1. Fetch data
    df = fetch_table_df("unified_register_v")
    if df.empty:
        print("No transaction data found.")
        return

    df['date'] = pd.to_datetime(df['date'])
    df['amount'] = pd.to_numeric(df['amount'], errors='coerce').fillna(0)

    # 2. Apply Date Filtering
    now = datetime.now()
    if days:
        start_date = now - timedelta(days=days)
    elif period == "weekly":
        start_date = now - timedelta(days=7)
    elif period == "monthly":
        start_date = now - timedelta(days=30)
    elif period == "yearly":
        start_date = now - timedelta(days=365)
    else:
        start_date = df['date'].min()

    filtered_df = df[df['date'] >= start_date].copy()

    # 3. Overall Totals
    income_df = filtered_df[filtered_df['type'] == 'Income']
    expense_df = filtered_df[filtered_df['type'] == 'Expense']

    total_income = income_df['amount'].sum()
    total_expense = expense_df['amount'].sum()
    net_cash_flow = total_income - total_expense
    savings_rate = (net_cash_flow / total_income * 100) if total_income > 0 else 0

    overview_data = [
        ["Total Income", f"{total_income:,.2f} BDT"],
        ["Total Expenses", f"{total_expense:,.2f} BDT"],
        ["Net Cash Flow", f"{net_cash_flow:,.2f} BDT"],
        ["Savings Rate", f"{savings_rate:.1f}%"],
        ["Transaction Count", len(filtered_df)]
    ]
    print("--- Executive Overview ---")
    print(tabulate(overview_data, headers=["Metric", "Value"], tablefmt="fancy_grid"))
    print("\n")

    # 4. Category Breakdown (Expenses)
    if not expense_df.empty:
        cat_summary = expense_df.groupby('category')['amount'].agg(['sum', 'count']).reset_index()
        cat_summary.columns = ['Category', 'Total Spent (BDT)', 'Tx Count']
        cat_summary['% of Expenses'] = (cat_summary['Total Spent (BDT)'] / total_expense * 100).round(1)
        cat_summary = cat_summary.sort_values(by='Total Spent (BDT)', ascending=False)

        print("--- Top Expense Categories ---")
        print(tabulate(cat_summary, headers="keys", tablefmt="github", showindex=False))
        print("\n")

    # 5. Tag Breakdown
    tag_rows = []
    for _, row in expense_df.iterrows():
        tags = row['tags']
        if isinstance(tags, list):
            for t in tags:
                tag_rows.append({'tag': t, 'amount': row['amount']})

    if tag_rows:
        tag_df = pd.DataFrame(tag_rows)
        tag_summary = tag_df.groupby('tag')['amount'].agg(['sum', 'count']).reset_index()
        tag_summary.columns = ['Tag', 'Total Spent (BDT)', 'Tx Count']
        tag_summary['% of Expenses'] = (tag_summary['Total Spent (BDT)'] / total_expense * 100).round(1)
        tag_summary = tag_summary.sort_values(by='Total Spent (BDT)', ascending=False).head(10)

        print("--- Top 10 Expense Tags ---")
        print(tabulate(tag_summary, headers="keys", tablefmt="github", showindex=False))
        print("\n")

    # 6. Wallet Balances
    wallets_df = fetch_table_df("wallet_balances_vw")
    if not wallets_df.empty:
        wallets_df['balance'] = pd.to_numeric(wallets_df['balance'], errors='coerce').fillna(0)
        wallets_df = wallets_df[['name', 'balance']].sort_values(by='balance', ascending=False)
        print("--- Current Live Wallet Balances ---")
        print(tabulate(wallets_df, headers=["Wallet", "Balance (BDT)"], tablefmt="fancy_grid"))
        print("\n")

    # 7. Optional Chart Generation
    if export_chart and not expense_df.empty:
        try:
            import matplotlib.pyplot as plt
            charts_dir = Path(__file__).resolve().parent / "charts"
            charts_dir.mkdir(exist_ok=True)

            # Category Pie Chart
            fig, ax = plt.subplots(figsize=(8, 6))
            top_cats = cat_summary.head(6)
            ax.pie(top_cats['Total Spent (BDT)'], labels=top_cats['Category'], autopct='%1.1f%%', startangle=140)
            ax.set_title(f"Expense Breakdown by Category ({period.capitalize()})")
            plt.tight_layout()
            chart_path = charts_dir / f"expense_breakdown_{period}.png"
            plt.savefig(chart_path, dpi=200)
            plt.close()
            print(f"📊 Saved chart to: {chart_path}")
        except Exception as e:
            print(f"Failed to generate chart: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Financial Database Summary Analytics")
    parser.add_argument("--period", choices=["weekly", "monthly", "yearly", "all"], default="monthly", help="Period to analyze")
    parser.add_argument("--days", type=int, help="Custom number of days to analyze")
    parser.add_argument("--chart", action="store_true", help="Export PNG charts to analysis/charts/")
    args = parser.parse_args()

    run_summary_analysis(period=args.period, days=args.days, export_chart=args.chart)

