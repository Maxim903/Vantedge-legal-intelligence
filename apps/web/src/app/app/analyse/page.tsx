import type { Metadata } from "next";
import Link from "next/link";
import { redirect } from "next/navigation";
import { Suspense } from "react";
import { Disclaimer } from "@/components/disclaimer";
import {
  analysisInputSchema,
  listAnalysis,
  listSituations,
  type AnalysisInput,
} from "@/features/analyse/repository";
import { createClient } from "@/lib/supabase/server";

export const metadata: Metadata = { title: "Analyse loi vs marché" };

type SearchParams = Record<string, string | string[] | undefined>;

function parseSearchParams(params: SearchParams) {
  const page = params.page ?? "1";
  if (typeof page !== "string" || !/^[1-9]\d*$/.test(page)) {
    return null;
  }
  const result = analysisInputSchema.safeParse({
    tri: params.tri ?? "notion",
    ordre: params.ordre ?? "asc",
    situation: params.situation ?? "",
    page: Number(page),
  });
  return result.success ? result.data : null;
}

function pageHref(input: AnalysisInput, page: number) {
  const params = new URLSearchParams({
    tri: input.tri,
    ordre: input.ordre,
    situation: input.situation,
    page: String(page),
  });
  return `/app/analyse?${params}`;
}

function Definition({ name, children }: { name: string; children: string }) {
  return (
    <details className="relative inline-block text-left">
      <summary
        aria-label={`Définition : ${name}`}
        className="ml-1 inline-block cursor-pointer rounded px-1 underline focus-visible:outline-2 focus-visible:outline-blue-600"
      >
        ⓘ
      </summary>
      <span className="absolute left-0 z-10 mt-1 w-64 rounded border border-zinc-400 bg-white p-3 text-sm font-normal text-zinc-900 shadow-lg dark:border-zinc-600 dark:bg-zinc-900 dark:text-white">
        {children}
      </span>
    </details>
  );
}

const numberFormat = new Intl.NumberFormat("fr-FR", {
  maximumFractionDigits: 2,
});

export async function Analyse({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  const supabase = await createClient();
  const {
    data: { user },
    error,
  } = await supabase.auth.getUser();
  if (error) {
    console.error("Authentification de l'analyse impossible", error);
    return (
      <div role="alert">
        <p>Impossible de vérifier votre session.</p>
        <Link className="underline" href="/app/analyse">
          Réessayer
        </Link>
      </div>
    );
  }
  if (!user) redirect("/connexion?redirect=%2Fapp%2Fanalyse");

  const input = parseSearchParams(await searchParams);
  if (!input) {
    return (
      <div role="alert">
        <p>Les paramètres de tri ou de pagination sont invalides.</p>
        <Link className="underline" href="/app/analyse">
          Réinitialiser
        </Link>
      </div>
    );
  }

  let result: Awaited<ReturnType<typeof listAnalysis>>;
  let situations: Awaited<ReturnType<typeof listSituations>>;
  try {
    [result, situations] = await Promise.all([
      listAnalysis(input),
      listSituations(),
    ]);
  } catch (error) {
    console.error("Chargement de l'analyse impossible", error);
    return (
      <div role="alert">
        <p>Impossible de charger l’analyse pour le moment.</p>
        <Link className="underline" href={pageHref(input, input.page)}>
          Réessayer
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <p>
        Périmètre : Code du travail, France et français. Les scores disponibles
        portent sur le code entier ; le calcul par livre n’est pas encore
        disponible.
      </p>
      <Disclaimer />
      <form
        action="/app/analyse"
        method="get"
        className="flex flex-wrap items-end gap-4"
      >
        <label className="grid gap-1">
          Situation de vie
          <select
            name="situation"
            defaultValue={input.situation}
            className="rounded border border-zinc-500 bg-transparent p-2 dark:border-zinc-400"
          >
            <option value="">Toutes les situations</option>
            {input.situation &&
              !situations.some((s) => s.situation_id === input.situation) && (
                <option value={input.situation}>Situation indisponible</option>
              )}
            {situations.map((s) => (
              <option key={s.situation_id} value={s.situation_id}>
                {s.libelle}
              </option>
            ))}
          </select>
        </label>
        <label className="grid gap-1">
          Trier par
          <select
            name="tri"
            defaultValue={input.tri}
            className="rounded border border-zinc-500 bg-transparent p-2 dark:border-zinc-400"
          >
            <option value="notion">Notion</option>
            <option value="demande">Demande D</option>
            <option value="saturation">Saturation S</option>
            <option value="importance">Importance I</option>
            <option value="ecart">Écart</option>
            <option value="criticite">Criticité</option>
          </select>
        </label>
        <label className="grid gap-1">
          Ordre
          <select
            name="ordre"
            defaultValue={input.ordre}
            className="rounded border border-zinc-500 bg-transparent p-2 dark:border-zinc-400"
          >
            <option value="asc">Croissant</option>
            <option value="desc">Décroissant</option>
          </select>
        </label>
        <button
          type="submit"
          className="rounded bg-blue-700 px-4 py-2 text-white hover:bg-blue-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600"
        >
          Appliquer
        </button>
      </form>

      {result.rows.length === 0 ? (
        <p>
          {input.page > 1
            ? "Aucun résultat sur cette page pour ce périmètre et ce filtre."
            : "Aucune analyse disponible pour ce périmètre et ce filtre."}
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-left text-sm">
            <caption className="mb-2 text-left">
              Scores disponibles, de 0 à 100
            </caption>
            <thead>
              <tr className="border-b border-zinc-400">
                <th scope="col" className="p-2">
                  Notion
                </th>
                <th scope="col" className="p-2">
                  Demande D
                  <Definition name="demande">
                    En v1 : rang percentile du volume mensuel moyen des
                    requêtes, pondéré par leur rattachement à la notion.
                  </Definition>
                </th>
                <th scope="col" className="p-2">
                  Saturation S
                  <Definition name="saturation">
                    En v1 : moyenne des percentiles de concurrence publicitaire
                    et de concentration des domaines dans la SERP.
                  </Definition>
                </th>
                <th scope="col" className="p-2">
                  Importance I
                  <Definition name="importance normative">
                    En v1 : moyenne des percentiles du nombre d’articles en
                    vigueur et du degré de la notion.
                  </Definition>
                </th>
                <th scope="col" className="p-2">
                  Écart
                  <Definition name="écart">
                    Demande D multipliée par (1 − S / 100) : une saturation
                    élevée réduit l’écart.
                  </Definition>
                </th>
                <th scope="col" className="p-2">
                  Criticité
                  <Definition name="criticité sémantique">
                    En v1 : moyenne de l’importance normative et de la part
                    pondérée des intentions commerciales ou transactionnelles.
                  </Definition>
                </th>
                <th scope="col" className="p-2">
                  Version et date
                </th>
              </tr>
            </thead>
            <tbody>
              {result.rows.map((row) => (
                <tr
                  key={row.gap_score_id}
                  className="border-b border-zinc-200 dark:border-zinc-700"
                >
                  <th scope="row" className="p-2 font-medium">
                    <Link
                      className="underline"
                      href={`/app/analyse/${encodeURIComponent(row.notion_id)}`}
                    >
                      {row.notion_libelle}
                    </Link>
                  </th>
                  <td className="p-2">
                    {numberFormat.format(row.indice_demande)}
                  </td>
                  <td className="p-2">
                    {numberFormat.format(row.indice_saturation)}
                  </td>
                  <td className="p-2">
                    {numberFormat.format(row.indice_importance_normative)}
                  </td>
                  <td className="p-2">
                    {numberFormat.format(row.score_ecart)}
                  </td>
                  <td className="p-2">
                    {numberFormat.format(row.criticite_semantique)}
                  </td>
                  <td className="p-2">
                    {row.version_score} ·{" "}
                    <time dateTime={row.date_calcul}>{row.date_calcul}</time>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <nav
        aria-label="Pagination des analyses"
        className="flex items-center gap-4"
      >
        {input.page > 1 && (
          <Link className="underline" href={pageHref(input, input.page - 1)}>
            Page précédente
          </Link>
        )}
        <span>Page {input.page}</span>
        {result.hasNextPage && (
          <Link className="underline" href={pageHref(input, input.page + 1)}>
            Page suivante
          </Link>
        )}
      </nav>
    </div>
  );
}

export default function Page({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Analyse loi vs marché</h1>
      <Suspense fallback={<p role="status">Chargement de l’analyse…</p>}>
        <Analyse searchParams={searchParams} />
      </Suspense>
    </div>
  );
}
