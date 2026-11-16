import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { Suspense, type ReactNode } from "react";
import { createClient } from "@/lib/supabase/server";
import {
  HistorySection,
  ProfileSection,
  ProjectsSection,
  QuotaSection,
  SubscriptionSection,
} from "@/features/account/sections";

export const metadata: Metadata = { title: "Mon compte" };

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="rounded border border-zinc-200 p-4 dark:border-zinc-800">
      <h2 className="mb-3 text-xl font-semibold">{title}</h2>
      <Suspense fallback={<p role="status">Chargement : {title}…</p>}>
        {children}
      </Suspense>
    </section>
  );
}

async function Account() {
  const supabase = await createClient();
  const {
    data: { user },
    error,
  } = await supabase.auth.getUser();
  if (error) {
    console.error("Authentification du compte impossible", error);
    return (
      <div role="alert">
        <p>Impossible de charger votre compte.</p>
        <a href="/app/compte" className="underline">
          Réessayer
        </a>
      </div>
    );
  }
  if (!user) redirect("/connexion?redirect=%2Fapp%2Fcompte");
  return (
    <div className="grid gap-4 md:grid-cols-2">
      <Section title="Profil">
        <ProfileSection userId={user.id} email={user.email} />
      </Section>
      <Section title="Abonnement">
        <SubscriptionSection userId={user.id} />
      </Section>
      <Section title="Quotas">
        <QuotaSection userId={user.id} />
      </Section>
      <Section title="Projets">
        <ProjectsSection userId={user.id} />
      </Section>
      <Section title="Historique des analyses">
        <HistorySection userId={user.id} />
      </Section>
    </div>
  );
}

export default function Page() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Mon compte</h1>
      <Suspense fallback={<p role="status">Chargement du compte…</p>}>
        <Account />
      </Suspense>
    </div>
  );
}
