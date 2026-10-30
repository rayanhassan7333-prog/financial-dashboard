# Financial Database Operational Rules

1. **Source of Truth**: Supabase Postgres is the source of truth. Write to base tables (`transactions_table`, `wallet_transfer_tb`) ONLY. Never write to views (`unified_register_v`).
2. **UUID Lookups**: Always look up `account_id` from `wallet_accounts_tb` and `category_id` from `parent_category_tb` before inserting or updating rows. Never pass raw string names into UUID columns.
3. **Status Field Scoping**: Discover the current status constraints and special-category trigger before writing. Subscriptions and tuition records may have category-specific lifecycle statuses; ordinary transactions use `NULL` unless the live schema establishes a supported exception. Do not apply a subscription-only restriction to tuition records or copy a cached status list.
4. **Subscription End Date & Duration**: Enter `end_date` (YYYY-MM-DD) separately as a dedicated column in `transactions_table`. Write duration in `notes` as `Duration: <Text>` (e.g. `Duration: 1 Year`). The database trigger extracts `duration` from notes and copies `end_date` to `subscriptions_list`.
5. **Execution Verification**: Verify database writes by reading back the affected base and relevant derived records. Queue status alone does not prove ledger correctness. When Notion mirroring is part of the requested outcome, also verify the queue result and destination record.
