#!/bin/bash
set -euo pipefail

# Navigate to the analysis directory
cd "$(dirname "$0")"

echo "⏳ Generating Financial Report..."
REPORT_MD=$(python3 generate_report.py)

echo "🚀 Pushing report to Notion via Antigravity Agent..."

# We use the agy CLI to leverage the Notion Cloud MCP integration natively.
# We pass the report through stdin to avoid command line length limits
if ! command -v agy >/dev/null 2>&1; then
    echo "❌ agy is not installed or not on PATH." >&2
    exit 1
fi

printf '%s\n' "$REPORT_MD" | agy --print "Please read the markdown text from standard input and replace the content of Notion page 3ac24426-9ef8-804e-b3ed-e9a614a69c80 with that exact text."


echo "✅ Notion page successfully updated!"
