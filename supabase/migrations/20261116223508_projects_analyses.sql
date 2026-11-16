create table public.projects (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null default auth.uid() references auth.users (id) on delete cascade,
  nom text not null check (length(trim(nom)) > 0),
  -- Cible de la clé étrangère composite de analyses : garantit qu'une analyse
  -- appartient au même utilisateur que son projet.
  unique (id, user_id)
);

create table public.analyses (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null,
  user_id uuid not null default auth.uid() references auth.users (id) on delete cascade,
  parametres jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  foreign key (project_id, user_id)
    references public.projects (id, user_id) on delete cascade
);

create index projects_user_id_idx on public.projects (user_id);
create index analyses_user_id_idx on public.analyses (user_id);
create index analyses_project_id_idx on public.analyses (project_id);

alter table public.projects enable row level security;
alter table public.analyses enable row level security;

-- Chaque utilisateur gère uniquement ses propres lignes.
create policy "projects_select_own" on public.projects for select to authenticated
  using ((select auth.uid()) = user_id);
create policy "projects_insert_own" on public.projects for insert to authenticated
  with check ((select auth.uid()) = user_id);
create policy "projects_update_own" on public.projects for update to authenticated
  using ((select auth.uid()) = user_id)
  with check ((select auth.uid()) = user_id);
create policy "projects_delete_own" on public.projects for delete to authenticated
  using ((select auth.uid()) = user_id);

create policy "analyses_select_own" on public.analyses for select to authenticated
  using ((select auth.uid()) = user_id);
create policy "analyses_insert_own" on public.analyses for insert to authenticated
  with check ((select auth.uid()) = user_id);
create policy "analyses_update_own" on public.analyses for update to authenticated
  using ((select auth.uid()) = user_id)
  with check ((select auth.uid()) = user_id);
create policy "analyses_delete_own" on public.analyses for delete to authenticated
  using ((select auth.uid()) = user_id);
