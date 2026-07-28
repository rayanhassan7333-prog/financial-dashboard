#!/usr/bin/env python3
import sys
from pathlib import Path

# Ensure analysis folder is in path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from summary_analytics import run_summary_analysis
from cashflow_forecast import run_cashflow_forecast

def main():
    print("\n" + "="*50)
    print("      FINANCIAL DASHBOARD & ANALYTICS SUITE")
    print("="*50)

    # 1. Monthly Summary Report
    run_summary_analysis(period="monthly")

    # 2. 30-Day Cash Flow Forecast
    run_cashflow_forecast(lookback_days=60, forecast_days=30)

if __name__ == "__main__":
    main()
