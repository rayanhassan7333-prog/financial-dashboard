import argparse
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
from tabulate import tabulate
from config import fetch_table_df

COMMUTE_TAGS = ['DailyCommute', 'CampusTrip', 'SocialTrip', 'TutorTrips', 'OtherCommute']

def run_commute_analytics(days: int = 60, export_chart: bool = False):
    print(f"\n=========================================")
    print(f"   COMMUTE & TUTOR TRAVEL EFFICIENCY REPORT ({days} DAYS)")
    print(f"=========================================\n")

    # 1. Fetch data
    df = fetch_table_df("unified_register_v")
    if df.empty:
        print("No transaction data available.")
        return

    df['date'] = pd.to_datetime(df['date'])
    df['amount'] = pd.to_numeric(df['amount'], errors='coerce').fillna(0)

    now = datetime.now()
    cutoff_date = now - timedelta(days=days)
    recent_df = df[df['date'] >= cutoff_date].copy()

    # 2. Extract Commute Transactions by Tag
    commute_rows = []
    expense_df = recent_df[recent_df['type'] == 'Expense']

    for _, row in expense_df.iterrows():
        tags = row.get('tags')
        if isinstance(tags, list):
            for t in tags:
                if t in COMMUTE_TAGS or 'commute' in t.lower() or 'trip' in t.lower():
                    commute_rows.append({
                        'date': row['date'],
                        'title': row['title'],
                        'amount': row['amount'],
                        'tag': t,
                        'wallet': row.get('wallet', 'Unknown')
                    })

    commute_df = pd.DataFrame(commute_rows)

    if not commute_df.empty:
        commute_summary = commute_df.groupby('tag')['amount'].agg(['sum', 'count', 'mean']).reset_index()
        commute_summary.columns = ['Commute Tag', 'Total Spent (BDT)', 'Trip Count', 'Avg Cost/Trip (BDT)']
        total_commute_spend = commute_summary['Total Spent (BDT)'].sum()
        commute_summary['% of Transport'] = (commute_summary['Total Spent (BDT)'] / total_commute_spend * 100).round(1)
        commute_summary = commute_summary.sort_values(by='Total Spent (BDT)', ascending=False)

        formatted_commute = []
        for _, row in commute_summary.iterrows():
            formatted_commute.append([
                row['Commute Tag'],
                f"{row['Total Spent (BDT)']:,.2f} BDT",
                int(row['Trip Count']),
                f"{row['Avg Cost/Trip (BDT)']:,.2f} BDT",
                f"{row['% of Transport']:.1f}%"
            ])

        print(f"--- Commute Breakdown by Trip Type (Last {days} Days) ---")
        print(tabulate(formatted_commute, headers=["Trip Type / Tag", "Total Spent", "Trips", "Avg Cost/Trip", "% Share"], tablefmt="fancy_grid"))
        print(f"Total Transport Expenditure: {total_commute_spend:,.2f} BDT\n")
    else:
        print("No commute tagged transactions found in the specified window.\n")
        total_commute_spend = 0.0

    # 3. Tutor Travel ROI & Net Tuition Yield
    income_df = recent_df[recent_df['type'] == 'Income']
    tuition_income_df = income_df[
        (income_df['category'].str.lower() == 'tuition') | 
        (income_df['title'].str.contains('Tuition|Nabiha|Ayesha|Mayan', case=False, na=False))
    ]

    gross_tuition_earned = tuition_income_df['amount'].sum()

    tutor_travel_cost = 0.0
    if not commute_df.empty and 'TutorTrips' in commute_df['tag'].values:
        tutor_travel_cost = commute_df[commute_df['tag'] == 'TutorTrips']['amount'].sum()

    net_tuition_revenue = gross_tuition_earned - tutor_travel_cost
    net_yield_pct = (net_tuition_revenue / gross_tuition_earned * 100) if gross_tuition_earned > 0 else 0.0

    roi_table = [
        ["Gross Tuition Revenue Earned", f"{gross_tuition_earned:,.2f} BDT"],
        ["Tutor Travel Transport Expenses (TutorTrips)", f"-{tutor_travel_cost:,.2f} BDT"],
        ["Net Tuition Revenue", f"{net_tuition_revenue:,.2f} BDT"],
        ["Net Revenue Yield Rate", f"{net_yield_pct:.1f}%"]
    ]

    print(f"--- Tutor Travel ROI & Revenue Yield ({days} Days) ---")
    print(tabulate(roi_table, headers=["Metric", "Value"], tablefmt="fancy_grid"))
    print("\n")

    # 4. Optional Chart Generation
    if export_chart and not commute_df.empty:
        try:
            import matplotlib.pyplot as plt
            charts_dir = Path(__file__).resolve().parent / "charts"
            charts_dir.mkdir(exist_ok=True)

            fig, ax = plt.subplots(figsize=(7, 5))
            ax.pie(commute_summary['Total Spent (BDT)'], labels=commute_summary['Commute Tag'], autopct='%1.1f%%', startangle=140)
            ax.set_title(f"Transport Spend Share by Tag ({days} Days)")
            plt.tight_layout()
            chart_path = charts_dir / "commute_breakdown.png"
            plt.savefig(chart_path, dpi=200)
            plt.close()
            print(f"📊 Saved chart to: {chart_path}")
        except Exception as e:
            print(f"Failed to generate chart: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Commute & Tutor Travel Efficiency Report")
    parser.add_argument("--days", type=int, default=60, help="Lookback window in days")
    parser.add_argument("--chart", action="store_true", help="Export PNG charts")
    args = parser.parse_args()

    run_commute_analytics(days=args.days, export_chart=args.chart)
