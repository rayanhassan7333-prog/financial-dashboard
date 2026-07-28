#!/usr/bin/env python3
import sys
import argparse
from pathlib import Path
from datetime import datetime

# Ensure analysis folder is in path
ANALYSIS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ANALYSIS_DIR))

from summary_analytics import get_summary_analytics
from cashflow_forecast import get_cashflow_forecast
from receivables_aging import get_receivables_aging
from anomaly_detection import get_anomaly_detection
from commute_analytics import get_commute_analytics
from net_worth_trends import get_net_worth_trends

def generate_markdown_report(output_file: Path):
    print("⏳ Running financial analysis modules...")
    
    # 1. Fetch data from all modules
    summary_data = get_summary_analytics(period="monthly", export_chart=True)
    forecast_data = get_cashflow_forecast(lookback_days=60, forecast_days=30)
    receivables_data = get_receivables_aging(export_chart=True)
    anomaly_data = get_anomaly_detection(baseline_days=90, recent_days=30, export_chart=True)
    commute_data = get_commute_analytics(days=60, export_chart=True)
    networth_data = get_net_worth_trends(export_chart=True)

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Build Markdown document
    lines = []

    # Title Banner
    lines.append("# 📊 Financial Database Executive Intelligence Report")
    lines.append(f"*Generated on: `{now_str}`*\n")
    lines.append("---")

    # Executive KPI Overview Grid
    lines.append("## ⚡ Executive Summary & Key Financial KPIs\n")

    net_worth = networth_data.get('total_net_worth', 0.0)
    liquid_cash = networth_data.get('liquid_cash', 0.0)
    monthly_income = summary_data.get('total_income', 0.0)
    monthly_expense = summary_data.get('total_expense', 0.0)
    net_cash_flow = summary_data.get('net_cash_flow', 0.0)
    forecast_ending = forecast_data.get('projected_ending_balance', 0.0)
    health_status = networth_data.get('health_status', 'N/A')

    lines.append("| Key Metric | Value | Status / Indicator |")
    lines.append("| :--- | :---: | :---: |")
    lines.append(f"| **Total Net Worth** | **{net_worth:,.2f} BDT** | 💼 Combined Assets |")
    lines.append(f"| **Liquid Cash & Bank** | **{liquid_cash:,.2f} BDT** | 💵 Available Liquidity |")
    lines.append(f"| **Monthly Net Cash Flow** | **{net_cash_flow:+,.2f} BDT** | {'🟢 Surplus' if net_cash_flow >= 0 else '🔴 Deficit'} |")
    lines.append(f"| **30-Day Forecast Ending Cash** | **{forecast_ending:,.2f} BDT** | 📈 Projected Balance |")
    lines.append(f"| **Liquidity Health** | {networth_data.get('liquidity_runway_months', 0.0):.1f} Months | {health_status} |")
    lines.append("\n")

    # Callout Alert based on status
    if anomaly_data.get('critical_count', 0) > 0:
        lines.append(f"> [!WARNING]")
        lines.append(f"> **Budget Drift Warning**: Detected {anomaly_data['critical_count']} critical spending category spike(s) over the last 30 days. Review Section 5 for details.\n")
    else:
        lines.append("> [!NOTE]")
        lines.append("> **Financial Status**: Spending is operating within normal baseline limits with strong liquidity support.\n")

    # Section 1: Net Worth & Asset Distribution
    lines.append("## 1. 💼 Net Worth & Asset Allocation\n")
    lines.append("Overview of total wealth distribution across liquid cash, loan receivables, and investment portfolios.\n")

    lines.append("| Asset Category | Value (BDT) | % Allocation |")
    lines.append("| :--- | :---: | :---: |")
    lines.append(f"| Liquid Cash & Bank Wallets | {networth_data.get('liquid_cash', 0.0):,.2f} BDT | {(networth_data.get('liquid_cash', 0.0)/net_worth*100 if net_worth else 0):.1f}% |")
    lines.append(f"| Outstanding Receivables (Loans) | {networth_data.get('total_receivables', 0.0):,.2f} BDT | {(networth_data.get('total_receivables', 0.0)/net_worth*100 if net_worth else 0):.1f}% |")
    lines.append(f"| Investments Portfolio | {networth_data.get('total_investments', 0.0):,.2f} BDT | {(networth_data.get('total_investments', 0.0)/net_worth*100 if net_worth else 0):.1f}% |")
    lines.append(f"| **Total Net Worth** | **{net_worth:,.2f} BDT** | **100.0%** |")
    lines.append("\n")

    # Live Wallet Breakdown
    wallets_df = summary_data.get('wallets_df')
    if wallets_df is not None and not wallets_df.empty:
        lines.append("### 🏦 Live Wallet Balances")
        lines.append("| Account / Wallet | Current Balance |")
        lines.append("| :--- | :---: |")
        for _, r in wallets_df.iterrows():
            lines.append(f"| {r['name']} | {r['balance']:,.2f} BDT |")
        lines.append("\n")

    if networth_data.get('chart_path'):
        lines.append("![Net Worth Allocation](charts/net_worth_allocation.png)\n")

    # Section 2: Monthly Summary
    lines.append("## 2. 📈 Monthly Income & Spending Overview\n")
    lines.append(f"Summary of all recorded transactions for the current monthly cycle.\n")

    lines.append("| Financial Metric | Amount |")
    lines.append("| :--- | :---: |")
    lines.append(f"| Total Gross Income | {monthly_income:,.2f} BDT |")
    lines.append(f"| Total Gross Expenses | {monthly_expense:,.2f} BDT |")
    lines.append(f"| Net Savings / Cash Flow | {net_cash_flow:+,.2f} BDT |")
    lines.append(f"| Savings Rate | {summary_data.get('savings_rate', 0.0):.1f}% |")
    lines.append(f"| Transaction Count | {summary_data.get('tx_count', 0)} |")
    lines.append("\n")

    # Top Expense Categories
    cat_df = summary_data.get('cat_summary')
    if cat_df is not None and not cat_df.empty:
        lines.append("### 🛒 Top Expense Categories")
        lines.append("| Category | Total Spent | Tx Count | % of Expenses |")
        lines.append("| :--- | :---: | :---: | :---: |")
        for _, r in cat_df.iterrows():
            lines.append(f"| {r['Category']} | {r['Total Spent (BDT)']:,.2f} BDT | {r['Tx Count']} | {r['% of Expenses']:.1f}% |")
        lines.append("\n")

    if summary_data.get('chart_path'):
        lines.append("![Expense Breakdown](charts/expense_breakdown_monthly.png)\n")

    # Section 3: Receivables & Tuition Aging
    lines.append("## 3. 🎯 Receivables & Tuition Collection Aging\n")
    lines.append("Tracking outstanding loans to receive and tuition collection performance against expected schedules.\n")

    # Tuition Table
    tuition_list = receivables_data.get('tuition_summary', [])
    if tuition_list:
        lines.append("### 📚 2026 Tuition Collection Efficiency")
        lines.append("| Student / Tuition | Monthly Rate | Expected YTD | Received YTD | Collection % | Status |")
        lines.append("| :--- | :---: | :---: | :---: | :---: | :---: |")
        for t in tuition_list:
            lines.append(f"| {t['name']} | {t['monthly_rate']:,.2f} BDT | {t['expected_ytd']:,.2f} BDT | {t['received_ytd']:,.2f} BDT | {t['collection_rate']:.1f}% | {t['status']} |")
        lines.append("\n")

    lines.append(f"**Tuition Collection Summary**: Expected YTD: `{receivables_data.get('total_expected_ytd', 0.0):,.2f} BDT` | Received YTD: `{receivables_data.get('total_received_ytd', 0.0):,.2f} BDT` | Overall Rate: `{receivables_data.get('overall_rate', 0.0):.1f}%`\n")

    # Outstanding Loans Aging
    loans_df = receivables_data.get('loans_df')
    if loans_df is not None and not loans_df.empty:
        lines.append("### ⏳ Loan Receivables Aging")
        lines.append("| Borrower | Outstanding | Age | Aging Bucket | Last Lent Date |")
        lines.append("| :--- | :---: | :---: | :---: | :---: |")
        for _, r in loans_df.iterrows():
            last_date = r['last_lent_date'].strftime('%Y-%m-%d') if 'last_lent_date' in r and not str(r['last_lent_date']).startswith('NaT') else 'N/A'
            lines.append(f"| {r.get('borrower', 'Unknown')} | {r['outstanding']:,.2f} BDT | {r.get('days_outstanding', 0)} days | {r.get('aging_bucket', 'N/A')} | {last_date} |")
        lines.append("\n")

    if receivables_data.get('chart_path'):
        lines.append("![Receivables Aging](charts/receivables_aging.png)\n")

    # Section 4: 30-Day Cash Flow Forecast
    lines.append("## 4. 🔮 30-Day Cash Flow & Runway Forecast\n")
    lines.append("Predictive model based on historical daily burn rate (60-day window) and fixed tuition schedules.\n")

    lines.append("| Forecast Parameter | Amount |")
    lines.append("| :--- | :---: |")
    lines.append(f"| Current Liquid Assets | {forecast_data.get('current_cash', 0.0):,.2f} BDT |")
    lines.append(f"| Average Daily Burn Rate (60d avg) | {forecast_data.get('daily_burn_rate', 0.0):,.2f} BDT/day |")
    lines.append(f"| Projected Tuition Revenue (+30d) | +{forecast_data.get('projected_tuition_revenue', 0.0):,.2f} BDT |")
    lines.append(f"| Projected Variable Expenses (-30d) | -{forecast_data.get('projected_variable_expenses', 0.0):,.2f} BDT |")
    lines.append(f"| Projected Subscriptions (-30d) | -{forecast_data.get('projected_subscriptions', 0.0):,.2f} BDT |")
    lines.append(f"| **Projected 30-Day Net Cash Flow** | **{forecast_data.get('projected_net_cash_flow', 0.0):+,.2f} BDT** |")
    lines.append(f"| **Projected Ending Cash Balance** | **{forecast_data.get('projected_ending_balance', 0.0):,.2f} BDT** |")
    lines.append("\n")

    # Section 5: Anomaly & Budget Drift
    lines.append("## 5. 🚨 Budget Drift & Anomaly Alerts\n")
    lines.append("Comparison of recent 30-day spend against 90-day historical baseline to flag unexpected drift.\n")

    cat_comp = anomaly_data.get('cat_comparison')
    if cat_comp is not None and not cat_comp.empty:
        lines.append("### 📊 Category Monthly Drift")
        lines.append("| Category | Baseline/Mo | Recent/Mo | Abs Drift | % Change | Status |")
        lines.append("| :--- | :---: | :---: | :---: | :---: | :---: |")
        for cat, r in cat_comp.iterrows():
            lines.append(f"| {cat} | {r['Baseline Monthly (BDT)']:,.2f} BDT | {r['Recent Monthly (BDT)']:,.2f} BDT | {r['Abs Change (BDT)']:+,.2f} BDT | {r['% Change']:+.1f}% | {r['Status']} |")
        lines.append("\n")

    tag_comp = anomaly_data.get('tag_comparison')
    if tag_comp is not None and not tag_comp.empty:
        lines.append("### 🏷️ Top Escalating Expense Tags")
        lines.append("| Tag | Baseline/Mo | Recent/Mo | Abs Drift | % Change |")
        lines.append("| :--- | :---: | :---: | :---: | :---: |")
        for tag, r in tag_comp.iterrows():
            lines.append(f"| {tag} | {r['Baseline/Mo']:,.2f} BDT | {r['Recent/Mo']:,.2f} BDT | {r['Abs Drift']:+,.2f} BDT | {r['% Change']:+.1f}% |")
        lines.append("\n")

    if anomaly_data.get('chart_path'):
        lines.append("![Budget Anomalies](charts/budget_anomalies.png)\n")

    # Section 6: Commute Analytics
    lines.append("## 6. 🚗 Commute & Tutor Travel Efficiency\n")
    lines.append("Transport breakdown by trip tag and net tuition yield after travel expenses.\n")

    commute_summary = commute_data.get('commute_summary')
    if commute_summary is not None and not commute_summary.empty:
        lines.append("| Trip Tag | Total Spent | Trips | Avg Cost/Trip | % Share |")
        lines.append("| :--- | :---: | :---: | :---: | :---: |")
        for _, r in commute_summary.iterrows():
            lines.append(f"| {r['Commute Tag']} | {r['Total Spent (BDT)']:,.2f} BDT | {int(r['Trip Count'])} | {r['Avg Cost/Trip (BDT)']:,.2f} BDT | {r['% of Transport']:.1f}% |")
        lines.append("\n")

    lines.append("### 🎓 Tutor Travel ROI")
    lines.append(f"- **Gross Tuition Earned**: `{commute_data.get('gross_tuition_earned', 0.0):,.2f} BDT`")
    lines.append(f"- **Tutor Travel Expenses (`TutorTrips`)**: `-{commute_data.get('tutor_travel_cost', 0.0):,.2f} BDT`")
    lines.append(f"- **Net Tuition Revenue**: `{commute_data.get('net_tuition_revenue', 0.0):,.2f} BDT` (Net Yield: `{commute_data.get('net_yield_pct', 0.0):.1f}%`)\n")

    if commute_data.get('chart_path'):
        lines.append("![Commute Breakdown](charts/commute_breakdown.png)\n")

    # Recommendations & Next Steps
    lines.append("## 💡 Executive Action Items & Recommendations\n")
    lines.append("1. **Tuition Receivables Follow-Up**: Focus collection efforts on pending tuition payments (e.g. Mayan / Nabiha variance) to ensure cash flow targets are met.")
    lines.append("2. **Category Drift Control**: Monitor escalated categories (`Food & Dining` / `City Commute`) to prevent ongoing budget drift.")
    lines.append("3. **Loan Recovery**: Maintain communication regarding outstanding loan receivables (`Waraka: 53,130 BDT`) to boost liquid cash reserves.")
    lines.append("\n---\n*Report compiled automatically by Antigravity Financial Intelligence Suite.*")

    content = "\n".join(lines)
    
    # Save to file
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"✅ Polished Financial Report successfully generated at: {output_file}")
    return output_file

def main():
    parser = argparse.ArgumentParser(description="Generate Executive Financial Markdown Report")
    parser.add_argument("--output", type=str, default="FINANCIAL_REPORT.md", help="Output markdown filename")
    args = parser.parse_args()

    out_path = ANALYSIS_DIR / args.output
    generate_markdown_report(out_path)

if __name__ == "__main__":
    main()
