-- Un mois calendaire UTC et une unité par consommation.
-- Le verrou sur l'abonnement sérialise les consommations d'un utilisateur et
-- empêche un changement de plan pendant la décision ; celui du plan protège sa limite.
create function public.quota_mensuel(p_user_id uuid, p_consume boolean)
returns jsonb
language plpgsql
security invoker
set search_path = ''
as $$
declare
  v_periode date := date_trunc('month', statement_timestamp() at time zone 'UTC')::date;
  v_plan text;
  v_limite integer;
  v_consomme integer;
  v_autorise boolean;
begin
  if p_user_id is null or p_consume is null then
    raise exception 'user_id et consume sont obligatoires' using errcode = '22004';
  end if;

  select s.plan_code, p.quota_mensuel_analyses
  into v_plan, v_limite
  from public.subscriptions s
  join public.plans p on p.code = s.plan_code
  where s.user_id = p_user_id
  for update of s
  for share of p;

  if not found then
    return jsonb_build_object(
      'autorise', false, 'motif', 'plan_absent', 'periode', v_periode,
      'plan', null, 'limite', null, 'consomme', null
    );
  end if;

  select q.consomme into v_consomme
  from public.usage_quotas q
  where q.user_id = p_user_id and q.periode = v_periode;
  v_consomme := coalesce(v_consomme, 0);

  v_autorise := v_consomme < v_limite;
  if p_consume and v_autorise then
    insert into public.usage_quotas as q (user_id, periode, consomme)
    values (p_user_id, v_periode, 1)
    on conflict (user_id, periode) do update
      set consomme = q.consomme + 1
      where q.consomme < v_limite
    returning q.consomme into v_consomme;

    if not found then
      v_autorise := false;
      select q.consomme into v_consomme
      from public.usage_quotas q
      where q.user_id = p_user_id and q.periode = v_periode;
    end if;
  end if;

  return jsonb_build_object(
    'autorise', v_autorise,
    'motif', case when v_autorise then null else 'limite_atteinte' end,
    'periode', v_periode, 'plan', v_plan, 'limite', v_limite, 'consomme', v_consomme
  );
end;
$$;

revoke all on function public.quota_mensuel(uuid, boolean) from public, anon, authenticated;
grant execute on function public.quota_mensuel(uuid, boolean) to service_role;
