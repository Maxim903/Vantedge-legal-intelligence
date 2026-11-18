import "server-only";
import { getNotionsVoisines } from "./repository";
import { NotionsGraph, type NotionGraphItem } from "./notions-graph";

export async function NotionsLieesSection({
  notionId,
  libelle,
  projectId,
}: {
  notionId: string;
  libelle: string;
  projectId: string;
}) {
  let notions: Awaited<ReturnType<typeof getNotionsVoisines>>;
  try {
    notions = await getNotionsVoisines(notionId);
  } catch (error) {
    console.error("Chargement des notions liées impossible", error);
    return (
      <div role="alert">
        <p>Impossible de charger les notions liées.</p>
        <a
          href={`/app/analyse/${encodeURIComponent(notionId)}?projet=${encodeURIComponent(projectId)}`}
          className="underline"
        >
          Réessayer
        </a>
      </div>
    );
  }
  if (!notions.length) return <p>Aucune notion liée disponible.</p>;
  const items = notions.map(
    ({ notion_id, libelle, nombre_articles_communs }) => ({
      notion_id,
      libelle,
      nombre_articles_communs,
    }),
  );
  return <NotionsLieesContent libelle={libelle} notions={items} />;
}

export function NotionsLieesContent({
  libelle,
  notions,
}: {
  libelle: string;
  notions: NotionGraphItem[];
}) {
  return (
    <div className="space-y-3">
      <p>Notions fondées sur des articles communs, tous codes confondus.</p>
      <NotionsGraph libelle={libelle} notions={notions} />
      <ul className="list-inside list-disc space-y-1">
        {notions.map((notion) => (
          <li key={notion.notion_id}>
            {notion.libelle} — {notion.nombre_articles_communs} article
            {notion.nombre_articles_communs > 1 ? "s" : ""} en commun
          </li>
        ))}
      </ul>
    </div>
  );
}
