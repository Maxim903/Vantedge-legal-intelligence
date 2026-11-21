import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { getDemoNotion } from "@/features/demo/data";

export const metadata: Metadata = { title: "Détail — Démo locale" };
export const instant = false;

export default async function DemoNotionPage({
  params,
}: {
  params: Promise<{ notionId: string }>;
}) {
  const { notionId } = await params;
  const notion = getDemoNotion(notionId);
  if (!notion) notFound();

  return (
    <main className="mx-auto w-full max-w-5xl flex-1 space-y-6 px-4 py-10">
      <Link href="/demo/analyse" className="underline">
        Retour aux analyses
      </Link>
      <header className="space-y-2">
        <p className="text-sm font-semibold uppercase tracking-wide text-blue-700 dark:text-blue-300">
          Exemple synthétique · aucune connexion cloud
        </p>
        <h1 className="text-3xl font-semibold">{notion.libelle}</h1>
        <p>{notion.definition}</p>
        <p>{notion.situation} · Code du travail · France/fr</p>
        <p>Score {notion.ecart}/100 · {notion.versionScore} · {notion.dateCalcul}</p>
        <p>Cet outil ne fournit aucun conseil juridique.</p>
      </header>

      <section className="space-y-3 rounded border border-zinc-300 p-4 dark:border-zinc-700">
        <h2 className="text-xl font-semibold">Articles sources (exemples)</h2>
        <ul className="list-inside list-disc">
          {notion.articles.map((article) => (
            <li key={article.numero}>
              Article {article.numero} — {article.titre} (donnée fictive)
            </li>
          ))}
        </ul>
      </section>

      <section className="space-y-3 rounded border border-zinc-300 p-4 dark:border-zinc-700">
        <h2 className="text-xl font-semibold">Requêtes et rattachements simulés</h2>
        <ul className="list-inside list-disc">
          {notion.requetes.map((item) => (
            <li key={item.texte}>
              {item.texte} — score {item.rattachement.toLocaleString("fr-FR")}
            </li>
          ))}
        </ul>
      </section>

      <section className="space-y-3 rounded border border-zinc-300 p-4 dark:border-zinc-700">
        <h2 className="text-xl font-semibold">Volumes mensuels (exemple)</h2>
        <div className="grid gap-2 sm:grid-cols-2">
          {notion.volumes.map((item) => (
            <div key={item.mois} className="flex items-center gap-3">
              <span className="w-12">{item.mois}</span>
              <div
                className="h-5 rounded bg-blue-600"
                style={{ width: `${Math.max(8, (item.volume / 6000) * 100)}%` }}
                aria-label={`${item.volume} recherches`}
              />
              <span>{item.volume.toLocaleString("fr-FR")}</span>
            </div>
          ))}
        </div>
      </section>

      <section className="space-y-3 rounded border border-zinc-300 p-4 dark:border-zinc-700">
        <h2 className="text-xl font-semibold">Résultats SERP simulés</h2>
        <ol className="list-inside list-decimal">
          {notion.serp.map((item) => (
            <li key={item.position}>
              Position {item.position} — {item.domaine} (URL illustrative :{" "}
              {item.url})
            </li>
          ))}
        </ol>
      </section>

      <section className="space-y-3 rounded border border-zinc-300 p-4 dark:border-zinc-700">
        <h2 className="text-xl font-semibold">Notions liées (liens Neo4j simulés)</h2>
        <ul className="list-inside list-disc">
          {notion.notionsLiees.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </section>

      <p className="text-sm text-zinc-600 dark:text-zinc-400">
        Cette page n&apos;interroge ni BigQuery ni Neo4j. Les articles, métriques,
        requêtes et liens sont des exemples et ne constituent pas des résultats
        juridiques ou de marché réels.
      </p>
    </main>
  );
}
