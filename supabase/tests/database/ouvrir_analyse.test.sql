begin;
select plan(15);

insert into auth.users (id, email) values
  ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'ouverture-a@test.local'),
  ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'ouverture-b@test.local');
insert into public.plans (code, quota_mensuel_analyses) values ('ouverture-test', 1);
insert into public.subscriptions (user_id, stripe_customer_id, plan_code, statut)
values ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'cus_ouverture', 'ouverture-test', 'active');
insert into public.projects (id, user_id, nom) values
  ('a1111111-1111-4111-8111-111111111111', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'A'),
  ('b1111111-1111-4111-8111-111111111111', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'B');

select is(public.ouvrir_analyse('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'a1111111-1111-4111-8111-111111111111', 'notion-1')->>'statut', 'cree', 'première ouverture');
select is((select count(*)::int from public.analyses), 1, 'analyse enregistrée');
select is((select parametres->>'notion_id' from public.analyses limit 1), 'notion-1', 'notion enregistrée');
select is((select consomme from public.usage_quotas where user_id = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'), 1, 'une unité consommée');
select is(public.ouvrir_analyse('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'a1111111-1111-4111-8111-111111111111', 'notion-1')->>'statut', 'existante', 'réouverture gratuite même quota épuisé');
select is((select count(*)::int from public.analyses), 1, 'pas de doublon');
select is(public.ouvrir_analyse('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'a1111111-1111-4111-8111-111111111111', 'notion-2')->>'statut', 'refusee', 'quota épuisé');
select is((select count(*)::int from public.analyses), 1, 'aucune analyse pour un refus');
select throws_ok(
  $$select public.ouvrir_analyse('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'b1111111-1111-4111-8111-111111111111', 'notion-3')$$,
  '42501', null, 'projet étranger refusé'
);
select is((select consomme from public.usage_quotas where user_id = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'), 1, 'refus sans consommation');
insert into public.analyses (project_id, user_id, parametres)
values ('a1111111-1111-4111-8111-111111111111', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', '{"notion_id":"ancienne"}');
select is(public.ouvrir_analyse('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'a1111111-1111-4111-8111-111111111111', 'ancienne')->>'statut', 'refusee', 'une ancienne ligne non vérifiée ne donne pas accès');

update public.plans set quota_mensuel_analyses = 2 where code = 'ouverture-test';
create function pg_temp.refuse_analyse() returns trigger language plpgsql as $$
begin raise exception 'test insertion'; end;
$$;
create trigger refuser_analyse before insert on public.analyses
for each row execute function pg_temp.refuse_analyse();
select throws_ok(
  $$select public.ouvrir_analyse('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'a1111111-1111-4111-8111-111111111111', 'notion-3')$$,
  'P0001', 'test insertion', 'une erreur d’insertion est propagée'
);
select is((select consomme from public.usage_quotas where user_id = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'), 1, 'la consommation est annulée avec l’insertion');
select is(has_function_privilege('authenticated', 'public.ouvrir_analyse(uuid,uuid,text)', 'EXECUTE'), false, 'fonction interdite aux clients');
select is(has_function_privilege('service_role', 'public.ouvrir_analyse(uuid,uuid,text)', 'EXECUTE'), true, 'fonction autorisée au service');

select * from finish();
rollback;
