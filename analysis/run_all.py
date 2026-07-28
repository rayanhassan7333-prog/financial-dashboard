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

def main():
    parser = argparse.ArgumentParser(description="Financial Dashboard Full Analytics Suite")
    parser.add_argument("--chart", action="store_true", help="Generate and save PNG charts to analysis/charts/")
    parser.add_argument("--module", choices=["all", "summary", "forecast", "receivables", "anomalies", "commute", "networth"], default="all", help="Select specific analysis module to run")
    args = parser.parse_args()

    print("\n" + "="*60)
    print("      FINANCIAL DASHBOARD & ANALYTICS SUITE (FULL RUN)")
    print("="*60)

    if args.module in ["all", "summary"]:
        run_summary_analysis(period="monthly", export_chart=args.chart)

    if args.module in ["all", "forecast"]:
        run_cashflow_forecast(lookback_days=60, forecast_days=30)

    if args.module in ["all", "receivables"]:
        run_receivables_aging(export_chart=args.chart)

    if args.module in ["all", "anomalies"]:
        run_anomaly_detection(baseline_days=90, recent_days=30, export_chart=args.chart)

    if args.module in ["all", "commute"]:
        run_commute_analytics(days=60, export_chart=args.chart)

    if args.module in ["all", "networth"]:
        run_net_worth_trends(export_chart=args.chart)

    print("\n" + "="*60)
    print("      ✅ ALL FINANCIAL ANALYSES COMPLETED SUCCESSFULLY")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
