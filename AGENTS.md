# Financial OS Instructions

Reviewed: 29 October 2026 (Asia/Dhaka). Inherits `../AGENTS.md`.

- Supabase is authoritative for live balances and transactions. Resolve the intended project, accounts and current schema before querying or writing; do not answer from old reports or cached totals.
- Answer current financial questions with dated ledger evidence in the conversation. Do not create or refresh a Notion financial dashboard, or copy changing balances and computed totals into the Second Brain. Save a lasting guide, plan, agreement, decision or lesson only when requested.
- Local README and sync utilities describe legacy Notion presentation/sync behavior. Their presence does not authorize re-enabling sync or publishing live figures. Inspect actual configuration for a sync-maintenance task and flag conflicts with the source-ownership rules.
- For authorized ledger changes, use the current finance workflow and schema, keep internal transfers separate from fees, prevent duplicate writes, and read back affected records and balances. Do not infer accounts or amounts.
- Preserve operational files and unrelated changes. Inspect the branch and working tree before editing; do not overwrite existing work or change deployed functions as part of documentation maintenance.
- Treat generated reports as dated analysis. Tracked assets alone do not establish complete net worth, and a ledger review is not a certified audit.
