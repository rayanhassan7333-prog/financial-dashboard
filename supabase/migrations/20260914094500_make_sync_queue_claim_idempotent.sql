begin;

create or replace function public.fn_claim_sync_queue(p_queue_id bigint)
returns boolean
language plpgsql
security definer
set search_path = pg_catalog, public
as $$
begin
    update public.sync_queue
    set status = 'processing',
        attempts = coalesce(attempts, 0) + 1,
        processed_at = null,
        error_msg = null
    where id = p_queue_id
      and status in ('pending', 'error');

    if found then
        return true;
    end if;
    if exists (select 1 from public.sync_queue where id = p_queue_id and status = 'done') then
        return false;
    end if;
    raise exception 'Queue item % cannot be claimed', p_queue_id;
end;
$$;

revoke execute on function public.fn_claim_sync_queue(bigint) from public, anon, authenticated;
grant execute on function public.fn_claim_sync_queue(bigint) to service_role;

drop function public.fn_increment_sync_attempt(bigint);

commit;
