# Financial Database Operational Rules

1. **Source of Truth**: Supabase Postgres is the source of truth. Write to base tables (`transactions_table`, `wallet_transfer_tb`) ONLY. Never write to views (`unified_register_v`).
2. **UUID Lookups**: Always look up `account_id` from `wallet_accounts_tb` and `category_id` from `parent_category_tb` before inserting or updating rows. Never pass raw string names into UUID columns.
3. **Status Field Scoping**: `status` MUST be `NULL` for all non-subscription transactions. Only Subscription category rows may have `status` set (`Active`, `Expired`, `Paused`).
4. **Subscription End Date & Duration**: Enter `end_date` (YYYY-MM-DD) separately as a dedicated column in `transactions_table`. Write duration in `notes` as `Duration: <Text>` (e.g. `Duration: 1 Year`). The database trigger extracts `duration` from notes and copies `end_date` to `subscriptions_list`.
5. **Execution Verification**: Always verify database writes by selecting updated rows or checking `sync_queue` status.
