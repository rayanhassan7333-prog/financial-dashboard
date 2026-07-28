import argparse
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
from tabulate import tabulate
from config import fetch_table_df

def run_anomaly_detection(baseline_days: int = 90, recent_days: int = 30, export_chart: bool = False):
    print(f"\n=========================================")
    print(f"   EXPENSE ANOMALY & BUDGET DRIFT DETECTOR")
    print(f"=========================================\n")

    # 1. Fetch data
    df = fetch_table_df("unified_register_v")
    if df.empty:
        print("No transaction data available.")
        return

    df['date'] = pd.to_datetime(df['date'])
    df['amount'] = pd.to_numeric(df['amount'], errors='coerce').fillna(0)
    expense_df = df[df['type'] == 'Expense'].copy()

    if expense_df.empty:
        print("No expense data available.")
        return

    now = datetime.now()
    recent_cutoff = now - timedelta(days=recent_days)
    baseline_start = recent_cutoff - timedelta(days=baseline_days)

    recent_df = expense_df[expense_df['date'] >= recent_cutoff].copy()
    baseline_df = expense_df[(expense_df['date'] >= baseline_start) & (expense_df['date'] < recent_cutoff)].copy()

    baseline_months = baseline_days / 30.0
    recent_months = recent_days / 30.0

    print(f"Baseline Window: {baseline_start.strftime('%Y-%m-%d')} to {recent_cutoff.strftime('%Y-%m-%d')} ({baseline_days} days)")
    print(f"Recent Window:   {recent_cutoff.strftime('%Y-%m-%d')} to {now.strftime('%Y-%m-%d')} ({recent_days} days)\n")

    # 2. Category Anomaly Analysis
    base_cat = baseline_df.groupby('category')['amount'].sum() / baseline_months
    recent_cat = recent_df.groupby('category')['amount'].sum() / recent_months

    cat_comparison = pd.DataFrame({
        'Baseline Monthly (BDT)': base_cat,
        'Recent Monthly (BDT)': recent_cat
    }).fillna(0)

    cat_comparison['Abs Change (BDT)'] = cat_comparison['Recent Monthly (BDT)'] - cat_comparison['Baseline Monthly (BDT)']
    
    def calc_cat_pct_change(row):
        base = row['Baseline Monthly (BDT)']
        rec = row['Recent Monthly (BDT)']
        if base > 0:
            return ((rec - base) / base) * 100
        elif rec > 0:
            return 100.0
        return 0.0

    cat_comparison['% Change'] = cat_comparison.apply(calc_cat_pct_change, axis=1)

    def flag_anomaly(row):
        pct = row['% Change']
        change = row['Abs Change (BDT)']
        if pct >= 40.0 and change > 500:
            return "🚨 CRITICAL SPIKE"
        elif pct >= 20.0 and change > 200:
            return "⚠️ Moderate Increase"
        elif pct <= -20.0:
            return "📉 Savings / Drop"
        else:
            return "✅ Normal Baseline"

    cat_comparison['Status'] = cat_comparison.apply(flag_anomaly, axis=1)
    cat_comparison = cat_comparison.sort_values(by='Abs Change (BDT)', ascending=False)

    formatted_cat_table = []
    for cat, row in cat_comparison.iterrows():
        formatted_cat_table.append([
            cat,
            f"{row['Baseline Monthly (BDT)']:,.2f} BDT",
            f"{row['Recent Monthly (BDT)']:,.2f} BDT",
            f"{row['Abs Change (BDT)']:+,.2f} BDT",
            f"{row['% Change']:+.1f}%",
            row['Status']
        ])

    print("--- Category Monthly Baseline vs Recent Comparison ---")
    print(tabulate(formatted_cat_table, headers=["Category", "Baseline/Mo", "Recent/Mo", "Abs Drift", "% Change", "Status"], tablefmt="fancy_grid"))
    print("\n")

    # 3. Tag Escalation Analysis
    def unnest_tags(data_frame):
        tag_rows = []
        for _, row in data_frame.iterrows():
            tags = row.get('tags')
            if isinstance(tags, list):
                for t in tags:
                    tag_rows.append({'tag': t, 'amount': row['amount']})
        return pd.DataFrame(tag_rows) if tag_rows else pd.DataFrame(columns=['tag', 'amount'])

    base_tags_df = unnest_tags(baseline_df)
    recent_tags_df = unnest_tags(recent_df)

    if not base_tags_df.empty or not recent_tags_df.empty:
        base_tag_sum = base_tags_df.groupby('tag')['amount'].sum() / baseline_months if not base_tags_df.empty else pd.Series(dtype=float)
        recent_tag_sum = recent_tags_df.groupby('tag')['amount'].sum() / recent_months if not recent_tags_df.empty else pd.Series(dtype=float)

        tag_comparison = pd.DataFrame({
            'Baseline/Mo': base_tag_sum,
            'Recent/Mo': recent_tag_sum
        }).fillna(0)

        tag_comparison['Abs Drift'] = tag_comparison['Recent/Mo'] - tag_comparison['Baseline/Mo']

        def calc_tag_pct_change(row):
            base = row['Baseline/Mo']
            rec = row['Recent/Mo']
            if base > 0:
                return ((rec - base) / base) * 100
            elif rec > 0:
                return 100.0
            return 0.0

        tag_comparison['% Change'] = tag_comparison.apply(calc_tag_pct_change, axis=1)
        tag_comparison = tag_comparison.sort_values(by='Abs Drift', ascending=False).head(10)

        formatted_tag_table = []
        for tag, row in tag_comparison.iterrows():
            formatted_tag_table.append([
                tag,
                f"{row['Baseline/Mo']:,.2f} BDT",
                f"{row['Recent/Mo']:,.2f} BDT",
                f"{row['Abs Drift']:+,.2f} BDT",
                f"{row['% Change']:+.1f}%"
            ])

        print("--- Top Escalating Expense Tags ---")
        print(tabulate(formatted_tag_table, headers=["Expense Tag", "Baseline/Mo", "Recent/Mo", "Abs Drift", "% Change"], tablefmt="github"))
        print("\n")

    # 4. Optional Chart Generation
    if export_chart and not cat_comparison.empty:
        try:
            import matplotlib.pyplot as plt
            charts_dir = Path(__file__).resolve().parent / "charts"
            charts_dir.mkdir(exist_ok=True)

            top_cats_chart = cat_comparison.head(6)
            fig, ax = plt.subplots(figsize=(9, 5))
            top_cats_chart[['Baseline Monthly (BDT)', 'Recent Monthly (BDT)']].plot(kind='bar', ax=ax)
            ax.set_title("Expense Drift: Baseline vs Recent Monthly Spend")
            ax.set_ylabel("Monthly Spend (BDT)")
            plt.xticks(rotation=25)
            plt.tight_layout()
            chart_path = charts_dir / "budget_anomalies.png"
            plt.savefig(chart_path, dpi=200)
            plt.close()
            print(f"📊 Saved chart to: {chart_path}")
        except Exception as e:
            print(f"Failed to generate chart: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Expense Anomaly & Budget Drift Detector")
    parser.add_argument("--baseline", type=int, default=90, help="Baseline lookback window in days")
    parser.add_argument("--recent", type=int, default=30, help="Recent evaluation window in days")
    parser.add_argument("--chart", action="store_true", help="Export PNG charts")
    args = parser.parse_args()

    run_anomaly_detection(baseline_days=args.baseline, recent_days=args.recent, export_chart=args.chart)
