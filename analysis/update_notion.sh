#!/bin/bash
set -euo pipefail

# Navigate to the analysis directory
cd "$(dirname "$0")"

echo "Skipped: Publishing financial dashboards and live balances to Notion is retired per AGENTS.md."
echo "Supabase remains authoritative for live financial transactions and balances."
echo "Run 'python3 run_all.py' to generate local dated analysis reports under analysis/reports/."
exit 0
