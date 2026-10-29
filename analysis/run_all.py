#!/usr/bin/env python3
import sys
import argparse
from pathlib import Path

# Ensure analysis folder is in path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from summary_analytics import run_summary_analysis
from cashflow_forecast import run_cashflow_forecast
from receivables_aging import run_receivables_aging
from anomaly_detection import run_anomaly_detection
from commute_analytics import run_commute_analytics
from net_worth_trends import run_net_worth_trends
from generate_report import generate_markdown_report

def main():
    parser = argparse.ArgumentParser(description="Financial Full Analytics Suite & Report Generator")
    parser.add_argument("--chart", action=argparse.BooleanOptionalAction, default=True, help="Generate and save PNG charts to analysis/charts/")
    parser.add_argument("--module", choices=["all", "summary", "forecast", "receivables", "anomalies", "commute", "networth", "report"], default="all", help="Select specific analysis module to run")
    parser.add_argument("--report", action=argparse.BooleanOptionalAction, default=None, help="Generate FINANCIAL_REPORT.md in analysis/reports/")
    args = parser.parse_args()

    print("\n" + "="*60)
    print("      FINANCIAL DASHBOARD & ANALYTICS SUITE (FULL RUN)")
    print("="*60)

    should_generate_report = args.report if args.report is not None else args.module in ["all", "report"]

    # A report already runs every analysis module. Avoid doing all work twice.
    ran_full_report = args.module == "all" and should_generate_report
    if ran_full_report:
        report_path = Path(__file__).resolve().parent / "reports" / "FINANCIAL_REPORT.md"
        generate_markdown_report(report_path, export_charts=args.chart)
    elif args.module in ["all", "summary"]:
        run_summary_analysis(period="monthly", export_chart=args.chart)

    if not ran_full_report and args.module != "report" and args.module in ["all", "forecast"]:
        run_cashflow_forecast(lookback_days=60)

    if not ran_full_report and args.module != "report" and args.module in ["all", "receivables"]:
        run_receivables_aging(export_chart=args.chart)

    if not ran_full_report and args.module != "report" and args.module in ["all", "anomalies"]:
        run_anomaly_detection(baseline_days=90, recent_days=30, export_chart=args.chart)

    if not ran_full_report and args.module != "report" and args.module in ["all", "commute"]:
        run_commute_analytics(days=30, export_chart=args.chart)

    if not ran_full_report and args.module != "report" and args.module in ["all", "networth"]:
        run_net_worth_trends(export_chart=args.chart)

    if should_generate_report and args.module != "all":
        report_path = Path(__file__).resolve().parent / "reports" / "FINANCIAL_REPORT.md"
        generate_markdown_report(report_path, export_charts=args.chart)

    print("\n" + "="*60)
    print("      ✅ ALL FINANCIAL ANALYSES & REPORT COMPLETED SUCCESSFULLY")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
