begin;

create policy "service role manages sync queue"
on public.sync_queue
for all
to service_role
using (true)
with check (true);

create policy "service role manages sync config"
on public.sys_config_tb
for all
to service_role
using (true)
with check (true);

commit;
