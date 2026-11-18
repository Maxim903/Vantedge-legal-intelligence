create table public.plans (
  code text primary key,
  quota_mensuel_analyses integer not null check (quota_mensuel_analyses >= 0)
);

create table public.subscriptions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null unique references auth.users (id) on delete cascade,
  stripe_customer_id text not null unique,
  stripe_subscription_id text unique,
  plan_code text not null references public.plans (code),
  statut text not null check (statut in (
    'trialing', 'active', 'past_due', 'canceled',
    'incomplete', 'incomplete_expired', 'unpaid', 'paused'
  )),
  periode_fin timestamptz
);

create table public.usage_quotas (
  user_id uuid not null references auth.users (id) on delete cascade,
  -- Premier jour du mois concerné.
  periode date not null check (periode = date_trunc('month', periode)::date),
  consomme integer not null default 0 check (consomme >= 0),
  primary key (user_id, periode)
);

-- Journal des évènements Stripe déjà traités : l'unicité d'event_id garantit l'idempotence
-- du webhook (insert ... on conflict do nothing).
create table public.stripe_events (
  event_id text primary key,
  received_at timestamptz not null default now()
);

alter table public.plans enable row level security;
alter table public.subscriptions enable row level security;
alter table public.usage_quotas enable row level security;
alter table public.stripe_events enable row level security;

-- Lecture : l'utilisateur ne voit que ses lignes ; le catalogue des plans est lisible
-- par tout utilisateur connecté.
create policy "plans_select_authenticated" on public.plans for select to authenticated
  using (true);
create policy "subscriptions_select_own" on public.subscriptions for select to authenticated
  using ((select auth.uid()) = user_id);
create policy "usage_quotas_select_own" on public.usage_quotas for select to authenticated
  using ((select auth.uid()) = user_id);

-- Écriture : aucune policy pour anon/authenticated, donc refusée. Seul le rôle service
-- (qui contourne la RLS) écrit. Les révocations ci-dessous doublent cette protection.
-- stripe_events n'est lisible par aucun rôle client.
revoke insert, update, delete, truncate on public.plans from anon, authenticated;
revoke insert, update, delete, truncate on public.subscriptions from anon, authenticated;
revoke insert, update, delete, truncate on public.usage_quotas from anon, authenticated;
revoke all on public.stripe_events from anon, authenticated;
