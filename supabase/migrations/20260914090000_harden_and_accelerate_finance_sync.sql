begin;

create index if not exists wallet_transfer_source_account_idx
    on public.wallet_transfer_tb (source_account_id);

create index if not exists wallet_transfer_dest_account_idx
    on public.wallet_transfer_tb (dest_account_id);

create index if not exists sync_queue_open_created_idx
    on public.sync_queue (created_at)
    where status in ('pending', 'processing', 'error');

alter view public.unified_register_v set (security_invoker = true);

alter function public.ai_snapshot(integer, integer)
    set search_path = pg_catalog, public, pg_temp;
alter function public.trg_process_special_categories_fn()
    set search_path = pg_catalog, public;
alter function public.trg_populate_transfer_title_fn()
    set search_path = pg_catalog, public;

create or replace function public.fn_increment_sync_attempt(p_queue_id bigint)
returns void
language plpgsql
security definer
set search_path = pg_catalog, public
as $$
begin
    update public.sync_queue
    set attempts = coalesce(attempts, 0) + 1
    where id = p_queue_id
      and status = 'processing';

    if not found then
        raise exception 'Queue item % is not processing', p_queue_id;
    end if;
end;
$$;

create or replace function public.fn_sync_complete_callback(
    p_queue_id bigint,
    p_table text,
    p_record_id uuid,
    p_notion_id uuid
)
returns void
language plpgsql
security definer
set search_path = pg_catalog, public
as $$
declare
    v_queue_table text;
    v_queue_record uuid;
begin
    if p_table not in ('transactions_table', 'wallet_transfer_tb', 'wallet_accounts_tb') then
        raise exception 'Unsupported source table: %', p_table;
    end if;

    select table_name, record_id
      into v_queue_table, v_queue_record
    from public.sync_queue
    where id = p_queue_id
    for update;

    if not found then
        raise exception 'Queue item % does not exist', p_queue_id;
    end if;
    if v_queue_table is distinct from p_table or v_queue_record is distinct from p_record_id then
        raise exception 'Queue callback does not match its source row';
    end if;

    if p_notion_id is not null then
        if p_table = 'transactions_table' then
            update public.transactions_table
            set notion_id = p_notion_id, updated_at = now()
            where id = p_record_id and notion_id is distinct from p_notion_id;
        elsif p_table = 'wallet_transfer_tb' then
            update public.wallet_transfer_tb
            set notion_id = p_notion_id, updated_at = now()
            where id = p_record_id and notion_id is distinct from p_notion_id;
        else
            update public.wallet_accounts_tb
            set notion_id = p_notion_id, updated_at = now()
            where id = p_record_id and notion_id is distinct from p_notion_id;
        end if;
    end if;

    update public.sync_queue
    set status = 'done', processed_at = now(), error_msg = null
    where id = p_queue_id;
end;
$$;

create or replace function public.trg_realtime_sync_to_notion_fn()
returns trigger
language plpgsql
set search_path = pg_catalog, public, extensions
as $$
declare
    v_webhook_url constant text := 'https://pyryeeewtdypukuprgwc.supabase.co/functions/v1/sync-to-notion';
    v_notion_token text;
    v_headers jsonb;
    v_payload jsonb;
    v_crucial_changed boolean := true;
    v_queue_id bigint;
    v_resolved jsonb := '{}'::jsonb;
    v_signature text;
begin
    if current_setting('myapp.disable_sync_trigger', true) = 'true' then
        return coalesce(new, old);
    end if;

    if tg_op = 'UPDATE' then
        if tg_table_name = 'transactions_table' then
            v_crucial_changed := not (
                new.date is not distinct from old.date and
                new.title is not distinct from old.title and
                new.amount is not distinct from old.amount and
                new.notes is not distinct from old.notes and
                new.type is not distinct from old.type and
                new.account_id is not distinct from old.account_id and
                new.category_id is not distinct from old.category_id and
                new.status is not distinct from old.status and
                new.tags is not distinct from old.tags and
                new.end_date is not distinct from old.end_date
            );
        elsif tg_table_name = 'wallet_transfer_tb' then
            v_crucial_changed := not (
                new.date is not distinct from old.date and
                new.title is not distinct from old.title and
                new.amount is not distinct from old.amount and
                new.source_account_id is not distinct from old.source_account_id and
                new.dest_account_id is not distinct from old.dest_account_id and
                new.notes is not distinct from old.notes
            );
        elsif tg_table_name = 'wallet_accounts_tb' then
            v_crucial_changed := new.name is distinct from old.name;
        end if;
    end if;

    if not v_crucial_changed then
        return new;
    end if;

    if tg_op = 'DELETE' then
        insert into public.sync_queue (table_name, record_id, operation, payload)
        values (tg_table_name, old.id, 'DELETE', jsonb_build_object('id', old.id, 'notion_id', old.notion_id))
        returning id into v_queue_id;
    else
        if tg_table_name = 'transactions_table' then
            v_resolved := jsonb_build_object(
                'wallet_notion_id', (select notion_id from public.wallet_accounts_tb where id = new.account_id),
                'category_name', (select name from public.parent_category_tb where id = new.category_id),
                'borrower', (select borrower::text from public.lending_records_tb where transaction_id = new.id),
                'end_date', (select end_date from public.subscriptions_list where transaction_id = new.id)
            );
        elsif tg_table_name = 'wallet_transfer_tb' then
            v_resolved := jsonb_build_object(
                'source_wallet_notion_id', (select notion_id from public.wallet_accounts_tb where id = new.source_account_id),
                'dest_wallet_notion_id', (select notion_id from public.wallet_accounts_tb where id = new.dest_account_id)
            );
        end if;

        insert into public.sync_queue (table_name, record_id, operation, payload)
        values (tg_table_name, new.id, tg_op, to_jsonb(new))
        returning id into v_queue_id;
    end if;

    select value into strict v_notion_token
    from public.sys_config_tb
    where key = 'NOTION_TOKEN';

    v_payload := jsonb_build_object(
        'queue_id', v_queue_id,
        'type', tg_op,
        'table', tg_table_name,
        'record', case when tg_op in ('INSERT', 'UPDATE') then to_jsonb(new) else null end,
        'old_record', case when tg_op in ('UPDATE', 'DELETE') then to_jsonb(old) else null end,
        'resolved', v_resolved
    );
    v_signature := encode(
        extensions.hmac(convert_to(v_payload::text, 'UTF8'), convert_to(v_notion_token, 'UTF8'), 'sha256'),
        'hex'
    );
    v_headers := jsonb_build_object(
        'Content-Type', 'application/json',
        'x-webhook-signature', v_signature
    );

    perform net.http_post(url := v_webhook_url, body := v_payload, headers := v_headers);
    return coalesce(new, old);
exception
    when no_data_found then
        raise exception 'NOTION_TOKEN is missing from sys_config_tb';
end;
$$;

revoke execute on function public.ai_snapshot(integer, integer) from public, anon, authenticated;
grant execute on function public.ai_snapshot(integer, integer) to service_role;

revoke execute on function public.fn_sync_complete_callback(bigint, text, uuid, uuid) from public, anon, authenticated;
grant execute on function public.fn_sync_complete_callback(bigint, text, uuid, uuid) to service_role;

revoke execute on function public.fn_increment_sync_attempt(bigint) from public, anon, authenticated;
grant execute on function public.fn_increment_sync_attempt(bigint) to service_role;

revoke all on table public.sync_queue, public.sys_config_tb from public, anon, authenticated;
grant all on table public.sync_queue, public.sys_config_tb to service_role;
grant usage, select on sequence public.sync_queue_id_seq to service_role;

comment on function public.trg_realtime_sync_to_notion_fn() is
    'Queues source changes and sends an HMAC-authenticated payload to sync-to-notion.';
comment on function public.fn_sync_complete_callback(bigint, text, uuid, uuid) is
    'Service-role-only callback that validates queue/source identity before completing a Notion sync.';

commit;
