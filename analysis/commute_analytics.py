import argparse
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
from tabulate import tabulate
from config import fetch_table_df

COMMUTE_TAGS = ['DailyCommute', 'CampusTrip', 'SocialTrip', 'TutorTrips', 'OtherCommute']

def get_commute_analytics(days: int = 60, export_chart: bool = False) -> dict:
    df = fetch_table_df("unified_register_v")
    if df.empty:
        return {}

    df['date'] = pd.to_datetime(df['date'])
    df['amount'] = pd.to_numeric(df['amount'], errors='coerce').fillna(0)

    now = datetime.now()
    cutoff_date = now - timedelta(days=days)
    recent_df = df[df['date'] >= cutoff_date].copy()

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
                        'amount': float(row['amount']),
                        'tag': t,
                        'wallet': row.get('wallet', 'Unknown')
                    })

    commute_df = pd.DataFrame(commute_rows)
    commute_summary = pd.DataFrame()
    total_commute_spend = 0.0

    if not commute_df.empty:
        commute_summary = commute_df.groupby('tag')['amount'].agg(['sum', 'count', 'mean']).reset_index()
        commute_summary.columns = ['Commute Tag', 'Total Spent (BDT)', 'Trip Count', 'Avg Cost/Trip (BDT)']
        total_commute_spend = float(commute_summary['Total Spent (BDT)'].sum())
        commute_summary['% of Transport'] = (commute_summary['Total Spent (BDT)'] / total_commute_spend * 100).round(1)
        commute_summary = commute_summary.sort_values(by='Total Spent (BDT)', ascending=False)

    income_df = recent_df[recent_df['type'] == 'Income']
    tuition_income_df = income_df[
        (income_df['category'].str.lower() == 'tuition') | 
        (income_df['title'].str.contains('Tuition|Nabiha|Ayesha|Mayan', case=False, na=False))
    ]

    gross_tuition_earned = float(tuition_income_df['amount'].sum())
    tutor_travel_cost = 0.0
    if not commute_df.empty and 'TutorTrips' in commute_df['tag'].values:
        tutor_travel_cost = float(commute_df[commute_df['tag'] == 'TutorTrips']['amount'].sum())

    net_tuition_revenue = gross_tuition_earned - tutor_travel_cost
    net_yield_pct = (net_tuition_revenue / gross_tuition_earned * 100) if gross_tuition_earned > 0 else 0.0

    chart_path = None
    if export_chart and not commute_summary.empty:
        try:
            import matplotlib.pyplot as plt
            charts_dir = Path(__file__).resolve().parent / "charts"
            charts_dir.mkdir(exist_ok=True)

            fig, ax = plt.subplots(figsize=(7, 5))
            ax.pie(commute_summary['Total Spent (BDT)'], labels=commute_summary['Commute Tag'], autopct='%1.1f%%', startangle=140)
            ax.set_title(f"Transport Spend Share by Tag ({days} Days)")
            plt.tight_layout()
            chart_file = charts_dir / "commute_breakdown.png"
            plt.savefig(chart_file, dpi=200)
            plt.close()
            chart_path = str(chart_file)
        except Exception as e:
            print(f"Failed to generate chart: {e}")

    return {
        "days": days,
        "commute_df": commute_df,
        "commute_summary": commute_summary,
        "total_commute_spend": total_commute_spend,
        "gross_tuition_earned": gross_tuition_earned,
        "tutor_travel_cost": tutor_travel_cost,
        "net_tuition_revenue": net_tuition_revenue,
        "net_yield_pct": net_yield_pct,
        "chart_path": chart_path
    }

def run_commute_analytics(days: int = 60, export_chart: bool = False):
    print(f"\n=========================================")
    print(f"   COMMUTE & TUTOR TRAVEL EFFICIENCY REPORT ({days} DAYS)")
    print(f"=========================================\n")

    res = get_commute_analytics(days=days, export_chart=export_chart)
    if not res:
        print("No transaction data available.")
        return

    commute_summary = res['commute_summary']
    if not commute_summary.empty:
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
        print(f"Total Transport Expenditure: {res['total_commute_spend']:,.2f} BDT\n")

    roi_table = [
        ["Gross Tuition Revenue Earned", f"{res['gross_tuition_earned']:,.2f} BDT"],
        ["Tutor Travel Transport Expenses (TutorTrips)", f"-{res['tutor_travel_cost']:,.2f} BDT"],
        ["Net Tuition Revenue", f"{res['net_tuition_revenue']:,.2f} BDT"],
        ["Net Revenue Yield Rate", f"{res['net_yield_pct']:.1f}%"]
    ]

    print(f"--- Tutor Travel ROI & Revenue Yield ({days} Days) ---")
    print(tabulate(roi_table, headers=["Metric", "Value"], tablefmt="fancy_grid"))
    print("\n")

    if res['chart_path']:
        print(f"📊 Saved chart to: {res['chart_path']}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Commute & Tutor Travel Efficiency Report")
    parser.add_argument("--days", type=int, default=60, help="Lookback window in days")
    parser.add_argument("--chart", action="store_true", help="Export PNG charts")
    args = parser.parse_args()

    run_commute_analytics(days=args.days, export_chart=args.chart)
