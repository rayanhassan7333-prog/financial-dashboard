import argparse
from pathlib import Path
from datetime import datetime
import pandas as pd
from tabulate import tabulate
from config import fetch_table_df

# ---------------------------------------------------------------------------
# Tuition Rate Configuration — Time-Segmented Schedules
# ---------------------------------------------------------------------------
# Each student has a list of rate segments: {"from": "YYYY-MM", "to": "YYYY-MM", "rate": float}
# The helper `get_rate_for_month()` returns the applicable rate for any given month.
# ---------------------------------------------------------------------------

TUITION_CONFIG = {
    "Nabiha": {
        "name": "Tuition-Nabiha",
        "student_tag": "Nabiha",
        "start_date": "2025-01-01",
        "rate_schedule": [
            {"from": "2025-01", "to": "2025-05", "rate": 14000.0},
            {"from": "2025-06", "to": "2025-07", "rate": 8000.0},
            {"from": "2025-08", "to": "2025-08", "rate": 14000.0},
            {"from": "2025-09", "to": "2026-08", "rate": 8000.0},
        ],
        "notes": "Concluded (Aug 2026; fully paid)"
    },
    "Ayesha": {
        "name": "Tuition-Ayesha",
        "student_tag": "Ayesha",
        "start_date": "2026-01-01",
        "rate_schedule": [
            {"from": "2026-01", "to": "2026-06", "rate": 9000.0},
        ],
        "notes": "Concluded (Jan–Jun 2026; fully paid)"
    },
    "Mayan": {
        "name": "Tuition-Mayan",
        "student_tag": "Mayan",
        "start_date": "2026-01-01",
        "rate_schedule": [
            {"from": "2026-01", "to": "2026-01", "rate": 3200.0},    # Jan session (paid Feb 19)
            {"from": "2026-02", "to": "2026-03", "rate": 8000.0},    # Feb & Mar rate
            {"from": "2026-04", "to": "2026-12", "rate": 12000.0},   # Apr onwards rate
        ],
        "notes": "Variable rate: 3.2k → 8k → 12k"
    },
    "Rafan": {
        "name": "Tuition-Rafan",
        "student_tag": "Rafan",
        "start_date": "2026-03-01",
        "rate_schedule": [
            {"from": "2026-03", "to": "2026-07", "rate": 1000.0},
        ],
        "notes": "Concluded (Mar–Jul 2026; fully paid)"
    }
}


def get_rate_for_month(config: dict, year: int, month: int) -> float:
    """Return the applicable tuition rate for a given year-month from a rate schedule."""
    month_key = f"{year:04d}-{month:02d}"

    # Check skip_months first
    if config.get("skip_months") and month in config["skip_months"]:
        return 0.0

    for seg in config.get("rate_schedule", []):
        if seg["from"] <= month_key <= seg["to"]:
            return seg["rate"]

    # Fallback: if month is before all segments or after, return 0
    return 0.0


def build_monthly_grid(config: dict, current_year: int, up_to_month: int, student_payments_df: pd.DataFrame) -> tuple[list, float, float]:
    """
    Build a month-by-month grid using multi-year FIFO allocation starting from start_date.
    Payments received chronologically are allocated to billable months sequentially,
    accounting for payment delays across year boundaries (e.g., Dec 2025 tuition received in Jan 2026).
    """
    start_date_str = config.get("start_date", f"{current_year}-01-01")
    start_year = int(start_date_str[:4])
    start_month = int(start_date_str[5:7])

    payment_pool = []
    if not student_payments_df.empty:
        start_dt = pd.to_datetime(start_date_str)
        valid_txs = student_payments_df[student_payments_df['date'] >= start_dt].sort_values('date', ascending=True)
        for _, tx in valid_txs.iterrows():
            payment_pool.append({
                "date": tx['date'],
                "date_str": tx['date'].strftime("%b %d, %Y" if tx['date'].year != current_year else "%b %d"),
                "amount_remaining": float(tx['amount'])
            })

    grid_all = []
    y = start_year
    m = start_month

    while (y < current_year) or (y == current_year and m <= up_to_month):
        rate = get_rate_for_month(config, y, m)
        month_label = datetime(y, m, 1).strftime("%b %Y")

        if rate == 0.0:
            grid_all.append({
                "year": y,
                "month": m,
                "month_label": month_label,
                "expected": 0.0,
                "received": 0.0,
                "status": "⬜ Skipped"
            })
        else:
            allocated = 0.0
            needed = rate
            dates_used = []

            for p in payment_pool:
                if p["amount_remaining"] <= 0:
                    continue

                take = min(needed, p["amount_remaining"])
                allocated += take
                needed -= take
                p["amount_remaining"] -= take

                if p["date_str"] not in dates_used:
                    dates_used.append(p["date_str"])

                if needed <= 0:
                    break

            dates_summary = ", ".join(dates_used) if dates_used else ""

            if allocated >= rate:
                status = f"✅ Paid (rec'd {dates_summary})" if dates_summary else "✅ Paid"
            elif allocated > 0:
                status = f"⚠️ Partial ({allocated:,.0f}/{rate:,.0f}) (rec'd {dates_summary})"
            else:
                status = "⏳ Pending"

            grid_all.append({
                "year": y,
                "month": m,
                "month_label": month_label,
                "expected": rate,
                "received": allocated,
                "status": status
            })

        if m == 12:
            y += 1
            m = 1
        else:
            m += 1

    grid_current_year = [g for g in grid_all if g["year"] == current_year]
    expected_ytd = sum(g["expected"] for g in grid_current_year)
    received_ytd = sum(g["received"] for g in grid_current_year)

    return grid_current_year, expected_ytd, received_ytd


LOAN_TARGET_CONFIG = {
    "Waraka": {
        "target_date": "2026-10-31",
        "target_label": "Oct 2026",
        "notes": "Cleared Oct 2026 (100% Repaid)"
    }
}


def get_receivables_aging(export_chart: bool = False) -> dict:
    now = datetime.now()
    current_year = now.year
    current_month = now.month

    # -----------------------------------------------------------------
    # 1. Loans Tracking against Expected Target Clearance Dates
    # -----------------------------------------------------------------
    loans_df = fetch_table_df("loans_receivable_v")
    if not loans_df.empty:
        loans_df['outstanding'] = pd.to_numeric(loans_df['outstanding'], errors='coerce').fillna(0)
        loans_df = loans_df[loans_df['outstanding'] > 0].copy()

        def process_loan_row(row):
            borrower = str(row.get('borrower', ''))
            cfg = LOAN_TARGET_CONFIG.get(borrower)

            if cfg:
                target_dt = pd.to_datetime(cfg["target_date"])
                days_left = (target_dt - now).days
                target_label = cfg["target_label"]

                if days_left >= 0:
                    status = f"✅ On Track (Due {target_label})"
                    bucket = f"{days_left}d remaining ({target_label})"
                else:
                    status = f"⚠️ Overdue by {abs(days_left)}d"
                    bucket = f"Overdue by {abs(days_left)}d ({target_label})"

                return pd.Series({
                    "target_label": target_label,
                    "days_remaining": days_left,
                    "loan_status": status,
                    "aging_bucket": bucket
                })
            else:
                last_lent = pd.to_datetime(row['last_lent_date']) if 'last_lent_date' in row and pd.notnull(row['last_lent_date']) else now
                days_out = (now - last_lent).days
                bucket = "0-30 days" if days_out <= 30 else ("31-60 days" if days_out <= 60 else "60+ days")
                return pd.Series({
                    "target_label": "N/A",
                    "days_remaining": -days_out,
                    "loan_status": bucket,
                    "aging_bucket": bucket
                })

        loan_meta = loans_df.apply(process_loan_row, axis=1)
        loans_df = pd.concat([loans_df, loan_meta], axis=1)

    # -----------------------------------------------------------------
    # 2. Tuition Collection — Fetch all income transactions
    # -----------------------------------------------------------------
    df = fetch_table_df("unified_register_v")
    tuition_income_df = pd.DataFrame()
    if not df.empty:
        df['date'] = pd.to_datetime(df['date'])
        df['amount'] = pd.to_numeric(df['amount'], errors='coerce').fillna(0)

        tuition_income_df = df[
            (df['type'] == 'Income') &
            (df['title'].str.contains('Tuition', case=False, na=False)) &
            (~df['title'].str.contains(r'^Repay', case=False, na=False))
        ].copy()

    # -----------------------------------------------------------------
    # 3. Calculate per-student tuition efficiency with multi-year FIFO allocation
    # -----------------------------------------------------------------
    tuition_summary = []
    tuition_grids = {}
    total_expected_ytd = 0.0
    total_received_ytd = 0.0

    for key, item in TUITION_CONFIG.items():
        student_payments_df = pd.DataFrame()
        if not tuition_income_df.empty:
            student_payments_df = tuition_income_df[
                tuition_income_df['title'].str.contains(item['student_tag'], case=False, na=False)
            ].copy()

        # Only evaluate completed months (exclude ongoing month until it is over)
        completed_month = current_month - 1
        grid, expected_ytd, received_ytd = build_monthly_grid(item, current_year, completed_month, student_payments_df)
        diff = received_ytd - expected_ytd
        current_rate = get_rate_for_month(item, current_year, current_month)

        if expected_ytd == 0.0:
            status = "⬜ No Sessions"
        elif diff >= 0:
            status = "✅ Concluded (Fully Paid)" if current_rate == 0.0 else "✅ On Track / Fully Paid"
        elif abs(diff) <= current_rate * 0.1:
            status = "✅ Approximately On Track"
        else:
            status = f"⚠️ Overdue/Pending ({abs(diff):,.0f} BDT)"

        collection_rate = (received_ytd / expected_ytd * 100) if expected_ytd > 0 else 100.0

        total_expected_ytd += expected_ytd
        total_received_ytd += received_ytd
        tuition_grids[key] = grid

        tuition_summary.append({
            "key": key,
            "name": item['name'],
            "current_rate": current_rate,
            "expected_ytd": expected_ytd,
            "received_ytd": received_ytd,
            "collection_rate": collection_rate,
            "diff": diff,
            "status": status,
            "notes": item.get("notes", ""),
            "monthly_grid": grid
        })

    overall_rate = (total_received_ytd / total_expected_ytd * 100) if total_expected_ytd > 0 else 100.0

    # -----------------------------------------------------------------
    # 4. Detailed Waraka Loan Repayment Rate & Clearance Analysis
    # -----------------------------------------------------------------
    waraka_analysis = {}
    loans_all_df = fetch_table_df("loans_receivable_v")
    if not loans_all_df.empty:
        loans_all_df['outstanding'] = pd.to_numeric(loans_all_df['outstanding'], errors='coerce').fillna(0)
        loans_all_df['total_lent'] = pd.to_numeric(loans_all_df['total_lent'], errors='coerce').fillna(0)
        loans_all_df['total_returned'] = pd.to_numeric(loans_all_df['total_returned'], errors='coerce').fillna(0)
        w_match = loans_all_df[loans_all_df['borrower'].astype(str).str.lower() == 'waraka']
        if not w_match.empty:
            w_row = w_match.iloc[0]
            total_lent = float(w_row['total_lent'])
            total_repaid = float(w_row['total_returned'])
            outstanding = float(w_row['outstanding'])

            if outstanding <= 0:
                waraka_analysis = {
                    "total_lent": total_lent,
                    "total_repaid": total_repaid,
                    "outstanding": 0.0,
                    "repayment_ratio": 100.0,
                    "avg_monthly_repayment": 0.0,
                    "req_monthly_for_sept": 0.0,
                    "months_remaining": 0,
                    "feasibility": "✅ Fully Cleared (100% Repaid)",
                    "projected_clearance_pct": 100.0
                }
            else:
                months_remaining = max(1, (datetime(2026, 12, 31) - now).days // 30)
                req_monthly = outstanding / months_remaining
                waraka_analysis = {
                    "total_lent": total_lent,
                    "total_repaid": total_repaid,
                    "outstanding": outstanding,
                    "repayment_ratio": (total_repaid / total_lent * 100) if total_lent > 0 else 100.0,
                    "avg_monthly_repayment": total_repaid / 10.0,
                    "req_monthly_for_sept": req_monthly,
                    "months_remaining": months_remaining,
                    "feasibility": "Active",
                    "projected_clearance_pct": (total_repaid / total_lent * 100) if total_lent > 0 else 100.0
                }

    # -----------------------------------------------------------------
    # 5. Chart Generation
    # -----------------------------------------------------------------
    chart_path = None
    if export_chart and not loans_df.empty:
        try:
            import matplotlib.pyplot as plt
            charts_dir = Path(__file__).resolve().parent / "charts"
            charts_dir.mkdir(exist_ok=True)

            fig, ax = plt.subplots(figsize=(8, 5))
            bucket_counts = loans_df.groupby('aging_bucket')['outstanding'].sum()
            bucket_counts.plot(kind='bar', ax=ax, color='#e74c3c')
            ax.set_title("Loan Receivables Tracking")
            ax.set_ylabel("Outstanding Amount (BDT)")
            ax.set_xlabel("Target Status")
            plt.xticks(rotation=15)
            plt.tight_layout()
            chart_file = charts_dir / "receivables_aging.png"
            plt.savefig(chart_file, dpi=200)
            plt.close()
            chart_path = str(chart_file)
        except Exception as e:
            print(f"Failed to generate chart: {e}")

    return {
        "loans_df": loans_df,
        "tuition_summary": tuition_summary,
        "tuition_grids": tuition_grids,
        "waraka_analysis": waraka_analysis,
        "total_expected_ytd": total_expected_ytd,
        "total_received_ytd": total_received_ytd,
        "variance": total_received_ytd - total_expected_ytd,
        "overall_rate": overall_rate,
        "chart_path": chart_path
    }


def run_receivables_aging(export_chart: bool = False):
    print(f"\n=========================================")
    print(f"   RECEIVABLES & TUITION AGING REPORT")
    print(f"=========================================\n")

    res = get_receivables_aging(export_chart=export_chart)
    loans_df = res['loans_df']

    if not loans_df.empty:
        loan_table = []
        for _, row in loans_df.iterrows():
            last_date_val = pd.to_datetime(row['last_lent_date']) if pd.notnull(row.get('last_lent_date')) else None
            last_date_str = last_date_val.strftime('%Y-%m-%d') if last_date_val is not None else "N/A"
            days_val = row.get('days_remaining', 0)
            timeline_str = f"{days_val} days left" if days_val >= 0 else f"{abs(days_val)} days past"
            loan_table.append([
                row.get('borrower', 'Unknown'),
                f"{row['outstanding']:,.2f} BDT",
                timeline_str,
                row.get('aging_bucket', 'N/A'),
                last_date_str
            ])
        print("--- Outstanding Loan Receivables Aging ---")
        print(tabulate(loan_table, headers=["Borrower", "Outstanding", "Timeline", "Target / Bucket", "Last Lent Date"], tablefmt="fancy_grid"))
        print("\n")

    tuition_rows = []
    for item in res['tuition_summary']:
        tuition_rows.append([
            item['name'],
            f"{item['current_rate']:,.2f} BDT",
            f"{item['expected_ytd']:,.2f} BDT",
            f"{item['received_ytd']:,.2f} BDT",
            f"{item['collection_rate']:.1f}%",
            item['status']
        ])
    print("--- Tuition Collection Efficiency (2026 YTD) ---")
    print(tabulate(tuition_rows, headers=["Tuition", "Current Rate", "Expected YTD", "Received YTD", "Collection %", "Status"], tablefmt="github"))
    print("\n")

    # Print month-by-month grids
    for item in res['tuition_summary']:
        print(f"  {item['name']} — Monthly Breakdown:")
        grid_rows = []
        for g in item['monthly_grid']:
            grid_rows.append([
                g['month_label'],
                f"{g['expected']:,.0f}" if g['expected'] > 0 else "—",
                f"{g['received']:,.0f}" if g['received'] > 0 else "—",
                g['status']
            ])
        print(tabulate(grid_rows, headers=["Month", "Expected", "Received", "Status"], tablefmt="simple"))
        print()

    overall_table = [
        ["Total Expected Tuition (YTD)", f"{res['total_expected_ytd']:,.2f} BDT"],
        ["Total Collected Tuition (YTD)", f"{res['total_received_ytd']:,.2f} BDT"],
        ["Outstanding Tuition Variance", f"{res['variance']:+,.2f} BDT"],
        ["Overall Tuition Collection Rate", f"{res['overall_rate']:.1f}%"]
    ]
    print("--- Tuition Collection Executive Summary ---")
    print(tabulate(overall_table, headers=["Metric", "Value"], tablefmt="fancy_grid"))
    print("\n")

    if res['chart_path']:
        print(f"📊 Saved chart to: {res['chart_path']}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Receivables & Tuition Aging Tracker")
    parser.add_argument("--chart", action="store_true", help="Export PNG charts")
    args = parser.parse_args()

    run_receivables_aging(export_chart=args.chart)
