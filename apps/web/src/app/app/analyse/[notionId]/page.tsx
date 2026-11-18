import type { Metadata } from "next";
import Link from "next/link";
import { notFound, redirect } from "next/navigation";
import { Suspense, type ReactNode } from "react";
import { z } from "zod";
import { Disclaimer } from "@/components/disclaimer";
import { getScopedNotion } from "@/features/analyse/detail-repository";
import {
  ArticlesSection,
  DetailSection,
  IntentionsSection,
  RequetesSection,
  SerpSection,
  VolumesSection,
} from "@/features/analyse/detail-sections";
import { notionDetailInputSchema } from "@/features/analyse/repository";
import { OpenAnalysisForm } from "@/features/analyse/open-form";
import { hasSavedAnalysis } from "@/features/analyse/saved-analysis";
import { NotionsLieesSection } from "@/features/graphe/notions-liees-section";
import { createClient } from "@/lib/supabase/server";

export const metadata: Metadata = { title: "Détail d’une notion" };
export const instant = false;

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <DetailSection title={title}>
      <Suspense fallback={<p role="status">Chargement : {title}…</p>}>
        {children}
      </Suspense>
    </DetailSection>
  );
}

export async function NotionDetail({
  notionId,
  projectId,
}: {
  notionId: string;
  projectId?: string | string[];
}) {
  const supabase = await createClient();
  const {
    data: { user },
    error,
  } = await supabase.auth.getUser();
  if (error) {
    console.error("Authentification du détail impossible", error);
    return (
      <div role="alert">
        <p>Impossible de vérifier votre session.</p>
        <a
          href={`/app/analyse/${encodeURIComponent(notionId)}`}
          className="underline"
        >
          Réessayer
        </a>
      </div>
    );
  }
  if (!user) {
    const destination = `/app/analyse/${encodeURIComponent(notionId)}${typeof projectId === "string" ? `?projet=${encodeURIComponent(projectId)}` : ""}`;
    redirect(`/connexion?redirect=${encodeURIComponent(destination)}`);
  }
  const parsed = notionDetailInputSchema.safeParse(notionId);
  if (!parsed.success) notFound();

  const parsedProject =
    projectId === undefined ? null : z.uuid().safeParse(projectId);
  if (parsedProject && !parsedProject.success) {
    return (
      <div role="alert">
        Projet invalide.{" "}
        <Link
          href={`/app/analyse/${encodeURIComponent(parsed.data)}`}
          className="underline"
        >
          Choisir un projet
        </Link>
      </div>
    );
  }
  const selectedProject = parsedProject?.success
    ? parsedProject.data
    : undefined;
  const retryUrl = `/app/analyse/${encodeURIComponent(parsed.data)}${selectedProject ? `?projet=${encodeURIComponent(selectedProject)}` : ""}`;
  let saved: boolean;
  try {
    saved = selectedProject
      ? await hasSavedAnalysis(supabase, user.id, selectedProject, parsed.data)
      : false;
  } catch (error) {
    console.error("Vérification de l'analyse impossible", error);
    return (
      <div role="alert">
        <p>Impossible de vérifier l’analyse enregistrée.</p>
        <a
          href={`/app/analyse/${encodeURIComponent(parsed.data)}`}
          className="underline"
        >
          Réessayer
        </a>
      </div>
    );
  }

  if (!saved || !selectedProject) {
    const { data: projects, error: projectsError } = await supabase
      .from("projects")
      .select("id, nom")
      .eq("user_id", user.id)
      .order("nom");
    if (projectsError) {
      console.error("Chargement des projets impossible", projectsError);
      return (
        <div role="alert">
          <p>Impossible de charger vos projets.</p>
          <a
            href={`/app/analyse/${encodeURIComponent(parsed.data)}`}
            className="underline"
          >
            Réessayer
          </a>
        </div>
      );
    }
    return (
      <div className="space-y-4">
        <Link href="/app/analyse" className="underline">
          Retour à l’analyse
        </Link>
        <h1 className="text-2xl font-semibold">Ouvrir une analyse</h1>
        {projects.length === 0 ? (
          <p>
            Créez d’abord un projet dans{" "}
            <Link href="/app/compte" className="underline">
              Mon compte
            </Link>
            .
          </p>
        ) : (
          <OpenAnalysisForm
            notionId={parsed.data}
            projects={projects}
            selectedProject={selectedProject}
          />
        )}
      </div>
    );
  }

  let notion: Awaited<ReturnType<typeof getScopedNotion>>;
  try {
    notion = await getScopedNotion(parsed.data);
  } catch (error) {
    console.error("Chargement de la notion impossible", error);
    return (
      <div role="alert">
        <p>Impossible de charger la notion.</p>
        <a href={retryUrl} className="underline">
          Réessayer
        </a>
      </div>
    );
  }
  if (!notion) notFound();

  const notionsLiees = await NotionsLieesSection({
    notionId: notion.notion_id,
    libelle: notion.libelle,
    projectId: selectedProject,
  });

  return (
    <div className="space-y-6">
      <Link href="/app/analyse" className="underline">
        Retour à l’analyse
      </Link>
      <h1 className="text-2xl font-semibold">{notion.libelle}</h1>
      {notion.definition_courte && <p>{notion.definition_courte}</p>}
      <p>Code du travail entier · France · français</p>
      <Disclaimer />
      <Section title="Articles sources">
        <ArticlesSection
          notionId={notion.notion_id}
          projectId={selectedProject}
        />
      </Section>
      <DetailSection title="Notions liées">{notionsLiees}</DetailSection>
      <Section title="Requêtes associées">
        <RequetesSection
          notionId={notion.notion_id}
          projectId={selectedProject}
        />
      </Section>
      <Section title="Volume mensuel">
        <VolumesSection
          notionId={notion.notion_id}
          projectId={selectedProject}
        />
      </Section>
      <Section title="Intentions">
        <IntentionsSection
          notionId={notion.notion_id}
          projectId={selectedProject}
        />
      </Section>
      <Section title="Top SERP">
        <SerpSection notionId={notion.notion_id} projectId={selectedProject} />
      </Section>
    </div>
  );
}

export default async function Page({
  params,
  searchParams,
}: {
  params: Promise<{ notionId: string }>;
  searchParams: Promise<{ projet?: string | string[] }>;
}) {
  const [{ notionId }, { projet }] = await Promise.all([params, searchParams]);
  return NotionDetail({ notionId, projectId: projet });
}
