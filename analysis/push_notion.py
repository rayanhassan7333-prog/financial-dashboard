import json
import sys
from pathlib import Path

ANALYSIS_DIR = Path(__file__).resolve().parent
REPORT_FILE = ANALYSIS_DIR / "reports" / "FINANCIAL_REPORT.md"

if not REPORT_FILE.exists():
    print(f"❌ Report not found at {REPORT_FILE}", file=sys.stderr)
    sys.exit(1)

with open(REPORT_FILE, "r", encoding="utf-8") as f:
    content = f.read()

args = {
    "page_id": "3ac24426-9ef8-804e-b3ed-e9a614a69c80",
    "command": "replace_content",
    "new_str": content
}

if __name__ == "__main__":
    if "--json" in sys.argv:
        print(json.dumps(args, indent=2))
    else:
        print(f"✅ Prepared payload for Notion Cloud MCP (notion-update-page) targeting page {args['page_id']} ({len(content)} chars).")

