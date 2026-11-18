create table public.profiles (
  id uuid primary key references auth.users (id) on delete cascade,
  display_name text,
  created_at timestamptz not null default now()
);

comment on table public.profiles is 'Profil applicatif, un par utilisateur auth.users.';

alter table public.profiles enable row level security;

-- Chaque utilisateur lit et modifie uniquement son propre profil.
-- Pas de policy d'insertion ni de suppression : le profil est créé par le trigger
-- et supprimé en cascade avec l'utilisateur.
create policy "profiles_select_own"
  on public.profiles for select
  to authenticated
  using ((select auth.uid()) = id);

create policy "profiles_update_own"
  on public.profiles for update
  to authenticated
  using ((select auth.uid()) = id)
  with check ((select auth.uid()) = id);

-- security definer : le trigger s'exécute avec les droits du propriétaire, car le rôle
-- qui inscrit l'utilisateur n'a pas accès à public.profiles.
create function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  insert into public.profiles (id, display_name)
  values (
    new.id,
    nullif(trim(coalesce(new.raw_user_meta_data ->> 'display_name', '')), '')
  );
  return new;
end;
$$;

revoke execute on function public.handle_new_user() from public, anon, authenticated;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();
