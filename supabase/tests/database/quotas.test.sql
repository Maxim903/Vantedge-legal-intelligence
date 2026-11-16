begin;
select plan(14);

insert into auth.users (id, email) values
  ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'quota-a@test.local'),
  ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'quota-b@test.local');
insert into public.plans (code, quota_mensuel_analyses) values ('quota-test', 2);
insert into public.subscriptions (user_id, stripe_customer_id, plan_code, statut)
values ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'cus_quota_a', 'quota-test', 'active');
insert into public.usage_quotas (user_id, periode, consomme)
values (
  'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
  (date_trunc('month', statement_timestamp() at time zone 'UTC') - interval '1 month')::date,
  2
);

select is(
  (public.quota_mensuel('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', false)->>'consomme')::int,
  0, 'le nouveau mois ignore la consommation du mois précédent'
);
select is(
  public.quota_mensuel('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', false)->>'periode',
  date_trunc('month', statement_timestamp() at time zone 'UTC')::date::text,
  'la période est le premier jour du mois UTC'
);
select is(
  (select count(*)::int from public.usage_quotas),
  1, 'la vérification ne crée aucune ligne'
);
select is(
  (public.quota_mensuel('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', true)->>'consomme')::int,
  1, 'la première consommation crée le compteur'
);
select is(
  (public.quota_mensuel('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', true)->>'autorise')::boolean,
  true, 'la dernière unité est autorisée'
);
select is(
  public.quota_mensuel('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', false)->>'motif',
  'limite_atteinte', 'la vérification refuse après la dernière unité'
);
select is(
  public.quota_mensuel('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', true)->>'motif',
  'limite_atteinte', 'la consommation supplémentaire est refusée'
);
select is(
  (select consomme from public.usage_quotas
   where user_id = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'
     and periode = date_trunc('month', statement_timestamp() at time zone 'UTC')::date),
  2, 'le compteur ne dépasse pas le plafond'
);
select is(
  public.quota_mensuel('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', true)->>'motif',
  'plan_absent', 'un utilisateur sans plan est refusé'
);
select is(
  (select count(*)::int from public.usage_quotas
   where user_id = 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb'),
  0, 'un utilisateur sans plan ne crée pas de compteur'
);
update public.plans set quota_mensuel_analyses = 0 where code = 'quota-test';
select is(
  public.quota_mensuel('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', true)->>'motif',
  'limite_atteinte', 'une limite nulle refuse toute consommation'
);
select is(has_function_privilege('authenticated', 'public.quota_mensuel(uuid,boolean)', 'EXECUTE'),
  false, 'les utilisateurs ne peuvent pas appeler le service privilégié');
select is(has_function_privilege('anon', 'public.quota_mensuel(uuid,boolean)', 'EXECUTE'),
  false, 'les anonymes ne peuvent pas appeler le service privilégié');
select is(has_function_privilege('service_role', 'public.quota_mensuel(uuid,boolean)', 'EXECUTE'),
  true, 'le rôle service peut appeler la fonction');

select * from finish();
rollback;
