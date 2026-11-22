import type { Metadata } from "next";
import Link from "next/link";
import { demoNotions, demoSituations } from "@/features/demo/data";

export const metadata: Metadata = { title: "Analyses — Démo locale" };
export const instant = false;

type Props = {
  searchParams: Promise<{ situation?: string; tri?: string; ordre?: string }>;
};

const labels = {
  demande: "Demande D",
  saturation: "Saturation S",
  importance: "Importance I",
  ecart: "Écart",
  criticite: "Criticité",
} as const;

type SortKey = keyof typeof labels;
const sortKeys = Object.keys(labels);
const numberFormat = new Intl.NumberFormat("fr-FR", {
  maximumFractionDigits: 2,
});

function isSortKey(value: string | undefined): value is SortKey {
  return value !== undefined && sortKeys.includes(value);
}

export default async function DemoAnalysisPage({ searchParams }: Props) {
  const params = await searchParams;
  const situation = demoSituations.includes(params.situation ?? "")
    ? params.situation
    : "";
  const sort = isSortKey(params.tri) ? params.tri : "ecart";
  const descending = params.ordre !== "asc";
  const rows = demoNotions
    .filter((notion) => !situation || notion.situation === situation)
    .toSorted((a, b) => {
      const difference = a[sort] - b[sort];
      return (descending ? -1 : 1) * (difference || a.libelle.localeCompare(b.libelle));
    });

  return (
    <main className="mx-auto w-full max-w-6xl flex-1 space-y-6 px-4 py-10">
      <Link href="/demo" className="underline">
        Retour à la démo
      </Link>
      <header className="space-y-2">
        <p className="text-sm font-semibold uppercase tracking-wide text-blue-700 dark:text-blue-300">
          Données synthétiques · aucune connexion cloud
        </p>
        <h1 className="text-3xl font-semibold">Analyse loi vs marché</h1>
        <p>
          Exemple France/fr · Scores fictifs version demo-v1 · calcul
          2026-10-01. Cet outil ne fournit aucun conseil juridique.
        </p>
      </header>

      <form action="/demo/analyse" method="get" className="flex flex-wrap gap-4">
        <label className="grid gap-1">
          Situation de vie
          <select
            name="situation"
            defaultValue={situation}
            className="rounded border border-zinc-500 bg-transparent p-2"
          >
            <option value="">Toutes</option>
            {demoSituations.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </label>
        <label className="grid gap-1">
          Trier par
          <select
            name="tri"
            defaultValue={sort}
            className="rounded border border-zinc-500 bg-transparent p-2"
          >
            {Object.entries(labels).map(([key, label]) => (
              <option key={key} value={key}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <label className="grid gap-1">
          Ordre
          <select
            name="ordre"
            defaultValue={descending ? "desc" : "asc"}
            className="rounded border border-zinc-500 bg-transparent p-2"
          >
            <option value="desc">Décroissant</option>
            <option value="asc">Croissant</option>
          </select>
        </label>
        <button
          type="submit"
          className="self-end rounded bg-blue-700 px-4 py-2 text-white hover:bg-blue-800"
        >
          Appliquer
        </button>
      </form>

      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-left text-sm">
          <caption className="mb-2 text-left">
            Scores simulés (0 à 100), triés par {labels[sort].toLowerCase()}
          </caption>
          <thead>
            <tr className="border-b border-zinc-400">
              <th scope="col" className="p-2">Notion</th>
              <th scope="col" className="p-2">Demande D</th>
              <th scope="col" className="p-2">Saturation S</th>
              <th scope="col" className="p-2">Importance I</th>
              <th scope="col" className="p-2">Écart</th>
              <th scope="col" className="p-2">Criticité</th>
              <th scope="col" className="p-2">Version · date</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((notion) => (
              <tr
                key={notion.id}
                className="border-b border-zinc-200 dark:border-zinc-700"
              >
                <th scope="row" className="p-2 font-medium">
                  <Link href={`/demo/analyse/${notion.id}`} className="underline">
                    {notion.libelle}
                  </Link>
                  <span className="block font-normal text-zinc-600 dark:text-zinc-400">
                    {notion.situation}
                  </span>
                </th>
                <td className="p-2">{numberFormat.format(notion.demande)}</td>
                <td className="p-2">{numberFormat.format(notion.saturation)}</td>
                <td className="p-2">{numberFormat.format(notion.importance)}</td>
                <td className="p-2 font-semibold">{numberFormat.format(notion.ecart)}</td>
                <td className="p-2">{numberFormat.format(notion.criticite)}</td>
                <td className="p-2">
                  {notion.versionScore} · <time>{notion.dateCalcul}</time>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {rows.length === 0 && <p>Aucune notion pour ce filtre.</p>}
      <p className="text-sm text-zinc-600 dark:text-zinc-400">
        Les filtres et tris fonctionnent sur le jeu synthétique local ; ils ne
        déclenchent aucune requête BigQuery.
      </p>
    </main>
  );
}
