---
name: finance-ledger
description: Query and maintain this workspace's live finance ledger in Supabase, including transactions, transfers, wallets, loans, investments, subscriptions, tuition records, and Notion sync diagnostics or recovery. Use for finance ledger work; use the installed Supabase plugin for general platform operations.
---

# Finance Ledger

## Sources and discovery

- Treat live Supabase data as the source for recorded financial facts. Follow workspace retrieval directives for personal context and canonical notes; distinguish saved snapshots and plans from live records.
- Discover the target project from the workspace's linked project configuration or configured client URL, then confirm it against available Supabase tools. Do not embed project refs, entity IDs, balances, counts, prices, dates, status lists, or account/category/project catalogs in this skill.
- Prefer the connected Supabase tools. Discover their actual signatures instead of relying on tool names from older clients. If unavailable, reuse the workspace's configured client without printing credentials or installing another client unnecessarily.
- Use the table and view names in [ledger.md](references/ledger.md) as discovery hints. Inspect only the relevant live columns, constraints, indexes, enums, or view definitions when they are not already verified in this session. If a hint no longer exists, discover its replacement by purpose instead of inventing a schema change.
- Read [notion-sync.md](references/notion-sync.md) only for sync verification, diagnostics, or recovery. General platform changes belong with the installed Supabase plugin and current official documentation.

## Efficient execution

- Start with the narrowest query that answers the request. Filter, join, count, and aggregate in SQL; return relevant fields rather than dumping tables. Batch independent lookups and related summaries into a structured result.
- Resolve wallets, categories, counterparties, and projects from live records using exact names and relationships. A fuzzy search may suggest candidates, but must not silently select an arbitrary match for a write. Missing or ambiguous matches require resolution before mutation.
- Reuse verified schema and entity mappings within the current session and target project. Refresh after relevant changes or errors. Do not persist cached mappings into instructions, and always fetch changing financial facts fresh.
- Reuse `analysis/config.py` when a Python fallback is useful. For current answers, disable its result cache. Prefer filtered client queries; use its paginated table loader only when the task actually needs the full dataset.
- Use transactions or dependent SQL statements for related database changes. Keep remote Notion calls outside database transactions. Do not combine unrelated mutations merely to reduce tool calls.

## Recording and correcting money movements

- Distinguish consumption expenses, earned income, internal transfers, loan principal, investment principal, and investment profit before choosing a destination table. Transfers and principal movements must not inflate expense or income totals.
- Validate account direction, amount, currency interpretation, category meaning, date, and relevant relationships from the user's request and live schema. Use decimal-safe money handling. Respect database constraints and legitimate special cases rather than inventing blanket numeric rules.
- Interpret relative dates in the user's timezone. Pass the resolved calendar date explicitly when the database or host timezone could differ.
- Check for an existing matching record when the user describes a completed action or retry. Use the live idempotency mechanism when supported, preserving the same operation key across retries. A timeout is not evidence that a write failed; look up its outcome before retrying. Similar records alone do not prove duplication.
- Use targeted mutations and `RETURNING` with the fields needed to verify the requested change. Check affected rows; an empty result is not success. Confirm derived balances or related records only when the task depends on them.
- Ordinary recording should use existing triggers and derived views. Do not manually recreate their output or create a Notion page alongside an automatically synced insert.
- Report database confirmation separately from Notion synchronization. Verify Notion when requested or when completion of the task depends on it; otherwise state that synchronization is asynchronous without claiming it finished.

## Reporting and persistence

- For totals, explain the scope, date range, matched record count, and material inclusions or exclusions. Use a consistent database snapshot when related totals must reconcile. Label partial periods and distinguish net worth, liquidity, outstanding principal, and profit.
- Search titles, notes, tags, and relationships when attribution needs them, then inspect the matched rows. A keyword match alone does not establish the purpose of spending.
- Treat restricted personal sources according to workspace retrieval rules. Do not expand a ledger lookup into unrelated sensitive data retrieval.
- Update canonical finance notes only when the user authorizes persistence. Include the actual verification date and source scope, rebuild the knowledge index, and reread the changed content. Do not save current facts in this skill.

## Platform maintenance

- For authorized migrations, Edge Function changes, logs, permissions, or advisors, use current tool schemas and official Supabase documentation. Inspect the target environment and existing migration workflow before changing it; preserve repository migration history and verify the resulting behavior.
- Preserve the caller's authentication model, RLS boundaries, and credential secrecy. Discover deployed function configuration rather than applying a universal JWT setting or copying an unfinished authentication template.
- Request logs only for the relevant service and time range. Run security or performance checks when the change or request warrants them, rather than attaching a full audit to routine bookkeeping.
- If an approach repeatedly fails, inspect the cause and change strategy. Stop retries that could duplicate financial records or external effects, and report the unresolved state precisely.
