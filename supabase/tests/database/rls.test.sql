begin;
select plan(37);

-- Jeu de données (rôle postgres, la RLS est contournée).
insert into auth.users (id, email) values
  ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'a@test.local'),
  ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'b@test.local');
update public.profiles set display_name = 'Alice' where id = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa';
update public.profiles set display_name = 'Bob' where id = 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb';

insert into public.plans (code, quota_mensuel_analyses) values ('test', 5);
insert into public.subscriptions (user_id, stripe_customer_id, plan_code, statut) values
  ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'cus_a', 'test', 'active'),
  ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'cus_b', 'test', 'active');
insert into public.usage_quotas (user_id, periode, consomme) values
  ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', '2026-11-01', 1),
  ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', '2026-11-01', 2);
insert into public.stripe_events (event_id) values ('evt_1');
insert into public.projects (id, user_id, nom) values
  ('a1111111-1111-1111-1111-111111111111', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'projet A'),
  ('b1111111-1111-1111-1111-111111111111', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'projet B');
insert into public.analyses (id, project_id, user_id, parametres) values
  ('a2222222-2222-2222-2222-222222222222', 'a1111111-1111-1111-1111-111111111111',
   'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', '{"q": "a"}'),
  ('b2222222-2222-2222-2222-222222222222', 'b1111111-1111-1111-1111-111111111111',
   'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', '{"q": "b"}');

-- ===== Utilisateur A =====
select set_config('request.jwt.claims',
  '{"sub": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", "role": "authenticated"}', true);
set local role authenticated;

-- Lecture : seulement ses propres lignes.
select is((select count(*) from public.profiles)::int, 1, 'A ne voit que son profil');
select is((select count(*) from public.projects)::int, 1, 'A ne voit que son projet');
select is((select count(*) from public.analyses)::int, 1, 'A ne voit que son analyse');
select is((select count(*) from public.subscriptions)::int, 1, 'A ne voit que sa souscription');
select is((select count(*) from public.usage_quotas)::int, 1, 'A ne voit que son quota');
select is((select count(*) from public.plans)::int, 1, 'A lit le catalogue des plans');
select throws_ok('select * from public.stripe_events', '42501', null, 'A ne lit pas stripe_events');

-- Modification et suppression des lignes de B : sans effet.
select lives_ok($$update public.profiles set display_name = 'piraté' where id = 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb'$$, 'A met à jour le profil de B sans erreur');
select lives_ok($$delete from public.profiles where id = 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb'$$, 'A supprime le profil de B sans erreur');
select lives_ok($$update public.projects set nom = 'piraté' where id = 'b1111111-1111-1111-1111-111111111111'$$, 'A met à jour le projet de B sans erreur');
select lives_ok($$delete from public.projects where id = 'b1111111-1111-1111-1111-111111111111'$$, 'A supprime le projet de B sans erreur');
select lives_ok($$update public.analyses set parametres = '{"q": "piraté"}' where id = 'b2222222-2222-2222-2222-222222222222'$$, 'A met à jour l''analyse de B sans erreur');
select lives_ok($$delete from public.analyses where id = 'b2222222-2222-2222-2222-222222222222'$$, 'A supprime l''analyse de B sans erreur');

-- Insertion au nom de B : refusée.
select throws_ok($$insert into public.projects (user_id, nom) values ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'x')$$, '42501', null, 'A ne crée pas de projet pour B');
select throws_ok($$insert into public.analyses (project_id, user_id) values ('b1111111-1111-1111-1111-111111111111', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb')$$, '42501', null, 'A ne crée pas d''analyse pour B');
select throws_ok($$insert into public.analyses (project_id, user_id) values ('b1111111-1111-1111-1111-111111111111', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa')$$, '23503', null, 'A ne rattache pas une analyse au projet de B');
select throws_ok($$insert into public.profiles (id) values (gen_random_uuid())$$, '42501', null, 'A ne crée pas de profil');

-- Écriture réservée au rôle service.
select throws_ok($$insert into public.subscriptions (user_id, stripe_customer_id, plan_code, statut) values ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'cus_x', 'test', 'active')$$, '42501', null, 'A n''insère pas de souscription');
select throws_ok($$update public.subscriptions set plan_code = 'test' where user_id = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'$$, '42501', null, 'A ne modifie pas sa souscription');
select throws_ok($$delete from public.subscriptions where user_id = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'$$, '42501', null, 'A ne supprime pas sa souscription');
select throws_ok($$update public.usage_quotas set consomme = 0 where user_id = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'$$, '42501', null, 'A ne modifie pas son quota');
select throws_ok($$insert into public.stripe_events (event_id) values ('evt_x')$$, '42501', null, 'A n''écrit pas dans stripe_events');
select throws_ok($$update public.plans set quota_mensuel_analyses = 999$$, '42501', null, 'A ne modifie pas les plans');

-- Témoin : A modifie ses propres lignes.
select lives_ok($$update public.projects set nom = 'projet A bis' where id = 'a1111111-1111-1111-1111-111111111111'$$, 'A met à jour son projet');

-- ===== Vérification des données de B (rôle postgres) =====
reset role;
select is((select display_name from public.profiles where id = 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb'), 'Bob', 'le profil de B est intact');
select is((select nom from public.projects where id = 'b1111111-1111-1111-1111-111111111111'), 'projet B', 'le projet de B est intact');
select is((select parametres from public.analyses where id = 'b2222222-2222-2222-2222-222222222222'), '{"q": "b"}'::jsonb, 'l''analyse de B est intacte');
select is((select consomme from public.usage_quotas where user_id = 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb'), 2, 'le quota de B est intact');
select is((select nom from public.projects where id = 'a1111111-1111-1111-1111-111111111111'), 'projet A bis', 'A a bien modifié son propre projet');

-- ===== Anonyme =====
set local role anon;
select is((select count(*) from public.profiles)::int, 0, 'anon ne lit pas profiles');
select is((select count(*) from public.projects)::int, 0, 'anon ne lit pas projects');
select is((select count(*) from public.analyses)::int, 0, 'anon ne lit pas analyses');
select is((select count(*) from public.subscriptions)::int, 0, 'anon ne lit pas subscriptions');
select is((select count(*) from public.usage_quotas)::int, 0, 'anon ne lit pas usage_quotas');
select is((select count(*) from public.plans)::int, 0, 'anon ne lit pas plans');
select throws_ok('select * from public.stripe_events', '42501', null, 'anon ne lit pas stripe_events');
select throws_ok($$insert into public.projects (user_id, nom) values ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'x')$$, '42501', null, 'anon ne crée pas de projet');

reset role;
select * from finish();
rollback;
