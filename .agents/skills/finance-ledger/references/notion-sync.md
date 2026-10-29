# Notion synchronization

## Establish the current pipeline

- Discover the live triggers, queue schema, completion routines, and deployed worker configuration. Repository source under `supabase/functions/` and migrations explains intended behavior; compare it with deployed behavior before relying on implementation details during recovery.
- Discovery hints are `sync_queue`, `trg_enqueue_notion_sync`, `sync-to-notion`, `fn_claim_sync_queue`, and `fn_sync_complete_callback`. Verify signatures and constraints before invoking anything; discover replacements if these names change.
- Resolve destination databases or data sources from the current integration configuration without printing secrets. Use the available Notion tool schema or current API documentation rather than embedding a client-specific invocation.

## Diagnose with minimal reads

- Aggregate queue counts by live status, and return a bounded relevant sample of errors, attempts, and timestamps. Keep total backlog separate from sample size. Distinguish queued, actively processing, failed, and completed work using the live status semantics.
- Check missing source `notion_id` links separately from queue status. A present link does not prove property freshness, and a missing link can mean normal asynchronous work is still pending.
- Inspect only the affected source row's actual columns and relationships. Wallet, transaction, and transfer rows have different shapes.
- Follow the affected record through queue, worker logs, and Notion destination as needed. Compare intended properties, relationships, and archive state; do not treat a successful HTTP response alone as proof of the desired result.
- Use a bounded observation window when waiting for completion. Avoid repeated polling of unchanged state; report pending work honestly if the pipeline has not completed.

## Recover without duplicating or hiding failures

- Diagnose the cause before retrying: transient API failure, permission issue, missing relation, invalid property, stale payload, or worker failure. Check whether the worker already retries and deduplicates that operation.
- Prefer the existing authenticated recovery or replay mechanism after verifying how it claims queue items, handles already-completed work, and finds existing Notion pages. Use the current source state where the integration requires it, preserving deletion identity and intended archive behavior.
- Changing queue status alone does not prove that a worker will replay it. If no supported replay path exists, determine the actual mechanism before mutating queue state; do not invent an unauthenticated webhook call.
- Honor the destination's retry guidance with bounded backoff. After an uncertain external outcome, look up the existing page by its stable source identity before attempting creation again.
- Manual Notion repair is a fallback within an authorized repair request. Confirm the exact source-to-page identity, patch the correct properties or archive state, and read back the outcome before completing the queue item.
- Use the verified atomic completion routine to reconcile the source link and queue together. Never mark an item completed merely to clear an error, and never claim a currently processing item without resolving worker ownership and stale-work rules.
- Verify the repaired source link, queue outcome, and destination properties. If only part succeeded, report that state and leave enough diagnostic evidence for recovery.

## Authentication and deployments

- Inspect the deployed worker's authentication and caller before redeploying. A signed database webhook and a user-JWT invocation require different checks; preserve signature validation and use current platform guidance for the applicable configuration.
- Keep signing secrets and service credentials in their configured secret stores. Do not include them in model input, generated recovery payloads, console output, or reports.
- Verify the actual deployed change with an authorized, narrowly scoped operation. A local code review or successful deployment alone does not establish end-to-end synchronization health.
