import argparse
from pathlib import Path
from datetime import datetime
import pandas as pd
from tabulate import tabulate
from config import fetch_table_df

TUITION_SCHEDULE = [
    {"name": "Tuition: Nabiha", "monthly_rate": 8000.0, "student_tag": "Nabiha", "start_date": "2025-01-01"},
    {"name": "Tuition: Ayesha", "monthly_rate": 9000.0, "student_tag": "Ayesha", "start_date": "2026-01-01"},
    {"name": "Tuition: Mayan",  "monthly_rate": 8000.0, "student_tag": "Mayan",  "start_date": "2026-01-01"}
]

def run_receivables_aging(export_chart: bool = False):
    print(f"\n=========================================")
    print(f"   RECEIVABLES & TUITION AGING REPORT")
    print(f"=========================================\n")

    now = datetime.now()

    # 1. Outstanding Loan Receivables Aging
    loans_df = fetch_table_df("loans_receivable_v")
    if not loans_df.empty:
        loans_df['outstanding'] = pd.to_numeric(loans_df['outstanding'], errors='coerce').fillna(0)
        loans_df = loans_df[loans_df['outstanding'] > 0].copy()

        if 'last_lent_date' in loans_df.columns:
            loans_df['last_lent_date'] = pd.to_datetime(loans_df['last_lent_date'])
            loans_df['days_outstanding'] = (now - loans_df['last_lent_date']).dt.days.fillna(0).astype(int)
        else:
            loans_df['days_outstanding'] = 0

        def bucket_days(days):
            if days <= 30:
                return "0-30 days (Current)"
            elif days <= 60:
                return "31-60 days (Overdue)"
            elif days <= 90:
                return "61-90 days (Late)"
            else:
                return "90+ days (Critical)"

        loans_df['aging_bucket'] = loans_df['days_outstanding'].apply(bucket_days)

        loan_table = []
        for _, row in loans_df.iterrows():
            last_date_str = row['last_lent_date'].strftime('%Y-%m-%d') if pd.notnull(row.get('last_lent_date')) else "N/A"
            loan_table.append([
                row.get('borrower', 'Unknown'),
                f"{row['outstanding']:,.2f} BDT",
                f"{row['days_outstanding']} days",
                row['aging_bucket'],
                last_date_str
            ])

        print("--- Outstanding Loan Receivables Aging ---")
        print(tabulate(loan_table, headers=["Borrower", "Outstanding", "Age", "Bucket", "Last Lent Date"], tablefmt="fancy_grid"))
        print("\n")
    else:
        print("--- Outstanding Loan Receivables ---")
        print("No active loan receivables found.\n")

    # 2. Tuition Collection & Schedule Tracker
    df = fetch_table_df("unified_register_v")
    tuition_income_df = pd.DataFrame()
    if not df.empty:
        df['date'] = pd.to_datetime(df['date'])
        df['amount'] = pd.to_numeric(df['amount'], errors='coerce').fillna(0)
        tuition_income_df = df[(df['type'] == 'Income') & (
            (df['category'].str.lower() == 'tuition') | 
            (df['title'].str.contains('Tuition|Nabiha|Ayesha|Mayan', case=False, na=False))
        )].copy()

    # Current year months elapsed
    current_year = now.year
    months_in_current_year = now.month

    tuition_summary = []
    total_expected_ytd = 0.0
    total_received_ytd = 0.0

    for item in TUITION_SCHEDULE:
        start_dt = pd.to_datetime(item['start_date'])
        # Months active in current year
        if start_dt.year == current_year:
            active_months = max(1, current_year_months := (now.month - start_dt.month + 1))
        elif start_dt.year < current_year:
            active_months = months_in_current_year
        else:
            active_months = 0

        expected_ytd = item['monthly_rate'] * active_months

        # Actual received YTD for this tuition
        received_ytd = 0.0
        if not tuition_income_df.empty:
            student_txs = tuition_income_df[
                (tuition_income_df['date'].dt.year == current_year) &
                (tuition_income_df['title'].str.contains(item['student_tag'], case=False, na=False))
            ]
            received_ytd = student_txs['amount'].sum()

        diff = received_ytd - expected_ytd
        status = "✅ On Track / Paid" if diff >= 0 else f"⚠️ Pending/Overdue ({abs(diff):,.2f} BDT)"
        collection_rate = (received_ytd / expected_ytd * 100) if expected_ytd > 0 else 100.0

        total_expected_ytd += expected_ytd
        total_received_ytd += received_ytd

        tuition_summary.append([
            item['name'],
            f"{item['monthly_rate']:,.2f} BDT",
            f"{expected_ytd:,.2f} BDT",
            f"{received_ytd:,.2f} BDT",
            f"{collection_rate:.1f}%",
            status
        ])

    print(f"--- Tuition Collection Efficiency ({current_year} YTD) ---")
    print(tabulate(tuition_summary, headers=["Tuition", "Monthly Rate", "Expected YTD", "Received YTD", "Collection %", "Status"], tablefmt="github"))
    print("\n")

    overall_rate = (total_received_ytd / total_expected_ytd * 100) if total_expected_ytd > 0 else 100.0
    overall_table = [
        ["Total Expected Tuition (YTD)", f"{total_expected_ytd:,.2f} BDT"],
        ["Total Collected Tuition (YTD)", f"{total_received_ytd:,.2f} BDT"],
        ["Outstanding Tuition Variance", f"{total_received_ytd - total_expected_ytd:+,.2f} BDT"],
        ["Overall Tuition Collection Rate", f"{overall_rate:.1f}%"]
    ]
    print("--- Tuition Collection Executive Summary ---")
    print(tabulate(overall_table, headers=["Metric", "Value"], tablefmt="fancy_grid"))
    print("\n")

    # 3. Optional Chart Generation
    if export_chart and not loans_df.empty:
        try:
            import matplotlib.pyplot as plt
            charts_dir = Path(__file__).resolve().parent / "charts"
            charts_dir.mkdir(exist_ok=True)

            fig, ax = plt.subplots(figsize=(8, 5))
            bucket_counts = loans_df.groupby('aging_bucket')['outstanding'].sum()
            bucket_counts.plot(kind='bar', ax=ax, color='#e74c3c')
            ax.set_title("Loan Receivables by Aging Bucket")
            ax.set_ylabel("Outstanding Amount (BDT)")
            ax.set_xlabel("Aging Bucket")
            plt.xticks(rotation=15)
            plt.tight_layout()
            chart_path = charts_dir / "receivables_aging.png"
            plt.savefig(chart_path, dpi=200)
            plt.close()
            print(f"📊 Saved chart to: {chart_path}")
        except Exception as e:
            print(f"Failed to generate chart: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Receivables & Tuition Aging Tracker")
    parser.add_argument("--chart", action="store_true", help="Export PNG charts")
    args = parser.parse_args()

    run_receivables_aging(export_chart=args.chart)
