> **Current source-ownership notice — 29 October 2026:** The local Second Brain folder has been removed. `AGENTS.md` governs current behavior: Supabase owns live financial values; Notion stores requested lasting plans and decisions. Do not copy balances, net worth, rolling income/spending totals, repayment balances, available cash or computed runway into Notion. `sync_finances_to_brain.py` and analysis push helpers are compatibility commands that explicitly skip without writing. The historical Notion sync architecture and IDs below are archived documentation and do not authorize re-enabling synchronization.

> **Transaction-mirror decision — 30 October 2026:** The user explicitly chose to keep the existing Supabase-to-Notion transaction/transfer mirror active. This is separate from the retired local-vault and financial-dashboard publishers. Supabase remains authoritative; do not publish computed balances or rolling totals to the Second Brain. Verify mirror recovery against current source identity and later operations; do not resurrect transactions that were subsequently deleted.

# Financial Agent Map

Read this first. It is the compact source map for AI agents working in this folder.

Supabase Postgres is the authoritative source of truth. Live balances, net worth, and rolling totals remain in Supabase only. Local files are analysis helpers, generated caches, or dated reports.

---

## 1. Fast Path

- Supabase Postgres is the authoritative source of truth for all ledger transactions and live balances.
- Notion does not receive live balance snapshots, rolling totals, or computed runway (per `AGENTS.md`).
- To inspect or run SQL queries, use the Supabase MCP server tool `execute_sql` or the Supabase dashboard.
- Do not query Notion for current balances or financial metrics; answer from live Supabase ledger data.

---

## 2. Live State

Do not record balances, row counts, receivables, or other changing financial facts in this routing file. Query Supabase using the SQL in section 8. For compact agent retrieval, call `ai_snapshot(p_months, p_recent)` with a trusted service-role connection.

---

## 3. Folder Map

| Path | Purpose |
| :--- | :--- |
| `ReadME.md` | Agent landing map and setup documentation. |
| `settings/` | Directory containing cached configurations (`summary.json`). |
| `.agents/` | Directory for agent skills configuration. |

---

## 4. Supabase Structure

Project: `Finance-tracker`
Project ref: `pyryeeewtdypukuprgwc`
Region: `ap-south-1`

### Tables
- `transactions_table`: Ledger transactions. Core source for income and expenses (with `idempotency_key`).
- `wallet_transfer_tb`: Wallet transfers (with `idempotency_key` and `project_id`).
- `wallet_accounts_tb`: Wallet/account lookup table (with `counterparty_id`).
- `counterparties_tb`: Relational counterparty/borrower registry (`Mom`, `Dadi`, `Zayed`, etc.).
- `investment_projects_tb`: Project-level investment registry (`Dazzling Trade`, `Onion Harvest`, etc.).
- `tags_tb`: Canonical tags registry strictly mapped to parent categories.
- `parent_category_tb`: Category lookup table.
- `subscriptions_list`: Subscription metadata attached to transaction rows.
- `investment_tracker`: Investment metadata attached to transaction rows.
- `sync_queue`: Backup/retry/audit queue for Supabase-to-Notion sync.
- `sys_config_tb`: Internal sync config (with Notion token secured in Supabase Vault).

### Views (All with `security_invoker = true`)
- `unified_register_v`: Main read view for ledger + transfers (uses `counterparties_tb`).
- `wallet_balances_vw`: Current wallet balances.
- `loans_receivable_v`: Outstanding loan balances (dynamically resolved from `counterparties_tb`).
- `active_recur_bills`: Active subscription view.
- `monthly_aggregates`, `net_worth_snapshot`, `investment_summary_v`: Summary/reporting views.

### Functions And Triggers
- `ai_snapshot(p_months, p_recent)`: compact JSON state for trusted agents.
- `trg_realtime_sync_to_notion_fn()`: trigger function for outbound Notion sync using Supabase Vault secrets.
- `fn_validate_transaction_tags()` / `trg_validate_transaction_tags`: enforces database-level category-to-tag integrity.
- `trg_process_special_categories_fn()`: keeps subscription/investment helper rows aligned and parses duration intervals.
- `trg_populate_transfer_title_fn()`: auto-generates transfer titles (`Transfer: <Source> -> <Dest>`) when omitted.
- `update_updated_at_column()`: timestamp helper.
- `trg_enqueue_notion_sync` runs on `INSERT`, `UPDATE`, and `DELETE` for `transactions_table`, `wallet_transfer_tb`, and `wallet_accounts_tb`.

---

## 5. Notion Connection Setup

### Notion Dashboards & Databases
- Financial Dashboard (Root): `36e24426-9ef8-8021-8e53-d993b3d7eb40`
- 2ndBrain Dashboard: `3cd24426-9ef8-8097-91e7-d24ba56aeb21`
  - Brain Dump Database: `3cd24426-9ef8-8051-be9c-de20c83c5a99` (Properties: `Name`, `Category`, `Status`, `Tags`)
- Academic Dashboard: `24424426-9ef8-8033-9927-f9336e4b5d13`
  - Student Info Database: `3cc24426-9ef8-803f-a364-cf4340ff4ff7` (Inline `Student Details`: `3cc24426-9ef8-802a-aeb7-e02e6e132f39`)
- Ledger database: `36e24426-9ef8-8070-bc1c-ea1ecd148662`
- Ledger data source: `36e24426-9ef8-8083-a8d0-000b7e61fb41`
- Transfer database: `36e24426-9ef8-8098-841d-e2bb26b6418e`
- Transfer data source: `36e24426-9ef8-800f-be2a-000b0e5aadff`
- Wallet database: `36e24426-9ef8-80e8-a27b-f7a6462d41a3`
- Wallet data source: `36e24426-9ef8-80e2-886f-000b593d2fc4`
- Automated Financial Intelligence Report page: `3ac24426-9ef8-804e-b3ed-e9a614a69c80`

Live Notion databases: `Ledger`, `Wallet`, `Transfer`, `Brain Dump`, `Student Details`, `Faculty`, `Courses`, `Categories`, `Semester`, `Grades`.

### Sync Flow
1. A row is added, updated, or deleted in Supabase `transactions_table`, `wallet_transfer_tb`, or `wallet_accounts_tb`.
2. Supabase trigger `trg_realtime_sync_to_notion_fn()` writes a `sync_queue` backup row.
3. The same trigger calls the deployed Edge Function `sync-to-notion` asynchronously through `pg_net`.
4. `sync-to-notion` creates, updates, or archives the matching Notion page.
5. The Edge Function writes `notion_id` back to Supabase when it creates or finds a Notion page.
6. The Edge Function marks the queue row `done` or `error`.

### Edge Function
- Name: `sync-to-notion`
- Local source: `supabase/functions/sync-to-notion/index.ts`
- JWT verification is disabled because the database trigger authenticates the request body with an HMAC signature.
- Required built-in secrets: `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`.
- Required database config: `NOTION_TOKEN` in the locked-down `sys_config_tb`; the Edge Function reads and caches it through its service-role client.
- Notion API version: `2026-03-11`; syncing uses data-source IDs and stores each source UUID in Notion's `Supabase ID` property.

### Normal Write Path
For the user's goal, write to Supabase from any device or connector. This includes ChatGPT's Supabase connector. If the write lands in `transactions_table`, `wallet_transfer_tb`, or `wallet_accounts_tb`, it syncs to Notion automatically.

---

## 6. Data Rules

- Use `transactions_table.type` values `Income` or `Expense`.
- Use `wallet_transfer_tb` for wallet-to-wallet movement, not two ledger rows.
- Lending transactions use category `Loans & Debt` and require borrower metadata.
- Subscription transactions use category `Subscription` and can create/update `subscriptions_list`.
- Investment transactions use category `Invest Funds` and tags/platform metadata.
- `status` is supported for subscriptions (`Active`, `Expired`) and tuitions (`Active`, `Paused`, `Expired`). All other standard ledger transactions default to `status = NULL`.
- Subcategory is retired; use `tags` / Notion `Tag`.
- **Tag Uniqueness**: Every tag must belong uniquely to exactly ONE parent category. Never duplicate tag names across different parent categories.
- **Tag Semantics & Naming**: Use clean PascalCase tags. Ensure income transactions use income-oriented tags (`PassiveInc`, `SalaryPaid`, `InterestIn`), and commute tags use explicit names (`DailyCommute`, `OtherCommute`, `CampusTrip`, `SocialTrip`, `TutorTrips`).

---

## 7. Changing Financial Facts

Tuition rates, statuses, balances, due dates, and receivables belong in Supabase or the canonical Second Brain finance notes—not this routing file. Always retrieve them live before answering or making a recommendation.

---

## 8. Copy-Ready SQL

Run queries via the Supabase dashboard or the Supabase MCP `execute_sql` tool.

### Live Wallet Balances
```sql
SELECT name AS wallet_name, balance
FROM wallet_balances_vw
ORDER BY name;
```

### Outstanding Loans
```sql
SELECT borrower, outstanding, times_lent, times_repaid, last_lent_date, last_repaid_date
FROM loans_receivable_v
ORDER BY borrower;
```

### Active Subscriptions
```sql
SELECT title, amount, wallet, status, start_date, end_date, duration, days_remaining
FROM active_recur_bills
ORDER BY days_remaining ASC;
```

### Investment Summary
```sql
SELECT i.platform,
       SUM(CASE WHEN i.direction = 'Invested' THEN t.amount ELSE 0 END) AS invested,
       SUM(CASE WHEN i.direction = 'Returned' THEN t.amount ELSE 0 END) AS returned,
       SUM(CASE WHEN i.direction = 'Invested' THEN t.amount ELSE 0 END)
     - SUM(CASE WHEN i.direction = 'Returned' THEN t.amount ELSE 0 END) AS outstanding
FROM investment_tracker i
JOIN transactions_table t ON i.transaction_id = t.id
GROUP BY i.platform
ORDER BY i.platform;
```

### Recent Transactions
```sql
SELECT date, title, amount, type, status
FROM unified_register_v
ORDER BY date DESC
LIMIT 20;
```

### Sync Queue
```sql
SELECT status, COUNT(*)
FROM sync_queue
GROUP BY status
ORDER BY status;
```

### Unsynced Records
```sql
SELECT 'transactions' AS table_name, COUNT(*) FROM transactions_table WHERE notion_id IS NULL
UNION ALL
SELECT 'transfers', COUNT(*) FROM wallet_transfer_tb WHERE notion_id IS NULL;
```
