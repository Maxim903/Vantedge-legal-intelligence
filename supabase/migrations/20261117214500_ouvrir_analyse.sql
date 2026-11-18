-- Seul le service peut créer ou modifier une analyse : son existence autorise
-- ensuite la consultation sans nouvelle consommation.
-- Les lignes préexistantes, insérables auparavant par les clients, ne prouvent
-- pas une consommation de quota.
alter table public.analyses add column quota_verifie boolean not null default false;
drop policy "analyses_insert_own" on public.analyses;
drop policy "analyses_update_own" on public.analyses;
revoke insert, update on public.analyses from anon, authenticated;

create function public.ouvrir_analyse(p_user_id uuid, p_project_id uuid, p_notion_id text)
returns jsonb
language plpgsql
security invoker
set search_path = ''
as $$
declare
  v_quota jsonb;
begin
  if p_user_id is null or p_project_id is null
      or p_notion_id is null or length(trim(p_notion_id)) = 0 then
    raise exception 'utilisateur, projet et notion obligatoires' using errcode = '22004';
  end if;

  -- Sérialise les ouvertures concurrentes d'une même notion dans ce projet.
  perform 1 from public.projects
  where id = p_project_id and user_id = p_user_id
  for update;
  if not found then
    raise exception 'projet introuvable ou inaccessible' using errcode = '42501';
  end if;

  if exists (
    select 1 from public.analyses
    where project_id = p_project_id and user_id = p_user_id
      and quota_verifie
      and parametres @> jsonb_build_object('notion_id', p_notion_id)
  ) then
    return jsonb_build_object('statut', 'existante');
  end if;

  v_quota := public.quota_mensuel(p_user_id, true);
  if not (v_quota->>'autorise')::boolean then
    return jsonb_build_object('statut', 'refusee', 'quota', v_quota);
  end if;

  insert into public.analyses (project_id, user_id, parametres, quota_verifie)
  values (p_project_id, p_user_id, jsonb_build_object('notion_id', p_notion_id), true);
  return jsonb_build_object('statut', 'cree', 'quota', v_quota);
end;
$$;

revoke all on function public.ouvrir_analyse(uuid, uuid, text) from public, anon, authenticated;
grant execute on function public.ouvrir_analyse(uuid, uuid, text) to service_role;
