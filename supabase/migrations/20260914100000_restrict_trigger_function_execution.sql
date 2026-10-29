begin;

revoke execute on function public.trg_realtime_sync_to_notion_fn() from public, anon, authenticated;
revoke execute on function public.trg_process_special_categories_fn() from public, anon, authenticated;
revoke execute on function public.trg_populate_transfer_title_fn() from public, anon, authenticated;

grant execute on function public.trg_realtime_sync_to_notion_fn() to service_role;
grant execute on function public.trg_process_special_categories_fn() to service_role;
grant execute on function public.trg_populate_transfer_title_fn() to service_role;

commit;
