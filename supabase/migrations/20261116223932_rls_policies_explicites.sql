-- Complète les policies RLS pour que chaque table ait select, insert, update et delete
-- explicites. Une policy `using (false)` / `with check (false)` refuse l'opération aux
-- rôles client : seul le rôle service, qui contourne la RLS, peut l'effectuer.

-- profiles : créé par le trigger handle_new_user, supprimé en cascade.
create policy "profiles_insert_denied" on public.profiles for insert to anon, authenticated
  with check (false);
create policy "profiles_delete_denied" on public.profiles for delete to anon, authenticated
  using (false);
create policy "profiles_select_anon_denied" on public.profiles for select to anon
  using (false);
create policy "profiles_update_anon_denied" on public.profiles for update to anon
  using (false) with check (false);

-- plans : catalogue en lecture seule.
create policy "plans_select_anon_denied" on public.plans for select to anon
  using (false);
create policy "plans_insert_denied" on public.plans for insert to anon, authenticated
  with check (false);
create policy "plans_update_denied" on public.plans for update to anon, authenticated
  using (false) with check (false);
create policy "plans_delete_denied" on public.plans for delete to anon, authenticated
  using (false);

-- subscriptions : lecture de ses lignes, écriture réservée au rôle service.
create policy "subscriptions_select_anon_denied" on public.subscriptions for select to anon
  using (false);
create policy "subscriptions_insert_denied" on public.subscriptions for insert to anon, authenticated
  with check (false);
create policy "subscriptions_update_denied" on public.subscriptions for update to anon, authenticated
  using (false) with check (false);
create policy "subscriptions_delete_denied" on public.subscriptions for delete to anon, authenticated
  using (false);

-- usage_quotas : lecture de ses lignes, écriture réservée au rôle service.
create policy "usage_quotas_select_anon_denied" on public.usage_quotas for select to anon
  using (false);
create policy "usage_quotas_insert_denied" on public.usage_quotas for insert to anon, authenticated
  with check (false);
create policy "usage_quotas_update_denied" on public.usage_quotas for update to anon, authenticated
  using (false) with check (false);
create policy "usage_quotas_delete_denied" on public.usage_quotas for delete to anon, authenticated
  using (false);

-- stripe_events : aucun accès pour les rôles client.
create policy "stripe_events_select_denied" on public.stripe_events for select to anon, authenticated
  using (false);
create policy "stripe_events_insert_denied" on public.stripe_events for insert to anon, authenticated
  with check (false);
create policy "stripe_events_update_denied" on public.stripe_events for update to anon, authenticated
  using (false) with check (false);
create policy "stripe_events_delete_denied" on public.stripe_events for delete to anon, authenticated
  using (false);

-- projects et analyses : le rôle anon n'a aucun accès.
create policy "projects_anon_select_denied" on public.projects for select to anon
  using (false);
create policy "projects_anon_insert_denied" on public.projects for insert to anon
  with check (false);
create policy "projects_anon_update_denied" on public.projects for update to anon
  using (false) with check (false);
create policy "projects_anon_delete_denied" on public.projects for delete to anon
  using (false);
create policy "analyses_anon_select_denied" on public.analyses for select to anon
  using (false);
create policy "analyses_anon_insert_denied" on public.analyses for insert to anon
  with check (false);
create policy "analyses_anon_update_denied" on public.analyses for update to anon
  using (false) with check (false);
create policy "analyses_anon_delete_denied" on public.analyses for delete to anon
  using (false);
