# Ledger workflows

## Discover by purpose

These names are starting points, not a schema snapshot. Confirm relevant live fields and semantics when needed; inspect view definitions before treating similarly named metrics as equivalent.

| Purpose | Discovery hints |
| --- | --- |
| Income and consumption expenses | `transactions_table`, `parent_category_tb` |
| Wallet movements and principal | `wallet_transfer_tb` |
| Accounts and borrower identity | `wallet_accounts_tb`, `counterparties_tb` |
| Investment project relationships | `investment_projects_tb`, transfer `project_id` |
| Combined activity and attribution | `unified_register_v` |
| Wallet balances | `wallet_balances_vw` |
| Loans outstanding | `loans_receivable_v` |
| Investment principal and returns | `investment_summary_v` |
| Ledger net worth | `net_worth_snapshot` |
| Derived subscription periods | `subscriptions_list`, special-category trigger |

## Transactions and transfers

- Record true consumption and earned income in the transaction ledger. Resolve category names by current meaning; a historical category's continued existence does not authorize using it for loan or investment principal.
- Record internal wallet movements in the transfer ledger. Money lent flows from the funding wallet to the borrower's lending wallet; repayment reverses that direction. Investment principal deployment flows to the platform investment wallet; principal recovery reverses it.
- Link investment transfers to the actual project through the supported relationship. Resolve the project's identity, platform, and current status live. Do not infer outstanding principal from status or tags alone.
- Separate investment profit from returned principal. Preserve the established profit-title convention of project name followed by `Profit`, and resolve the income category with that meaning live. Use the platform's established tag without embedding a platform list here.
- Keep existing semantic tags and spelling. Transaction tags and transfer-direction tags can follow different conventions; do not enforce a blanket casing rule. Read the relevant view or trigger if a tag controls classification.
- For mixed receipts, separate principal recovery from profit and reconcile their sum to the actual receipt. Do not count the same movement again through both a transfer and a transaction.

## Wallet and project provisioning

- Search existing entities before creating them. Resolve the live account type and required fields, using database-generated identifiers and defaults.
- For a lending wallet, link the correct counterparty; do not equate similar borrower names without evidence.
- For an investment project, link its platform account. Create only entities needed for the authorized action.
- Let the normal sync pipeline provision Notion wallet pages. A missing Notion link should lead to sync diagnostics, not an immediate duplicate page.

## Subscriptions and tuition

- Inspect the live special-category trigger or parser before choosing subscription note syntax, status, or end-date fields. Let its normal processing populate derived subscription records, then verify those records when the requested outcome depends on them.
- Preserve established tuition recording conventions: student identity in the title prefixed by `Tuition:`, the income category by current meaning, and `SalaryPaid` where applicable. Use existing records and canonical business notes to resolve the payment period and terms.
- Payment records establish recorded receipts, not a student's current schedule or an unrecorded obligation. Do not infer receivables from an active status alone.
- Only completed past billing months count as overdue under the existing tuition convention; the ongoing month is not overdue. Apply verified fees, start/end terms, paid periods, and the user's timezone before calculating arrears.

## Analysis

- Prefer established derived views for their intended metrics, and reconcile to source records if definitions or results are uncertain.
- Keep income/expense analysis separate from principal movement. Distinguish gross receipts from earned income and principal outstanding from investment profit.
- When calculating purchase totals, verify transaction purpose and relevant purchase tags. Exclude repairs, accessories, and transport unless the user requested them.
- Do not assume every asset belongs in ledger net worth or every stored wallet amount needs conversion. Inspect the current accounting convention and currency representation before adding assets or applying exchange rates.
