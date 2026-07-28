---
name: financial-db-sync
description: Workflows for checking Supabase-to-Notion sync health, resolving pending queue items, and managing subscription alignment.
---

# Financial Database Sync Skill

## Account & Wallet Provisioning Workflow
When creating or adding a new wallet/account (e.g. Binance, Wise, etc.):
1. **Insert into Supabase**: Add record to `wallet_accounts_tb` with `name`.
2. **Create Notion Wallet Page**: Create page in Notion Wallet Database (`36e24426-9ef8-80e8-a27b-f7a6462d41a3`) titled with the wallet name.
3. **Link notion_id Immediately**:
   ```sql
   UPDATE wallet_accounts_tb
   SET notion_id = '<notion_page_id>'
   WHERE id = '<account_id>';
   ```

## Fast Transaction & Transfer Execution
1. **Wallet Transfers**: Insert into `wallet_transfer_tb` with `source_account_id`, `dest_account_id`, `amount`, and `date`.
2. **Ledger Transactions**: Insert into `transactions_table` with `account_id`, `category_id`, `type`, `amount`, `tags` (PascalCase array), `status` (set to `Active` for subscriptions, `NULL` otherwise), `end_date` (for subscriptions), and `notes` containing `Duration: <Text>` for subscriptions.
3. **Automated Sync Verification**: Verify `sync_queue` item transitions to `status = 'done'` via Edge Function `sync-to-notion` (v7).

## Diagnostics
1. **Check Sync Queue Status**:
   ```sql
   SELECT id, record_id, status, error_msg, processed_at
   FROM sync_queue
   WHERE status != 'done';
   ```

2. **Check Unsynced Rows**:
   ```sql
   SELECT 'transactions' AS table_name, COUNT(*) FROM transactions_table WHERE notion_id IS NULL
   UNION ALL
   SELECT 'transfers', COUNT(*) FROM wallet_transfer_tb WHERE notion_id IS NULL;
   ```

## Queue Resolution Workflow
When a queue item fails (e.g. Notion API `409 Conflict Error` or rate limit):
1. **Inspect Record in Supabase**: Retrieve current properties (`title`, `amount`, `date`, `tags`, `status`, `notes`) from `transactions_table` or `wallet_transfer_tb`.
2. **Patch Notion Page Directly**: Use Notion MCP tool `API-patch-page` to update missing or outdated properties on the corresponding `notion_id` page.
3. **Update Queue Status**:
   ```sql
   UPDATE sync_queue
   SET status = 'done', error_msg = NULL, processed_at = NOW()
   WHERE id = <queue_id>;
   ```

## Subscription Synchronization
1. When updating a subscription's status or end date in `transactions_table`, verify that `subscriptions_list` reflects the changes:
   ```sql
   SELECT * FROM subscriptions_list WHERE transaction_id = '<transaction_id>';
   ```
2. Verify inclusion in the active bills view:
   ```sql
   SELECT * FROM active_recur_bills WHERE transaction_id = '<transaction_id>';
   ```
