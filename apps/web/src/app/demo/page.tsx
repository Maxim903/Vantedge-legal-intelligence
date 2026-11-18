import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = { title: "Démo locale" };

const cards = [
  {
    name: "Supabase",
    detail: "Compte et projets de démonstration",
    behavior: "Sessions et données simulées",
  },
  {
    name: "BigQuery",
    detail: "Jeu synthétique marts",
    behavior: "3 notions et scores d'exemple",
  },
  {
    name: "Neo4j",
    detail: "Liens entre notions",
    behavior: "Relations d'exemple, graphe non connecté",
  },
  {
    name: "Cloud Storage",
    detail: "Bucket d'archives",
    behavior: "Aucun bucket contacté",
  },
];

export default function DemoPage() {
  return (
    <main className="mx-auto w-full max-w-5xl flex-1 space-y-8 px-4 py-10">
      <header className="space-y-3">
        <p className="text-sm font-semibold uppercase tracking-wide text-blue-700 dark:text-blue-300">
          Aperçu local · données fictives
        </p>
        <h1 className="text-3xl font-semibold">Explorer Vantedge</h1>
        <p className="max-w-3xl text-zinc-600 dark:text-zinc-400">
          Parcourez les écrans d&apos;analyse sans vous connecter à un service
          externe. Les exemples ci-dessous n&apos;ont été lus ni écrits dans aucune
          base ni aucun bucket.
        </p>
      </header>

      <section aria-labelledby="sources-title" className="space-y-4">
        <h2 id="sources-title" className="text-xl font-semibold">
          Comportement des sources — simulation
        </h2>
        <div className="grid gap-4 sm:grid-cols-2">
          {cards.map((card) => (
            <article
              key={card.name}
              className="space-y-2 rounded border border-zinc-300 p-4 dark:border-zinc-700"
            >
              <h3 className="font-semibold">{card.name}</h3>
              <p>{card.detail}</p>
              <p className="text-sm text-zinc-600 dark:text-zinc-400">
                {card.behavior}
              </p>
            </article>
          ))}
        </div>
        <p className="text-sm">
          Flux illustré : BigQuery fournit des scores pré-calculés ; le graphe
          relie les notions ; l&apos;interface affiche les résultats. Le traitement
          du corpus et les lectures/écritures GCS ne sont pas exécutés dans cette
          démo.
        </p>
      </section>

      <Link
        href="/demo/analyse"
        className="inline-block rounded bg-blue-700 px-5 py-3 font-medium text-white hover:bg-blue-800"
      >
        Voir les analyses
      </Link>
    </main>
  );
}
