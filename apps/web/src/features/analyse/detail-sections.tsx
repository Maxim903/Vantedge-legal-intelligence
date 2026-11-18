import "server-only";
import type { ReactNode } from "react";
import {
  getArticles,
  getIntentions,
  getRequetes,
  getSerp,
  getVolumes,
} from "./detail-repository";
import { VolumeChart } from "./volume-chart";

type SectionProps = { notionId: string; projectId: string };

function SectionError({
  name,
  notionId,
  projectId,
}: SectionProps & { name: string }) {
  return (
    <div role="alert">
      <p>Impossible de charger {name}.</p>
      <a
        href={`/app/analyse/${encodeURIComponent(notionId)}?projet=${encodeURIComponent(projectId)}`}
        className="underline"
      >
        Réessayer
      </a>
    </div>
  );
}

async function load<T>(
  name: string,
  operation: () => Promise<T[]>,
): Promise<{ ok: true; rows: T[] } | { ok: false }> {
  try {
    return { ok: true, rows: await operation() };
  } catch (error) {
    console.error(`Chargement ${name} impossible`, error);
    return { ok: false };
  }
}

export function DetailSection({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <section className="space-y-3 rounded border border-zinc-200 p-4 dark:border-zinc-800">
      <h2 className="text-xl font-semibold">{title}</h2>
      {children}
    </section>
  );
}

export async function ArticlesSection({ notionId, projectId }: SectionProps) {
  const result = await load("des articles", () => getArticles(notionId));
  if (!result.ok)
    return (
      <SectionError
        name="les articles"
        notionId={notionId}
        projectId={projectId}
      />
    );
  if (!result.rows.length) return <p>Aucun article source disponible.</p>;
  return (
    <ul className="space-y-2">
      {result.rows.map((article) => (
        <li key={article.article_id}>
          <a
            className="underline"
            href={`https://www.legifrance.gouv.fr/codes/article_lc/${article.article_version_id}`}
            target="_blank"
            rel="noopener noreferrer"
          >
            Article {article.numero} sur Légifrance
          </a>
          {" — "}
          {article.etat} · depuis le {article.date_debut}
          {article.date_fin && ` jusqu’au ${article.date_fin}`}
          {!article.en_vigueur && " · aucune version actuellement en vigueur"}
        </li>
      ))}
    </ul>
  );
}

export async function RequetesSection({ notionId, projectId }: SectionProps) {
  const result = await load("des requêtes", () => getRequetes(notionId));
  if (!result.ok)
    return (
      <SectionError
        name="les requêtes"
        notionId={notionId}
        projectId={projectId}
      />
    );
  if (!result.rows.length) return <p>Aucune requête associée disponible.</p>;
  return (
    <ul className="space-y-1">
      {result.rows.map((item) => (
        <li key={item.requete_id}>
          {item.texte} — rattachement :{" "}
          {item.score_rattachement.toLocaleString("fr-FR", {
            maximumFractionDigits: 2,
          })}
        </li>
      ))}
    </ul>
  );
}

export async function VolumesSection({ notionId, projectId }: SectionProps) {
  const result = await load("des volumes mensuels", () => getVolumes(notionId));
  if (!result.ok)
    return (
      <SectionError
        name="les volumes mensuels"
        notionId={notionId}
        projectId={projectId}
      />
    );
  if (!result.rows.length) return <p>Aucun volume mensuel disponible.</p>;
  return <VolumeChart volumes={result.rows} />;
}

export async function IntentionsSection({ notionId, projectId }: SectionProps) {
  const result = await load("des intentions", () => getIntentions(notionId));
  if (!result.ok)
    return (
      <SectionError
        name="les intentions"
        notionId={notionId}
        projectId={projectId}
      />
    );
  if (!result.rows.length) return <p>Aucune intention disponible.</p>;
  return (
    <ul>
      {result.rows.map((item) => (
        <li key={item.intention_type ?? "inconnue"}>
          {item.intention_type ?? "Intention inconnue"} : {item.nombre_requetes}{" "}
          requête{item.nombre_requetes > 1 ? "s" : ""}
        </li>
      ))}
    </ul>
  );
}

function safeHttpUrl(value: string | null): string | null {
  if (!value) return null;
  try {
    const url = new URL(value);
    return (url.protocol === "https:" || url.protocol === "http:") &&
      !url.username &&
      !url.password
      ? url.href
      : null;
  } catch {
    return null;
  }
}

export async function SerpSection({ notionId, projectId }: SectionProps) {
  const result = await load("des résultats SERP", () => getSerp(notionId));
  if (!result.ok)
    return (
      <SectionError
        name="les résultats SERP"
        notionId={notionId}
        projectId={projectId}
      />
    );
  if (!result.rows.length) return <p>Aucun résultat SERP disponible.</p>;
  const groups = new Map<string, typeof result.rows>();
  for (const item of result.rows) {
    const group = groups.get(item.requete_id);
    if (group) group.push(item);
    else groups.set(item.requete_id, [item]);
  }
  return (
    <div className="space-y-4">
      {[...groups.entries()].map(([id, items]) => (
        <div key={id}>
          <h3 className="font-semibold">{items[0].texte}</h3>
          <p>Dernière SERP : {items[0].date_resultat}</p>
          <ol className="list-inside list-decimal">
            {items.map((item) => {
              const url = safeHttpUrl(item.url);
              return (
                <li key={item.position} value={item.position}>
                  {url ? (
                    <a
                      href={url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="underline"
                    >
                      {item.domaine || url}
                    </a>
                  ) : (
                    <span>
                      {item.domaine || "Domaine inconnu"} — lien indisponible
                    </span>
                  )}
                </li>
              );
            })}
          </ol>
        </div>
      ))}
    </div>
  );
}
