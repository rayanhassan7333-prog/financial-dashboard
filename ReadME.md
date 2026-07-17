# Financial Dashboard Agent Map

Read this first. It is the compact source map for AI agents working in this folder.

Supabase Postgres is the source of truth. Notion is the synced presentation layer. Local files are helpers, generated caches, or docs.

Last Generated: 2026-07-12 22:25:32 (Supabase Postgres)

---

## 1. Fast Path

- Supabase is the source of truth, and Notion is the synced presentation layer.
- All syncing operates automatically in the cloud via database triggers and Supabase Edge Functions.
- To inspect or run SQL queries, use the Supabase MCP server tool `execute_sql` or the Supabase dashboard.
- Do not start with Notion unless necessary. The database is faster and more complete.

---

## 2. Current Live Summary

| Metric | Value |
| :--- | :--- |
| Total Cash & Bank Assets | 124,873.48 BDT |
| Outstanding Loans to Receive | 53,054.00 BDT |
| Active Subscriptions Count | 6 |
| Ledger Transactions | 634 |
| Transfers | 121 |

### Live Account Balances
- BKash: 2,775.55 BDT
- Bank: 100,747.93 BDT
- Cash: 1,350.00 BDT
- Savings: 20,000.00 BDT

### Loans Outstanding
- Waraka: 53,130.00 BDT
- Zayed: 0.00 BDT
- Mayan & Mom: 0.00 BDT (Fully Repaid)

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
- `transactions_table`: Ledger transactions. Core source for income and expenses.
- `wallet_transfer_tb`: Wallet transfers.
- `wallet_accounts_tb`: Wallet/account lookup table.
- `parent_category_tb`: Category lookup table.
- `lending_records_tb`: Loan metadata attached to transaction rows.
- `subscriptions_list`: Subscription metadata attached to transaction rows.
- `investment_tracker`: Investment metadata attached to transaction rows.
- `sync_queue`: Backup/retry/audit queue for Supabase-to-Notion sync.
- `sys_config_tb`: Internal sync config.

There is no active `sub_category_tb` table and no `transactions_table.subcategory_id` column. Tags are stored in `transactions_table.tags` and synced to Notion `Tag`.

### Views
- `unified_register_v`: Main read view for ledger + transfers.
- `wallet_balances_vw`: Current wallet balances.
- `loans_receivable_v`: Outstanding loan balances.
- `active_recur_bills`: Active subscription view.
- `monthly_aggregates`, `net_worth_snapshot`, `investment_summary_v`: Summary/reporting views.

### Functions And Triggers
- `ai_snapshot(recent_limit, subscription_limit)`: compact JSON state for agents.
- `trg_realtime_sync_to_notion_fn()`: trigger function for outbound Notion sync.
- `trg_process_special_categories_fn()`: keeps lending/subscription/investment helper rows aligned.
- `update_updated_at_column()`: timestamp helper.
- `trg_enqueue_notion_sync` runs on `INSERT`, `UPDATE`, and `DELETE` for `transactions_table` and `wallet_transfer_tb`.

---

## 5. Notion Connection Setup

### Notion Databases
- Root dashboard: `36e24426-9ef8-8021-8e53-d993b3d7eb40`
- Ledger database: `36e24426-9ef8-8070-bc1c-ea1ecd148662`
- Ledger data source: `36e24426-9ef8-8083-a8d0-000b7e61fb41`
- Transfer database: `36e24426-9ef8-8098-841d-e2bb26b6418e`
- Transfer data source: `36e24426-9ef8-800f-be2a-000b0e5aadff`
- Wallet database: `36e24426-9ef8-80e8-a27b-f7a6462d41a3`
- Wallet data source: `36e24426-9ef8-80e2-886f-000b593d2fc4`

Current live Notion sources visible through local Notion MCP: `Ledger`, `Wallet`, `Transfer`.

### Sync Flow
1. A row is added, updated, or deleted in Supabase `transactions_table` or `wallet_transfer_tb`.
2. Supabase trigger `trg_realtime_sync_to_notion_fn()` writes a `sync_queue` backup row.
3. The same trigger calls the deployed Edge Function `sync-to-notion` asynchronously through `pg_net`.
4. `sync-to-notion` creates, updates, or archives the matching Notion page.
5. The Edge Function writes `notion_id` back to Supabase when it creates or finds a Notion page.
6. The Edge Function marks the queue row `done` or `error`.

### Edge Function
- Name: `sync-to-notion`
- Local source: `supabase/functions/sync-to-notion/index.ts`
- Deployed version last verified in this workspace: `6`
- JWT verification is disabled because the database trigger authenticates with `WEBHOOK_SECRET`.
- Required secrets: `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `NOTION_TOKEN`, `WEBHOOK_SECRET`.

### Normal Write Path
For the user's goal, write to Supabase from any device or connector. This includes ChatGPT's Supabase connector. If the write lands in `transactions_table` or `wallet_transfer_tb`, it should sync to Notion automatically.

---

## 6. Data Rules

- Use `transactions_table.type` values `Income` or `Expense`.
- Use `wallet_transfer_tb` for wallet-to-wallet movement, not two ledger rows.
- Lending transactions use category `Loans & Debt` and require borrower metadata.
- Subscription transactions use category `Subscription` and can create/update `subscriptions_list`.
- Investment transactions use category `Invest Funds` and tags/platform metadata.
- `status` is for subscriptions only. Lending status should stay `NULL`.
- Subcategory is retired; use `tags` / Notion `Tag`.

---

## 7. Tuition Reference

| Tuition Name | Start Date | Monthly Rate | Expected Payment Date |
| :--- | :---: | :---: | :--- |
| Tuition: Nabiha | Jan 2025 | 8,000 TK (14,000 TK in 2025) | By the end of the month |
| Tuition: Ayesha | Jan 2026 | 9,000 TK | By the end of the month |
| Tuition: Mayan | Jan 2026 | 8,000 TK (or 12,000 TK) | By the end of the month; consistently late |

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
