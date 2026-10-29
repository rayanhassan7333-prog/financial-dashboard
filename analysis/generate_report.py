#!/usr/bin/env python3
"""
Financial Report Generator — Highly Visual & Aesthetic Executive Report
======================================================================
Generates a modern, aesthetic Markdown financial report using beautifully formatted
Mermaid diagrams (Pie Charts, Flowcharts, Timelines) with clean typography and
space-efficient side-by-side tables.
"""
import os
import sys
import argparse
from pathlib import Path
from datetime import datetime
import pandas as pd

# Ensure analysis folder is in path
ANALYSIS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ANALYSIS_DIR))

from summary_analytics import get_summary_analytics
from cashflow_forecast import get_cashflow_forecast
from receivables_aging import get_receivables_aging, TUITION_CONFIG
from anomaly_detection import get_anomaly_detection
from commute_analytics import get_commute_analytics
from net_worth_trends import get_net_worth_trends


# ───────────────────────────────────────────────────────────────────
#  Helper — Chart path resolver
# ───────────────────────────────────────────────────────────────────

def _chart_prefix(output_file: Path) -> str:
    """Resolve a relative path from the report location to the charts/ dir."""
    charts_dir = ANALYSIS_DIR / "charts"
    try:
        return Path(os.path.relpath(charts_dir, output_file.parent)).as_posix() + "/"
    except Exception:
        return "../charts/"


# ───────────────────────────────────────────────────────────────────
#  Helper — Dynamic Action Item Generator
# ───────────────────────────────────────────────────────────────────

def _generate_action_items(receivables_data, anomaly_data, forecast_data, networth_data) -> list[str]:
    """Build context-aware recommendations based on actual data thresholds."""
    items = []

    # Tuition collection gaps
    for t in receivables_data.get('tuition_summary', []):
        if t['diff'] < -500:
            items.append(
                f"**Collect {t['name']}**: "
                f"`{abs(t['diff']):,.0f} BDT` overdue (Collection: `{t['collection_rate']:.0f}%`)."
            )

    # Budget drift alerts
    critical_cats = []
    cat_comp = anomaly_data.get('cat_comparison')
    if cat_comp is not None and not cat_comp.empty:
        for cat, row in cat_comp.iterrows():
            if 'CRITICAL' in str(row.get('Status', '')):
                critical_cats.append(f"{cat} (+{row['% Change']:+.0f}%)")
    if critical_cats:
        items.append(
            f"**Control Budget Drift**: {', '.join(critical_cats)} are spiking. Apply category caps."
        )

    # Loan recovery
    loans_df = receivables_data.get('loans_df')
    if loans_df is not None and not loans_df.empty:
        for _, row in loans_df.iterrows():
            if row['outstanding'] > 5000:
                items.append(
                    f"**Loan Recovery ({row.get('borrower', 'Unknown')})**: "
                    f"`{row['outstanding']:,.0f} BDT` remaining (Due: {row.get('target_label', 'Sept 2026')})."
                )

    if not items:
        items.append("**No Urgent Actions**: All financial metrics are within healthy ranges.")

    return items


# ───────────────────────────────────────────────────────────────────
#  Main Report Generator
# ───────────────────────────────────────────────────────────────────

def generate_markdown_report(output_file: Path = None, export_charts: bool = True):
    print("⏳ Running financial analysis modules...", file=sys.stderr)

    # 1. Fetch data from all modules
    summary_data     = get_summary_analytics(period="monthly", export_chart=export_charts)
    forecast_data    = get_cashflow_forecast(lookback_days=60)
    receivables_data = get_receivables_aging(export_chart=export_charts)
    anomaly_data     = get_anomaly_detection(baseline_days=90, recent_days=30, export_chart=export_charts)
    commute_data     = get_commute_analytics(days=30, export_chart=export_charts)
    networth_data    = get_net_worth_trends(export_chart=export_charts)

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # Precompute key figures
    net_worth       = networth_data.get('total_net_worth', 0.0)
    liquid_cash     = networth_data.get('liquid_cash', 0.0)
    monthly_income  = summary_data.get('total_income', 0.0)
    monthly_expense = summary_data.get('total_expense', 0.0)
    net_cash_flow   = summary_data.get('net_cash_flow', 0.0)
    forecast_ending = forecast_data.get('projected_ending_balance', 0.0)
    health_status   = networth_data.get('health_status', 'N/A')
    runway_months   = networth_data.get('liquidity_runway_months', 0.0)
    target_label    = forecast_data.get('target_label', 'Aug 31, 2026')

    gross_sr = summary_data.get('savings_rate', 0.0)
    routine_sr = summary_data.get('routine_savings_rate', 0.0)
    cf_direction = "surplus" if net_cash_flow >= 0 else "deficit"
    cf_emoji = "🟢" if net_cash_flow >= 0 else "🔴"

    rec_val  = networth_data.get('total_receivables', 0.0)
    loan_rec = networth_data.get('loan_receivables', 0.0)
    tui_rec  = networth_data.get('tuition_receivables', 0.0)
    inv_val  = networth_data.get('total_investments', 0.0)
    pct      = lambda v: f"{(v/net_worth*100):.1f}%" if net_worth else "0%"

    L = []  # Line accumulator

    # ─────────────────────────────────────────────────────────
    # TITLE & GENERATION META
    # ─────────────────────────────────────────────────────────
    L.append("# 📊 Financial Intelligence Report")
    L.append("")
    L.append(f"> 📅 **Generated**: `{now_str}` | **Reporting Period**: Monthly Cycle | **Database**: Supabase")
    L.append(">")

    # ─────────────────────────────────────────────────────────
    # ACTION ITEMS (TL;DR)
    # ─────────────────────────────────────────────────────────
    action_items = _generate_action_items(receivables_data, anomaly_data, forecast_data, networth_data)

    L.append("> 🚨 **Immediate Action Items**")
    L.append(">")
    for i, item in enumerate(action_items, 1):
        L.append(f"> {i}. {item}")
    L.append("")
    L.append("---")
    L.append("")

    # ─────────────────────────────────────────────────────────
    # EXECUTIVE SUMMARY & NET WORTH ARCHITECTURE
    # ─────────────────────────────────────────────────────────
    L.append("## Executive Summary")
    L.append("")
    L.append(
        f"Total net worth is **{net_worth:,.0f} BDT**, with **{liquid_cash:,.0f} BDT** "
        f"in liquid cash providing **{runway_months:.1f} months** of operating runway. "
        f"This month shows a **{cf_emoji} {abs(net_cash_flow):,.0f} BDT {cf_direction}**. "
        f"Forward projection to **{target_label}** estimates ending balance of **{forecast_ending:,.0f} BDT**."
    )
    L.append("")

    # Executive Mermaid Flow Architecture
    L.append("```mermaid")
    L.append("flowchart TD")
    L.append(f"    NW[\"💼 Net Worth<br/><b>{net_worth:,.0f} BDT</b>\"]")
    L.append(f"    NW --> Liquid[\"💵 Liquid Cash<br/><b>{liquid_cash:,.0f} BDT ({pct(liquid_cash)})</b>\"]")
    L.append(f"    NW --> Rec[\"📥 Total Receivables<br/><b>{rec_val:,.0f} BDT ({pct(rec_val)})</b>\"]")
    L.append(f"    NW --> Inv[\"📈 Investments<br/><b>{inv_val:,.0f} BDT ({pct(inv_val)})</b>\"]")
    L.append(f"    Liquid --> Run[\"✅ Liquidity Runway<br/><b>{runway_months:.1f} Months</b>\"]")
    if loan_rec > 0:
        L.append(f"    Rec --> Loans[\"Loans Receivable<br/><b>{loan_rec/1000:.1f}k BDT</b>\"]")
    else:
        L.append("    Rec --> Loans[\"Loans: All Cleared<br/><b>0.0k BDT</b>\"]")
    if tui_rec > 0:
        L.append(f"    Rec --> Tuition[\"Tuition Overdue<br/><b>{tui_rec/1000:.1f}k BDT</b>\"]")
    else:
        L.append("    Rec --> Tuition[\"Tuition: All Cleared<br/><b>0.0k BDT</b>\"]")
    L.append("```")
    L.append("")

    # ─────────────────────────────────────────────────────────
    # SECTION 1 — ASSET ALLOCATION & WALLETS
    # ─────────────────────────────────────────────────────────
    L.append("## 1 · Asset Allocation & Liquid Wallets")
    L.append("")
    L.append("> 💡 **Asset Overview**: Breakdown of your net worth components alongside current balances of your liquid checking and savings accounts.")
    L.append("")

    wallets_df = summary_data.get('wallets_df')

    L.append("### Asset Allocation")
    L.append("")
    L.append("| Asset Class | Allocation |")
    L.append("| :--- | ---: |")
    L.append(f"| Liquid Cash & Bank | {pct(liquid_cash)} |")
    L.append(f"| Loan Receivables | {pct(loan_rec)} |")
    L.append(f"| Tuition Receivables | {pct(tui_rec)} |")
    L.append(f"| Investments | {pct(inv_val)} |")
    L.append(f"| **Total** | **100%** |")
    L.append("")

    if wallets_df is not None and not wallets_df.empty:
        L.append("### Wallets & Accounts")
        L.append("")
        if 'account_type' in wallets_df.columns:
            L.append("| Wallet / Account | Type | Balance (BDT) |")
            L.append("| :--- | :--- | ---: |")
            for _, r in wallets_df.iterrows():
                L.append(f"| {r['name']} | {str(r.get('account_type', 'personal')).capitalize()} | {r['balance']:,.0f} |")
        else:
            L.append("| Wallet / Account | Balance (BDT) |")
            L.append("| :--- | ---: |")
            for _, r in wallets_df.iterrows():
                L.append(f"| {r['name']} | {r['balance']:,.0f} |")
        L.append("")

    L.append("---")
    L.append("")

    # ─────────────────────────────────────────────────────────
    # SECTION 2 — RECEIVABLES & LOAN RECOVERY
    # ─────────────────────────────────────────────────────────
    L.append("## 2 · Receivables & Loan Recovery")
    L.append("")

    # Tuition Mermaid & Table
    tuition_list = receivables_data.get('tuition_summary', [])
    if tuition_list:
        L.append("### Tuition Collection Pipeline")
        L.append("")
        L.append("```mermaid")
        L.append("flowchart LR")
        for t in tuition_list:
            n = t['name'].split(': ')[-1] if ': ' in t['name'] else t['name']
            r = t['received_ytd'] / 1000
            diff = t['diff']
            if diff < 0:
                L.append(f"    {n}[\"{n} ({t['current_rate']/1000:.1f}k/mo)\"] -->|Paid {r:.1f}k| {n}P[\"⚠️ Pending ({abs(diff)/1000:.1f}k)\"]")
            else:
                L.append(f"    {n}[\"{n} ({t['current_rate']/1000:.1f}k/mo)\"] -->|Paid {r:.1f}k| {n}P[\"✅ All Clear\"]")
        L.append("```")
        L.append("")

        L.append("| Student | Current Rate | Expected YTD | Received YTD | Collection |")
        L.append("| :--- | ---: | ---: | ---: | :---: |")
        for t in tuition_list:
            L.append(
                f"| {t['name']} | {t['current_rate']:,.0f} | "
                f"{t['expected_ytd']:,.0f} | {t['received_ytd']:,.0f} | "
                f"{t['collection_rate']:.0f}% |"
            )
        L.append("")

    # Loan Status Flowchart / Badge
    loans_df = receivables_data.get('loans_df')
    waraka_info = receivables_data.get('waraka_analysis', {})

    if loans_df is not None and not loans_df.empty:
        L.append("### Loan Recovery Status")
        L.append("")
        L.append("| Borrower | Outstanding (BDT) | Status | Last Lent |")
        L.append("| :--- | ---: | :--- | :--- |")
        for _, lr in loans_df.iterrows():
            L.append(f"| {lr.get('borrower', 'Unknown')} | {lr.get('outstanding', 0):,.0f} | {lr.get('loan_status', 'Active')} | {lr.get('last_lent_date', 'N/A')} |")
        L.append("")
    elif waraka_info and waraka_info.get("outstanding", 0) == 0:
        L.append("### Loan Recovery Status")
        L.append("")
        L.append(f"> ✅ **All Loans Cleared**: Total loans of `{waraka_info.get('total_lent', 0):,.0f} BDT` (Waraka) and all other borrower balances are 100% repaid. Outstanding balance is `0 BDT`.")
        L.append("")

    L.append("---")
    L.append("")

    # ─────────────────────────────────────────────────────────
    # SECTION 3 — MONTHLY INCOME & SPENDING
    # ─────────────────────────────────────────────────────────
    L.append("## 3 · Monthly Income & Spending Summary")
    L.append("")
    L.append("> 💡 **Cash Flow Details**: Top expense categories for the current period and overall macro-financial summary.")
    L.append("")

    L.append("### Financial Summary")
    L.append("")
    L.append("| Financial Metric | Amount (BDT) |")
    L.append("| :--- | ---: |")
    L.append(f"| Gross Income | {monthly_income:,.0f} |")
    L.append(f"| Gross Expenses | {monthly_expense:,.0f} |")
    L.append(f"| Net Cash Flow | {net_cash_flow:+,.0f} |")
    L.append(f"| Gross Savings Rate | {gross_sr:.1f}% |")
    L.append(f"| Routine Savings Rate | {routine_sr:.1f}% |")
    L.append("")

    cat_df = summary_data.get('cat_summary')
    if cat_df is not None and not cat_df.empty:
        L.append("### Top Expense Categories")
        L.append("")
        L.append("| Category | Spent (BDT) | Share |")
        L.append("| :--- | ---: | ---: |")
        for _, r in cat_df.head(6).iterrows():
            L.append(f"| {r['Category']} | {r['Total Spent (BDT)']:,.0f} | {r['% of Expenses']:.1f}% |")
        L.append("")

    L.append("---")
    L.append("")

    # ─────────────────────────────────────────────────────────
    # SECTION 4 — CASH FLOW FORECAST (Visual Flow)
    # ─────────────────────────────────────────────────────────
    L.append(f"## 4 · Cash Flow Forecast (to {target_label})")
    L.append("")

    proj_tuition = forecast_data.get('projected_tuition_revenue', 0.0)
    proj_loan    = forecast_data.get('projected_loan_revenue', 0.0)
    proj_inflow  = proj_tuition + proj_loan
    proj_varexp  = forecast_data.get('projected_variable_expenses', 0.0)
    proj_subs    = forecast_data.get('projected_subscriptions', 0.0)

    # Waterfall Flowchart
    L.append("```mermaid")
    L.append("flowchart LR")
    L.append(f"    Start[\"Current Liquid Cash<br/><b>{liquid_cash:,.0f} BDT</b>\"] --> Inflow[\"＋ Projected Inflows<br/><b>+{proj_inflow:,.0f} BDT</b>\"]")
    L.append(f"    Inflow --> Outflow[\"− Projected Outflows<br/><b>-{(proj_varexp + proj_subs):,.0f} BDT</b>\"]")
    L.append(f"    Outflow --> EndState[\"🏁 Ending Cash ({target_label})<br/><b>{forecast_ending:,.0f} BDT</b>\"]")
    L.append("```")
    L.append("")

    tuition_sched = forecast_data.get('tuition_schedule', [])
    if tuition_sched or proj_loan > 0:
        L.append("### Expected Inflow Breakdown")
        L.append("")
        L.append("| Inflow Source | Expected Amount (BDT) | Details |")
        L.append("| :--- | ---: | :--- |")
        if tuition_sched:
            for ts in tuition_sched:
                L.append(f"| {ts['name']} | {ts['rate_30d']:,.0f} | {ts['notes']} |")
        if proj_loan > 0:
            L.append(f"| Loan Repayments | {proj_loan:,.0f} | Projected loan recovery inflows |")
        L.append("")

    L.append("---")
    L.append("")

    # ─────────────────────────────────────────────────────────
    # SECTION 5 — BUDGET DRIFT, ANOMALIES & COMMUTE
    # ─────────────────────────────────────────────────────────
    L.append("## 5 · Budget Drift, Anomalies & Commute Efficiency")
    L.append("")
    L.append("> 💡 **Anomaly Detection**: Compares recent 30-day spend against the 90-day historical baseline to flag unusual activity.")
    L.append("")

    # Generate Alerts
    cat_comp = anomaly_data.get('cat_comparison')
    spikes = []
    drops = []
    if cat_comp is not None and not cat_comp.empty:
        for cat, r in cat_comp.iterrows():
            if 'CRITICAL' in r['Status']:
                spikes.append(f"{cat} ({r['% Change']:+.0f}%)")
            elif 'Savings' in r['Status']:
                drops.append(f"{cat} ({r['% Change']:+.0f}%)")

    if spikes:
        L.append("> 🚨 **Critical Expense Spikes**: " + ', '.join(spikes) + " are trending significantly above their 90-day baseline.")
        L.append("")
    if drops:
        L.append("> 💡 **Major Cost Reductions**: " + ', '.join(drops) + " are trending below baseline, increasing your routine savings rate.")
        L.append("")

    tag_comp = anomaly_data.get('tag_comparison')
    if tag_comp is not None and not tag_comp.empty:
        # Keep top 5 tags by absolute drift
        tag_comp['AbsVal'] = tag_comp['Abs Drift'].abs()
        tag_comp = tag_comp.sort_values(by='AbsVal', ascending=False).head(5)

        L.append("### Escalating Expense Tags")
        L.append("")
        L.append("| Tag | Drift (BDT) | % Change |")
        L.append("| :--- | ---: | ---: |")
        for idx, r in tag_comp.iterrows():
            t_name = r.get('tag', r.get('Tag', idx))
            L.append(f"| {t_name} | {r['Abs Drift']:+,.0f} | {r['% Change']:+.0f}% |")
        L.append("")

    commute_summary = commute_data.get('commute_summary')
    if commute_summary is not None and not commute_summary.empty:
        L.append("### Commute Breakdown")
        L.append("")
        L.append("| Commute Type | Spent (BDT) | Trips |")
        L.append("| :--- | ---: | ---: |")
        for _, r in commute_summary.iterrows():
            L.append(f"| {r['Commute Tag']} | {r['Total Spent (BDT)']:,.0f} | {int(r['Trip Count'])} |")
        L.append("")

    # Tutor Travel ROI
    gross = commute_data.get('gross_tuition_earned', 0.0)
    travel = commute_data.get('tutor_travel_cost', 0.0)
    net_rev = commute_data.get('net_tuition_revenue', 0.0)
    net_pct = commute_data.get('net_yield_pct', 0.0)

    if gross > 0:
        L.append("### Tutor Travel ROI")
        L.append(f"**Gross Tuition Earned**: `{gross:,.0f} BDT` | **Travel Cost**: `-{travel:,.0f} BDT` | **Net Yield**: `{net_pct:.1f}%` (`{net_rev:,.0f} BDT`)")
        L.append("")

    # ─────────────────────────────────────────────────────────
    # FOOTER
    # ─────────────────────────────────────────────────────────
    L.append("---")
    L.append("")
    L.append(f"*Report compiled automatically by Antigravity Financial Intelligence Suite · {now_str}*")

    # ─────────────────────────────────────────────────────────
    # Output to stdout
    # ─────────────────────────────────────────────────────────
    content = "\n".join(L)
    if output_file:
        out_p = Path(output_file)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(content)
    print(content)
    return content

def main():
    parser = argparse.ArgumentParser(description="Financial Report Generator")
    parser.add_argument("--output", "-o", type=Path, default=ANALYSIS_DIR / "reports" / "FINANCIAL_REPORT.md", help="Output file path")
    parser.add_argument("--chart", action=argparse.BooleanOptionalAction, default=True, help="Generate and save PNG charts")
    args = parser.parse_args()
    generate_markdown_report(output_file=args.output, export_charts=args.chart)

if __name__ == "__main__":
    main()
