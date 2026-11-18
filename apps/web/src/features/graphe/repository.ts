import "server-only";
import neo4j, { type Integer, type Path } from "neo4j-driver";
import { z } from "zod";
import { query } from "@/lib/server/neo4j";
import cheminsCypher from "../../../../../graph/queries/chemins_notion_articles.cypher?raw";
import clustersCypher from "../../../../../graph/queries/clusters_situations.cypher?raw";
import connecteesCypher from "../../../../../graph/queries/notions_connectees.cypher?raw";
import voisinesCypher from "../../../../../graph/queries/notions_voisines.cypher?raw";

const identifierSchema = z.string().trim().min(1);
const integerSchema = z
  .custom<Integer>(neo4j.isInt)
  .transform((value, context) => {
    if (!value.inSafeRange()) {
      context.addIssue({
        code: "custom",
        message: "Entier Neo4j hors plage sûre.",
      });
      return z.NEVER;
    }
    return value.toNumber();
  })
  .pipe(z.number().int().nonnegative());

const articleSchema = z.object({
  article_id: identifierSchema,
  numero: z.string().nullable(),
});
const notionSchema = z.object({
  notion_id: identifierSchema,
  libelle: z.string(),
});
const voisineSchema = notionSchema.extend({
  nombre_articles_communs: integerSchema,
  articles_communs: z.array(articleSchema),
});
const connecteeSchema = notionSchema.extend({ degre: integerSchema });
const clusterSchema = z.object({
  situation_id: identifierSchema,
  libelle: z.string(),
  nombre_notions: integerSchema,
  notions: z.array(notionSchema),
});
const relationSchema = z.enum([
  "SE_FONDE_SUR",
  "RENVOIE_A",
  "MODIFIE",
  "ABROGE",
]);
const pathSchema = z.custom<Path>(neo4j.isPath).transform((path) => {
  if (!path.start.labels.includes("Notion") || path.segments.length === 0) {
    throw new Error("Chemin Neo4j invalide : notion ou article source absent.");
  }
  const { notion_id } = z
    .object({ notion_id: identifierSchema })
    .parse(path.start.properties);
  const articles = path.segments.map((segment) => {
    if (!segment.end.labels.includes("Article")) {
      throw new Error("Chemin Neo4j invalide : un nœud n'est pas un article.");
    }
    return articleSchema.parse(segment.end.properties);
  });
  const relations = z
    .array(relationSchema)
    .parse(path.segments.map((segment) => segment.relationship.type));
  if (
    relations[0] !== "SE_FONDE_SUR" ||
    relations.slice(1).includes("SE_FONDE_SUR")
  ) {
    throw new Error("Chemin Neo4j invalide : relations inattendues.");
  }
  return { notion_id, articles, relations };
});
const cheminSchema = z.object({
  article_id: identifierSchema,
  numero: z.string().nullable(),
  nombre_liens_normatifs: integerSchema,
  chemin: pathSchema,
});

export type NotionVoisine = z.output<typeof voisineSchema>;
export type NotionConnectee = z.output<typeof connecteeSchema>;
export type ClusterSituation = z.output<typeof clusterSchema>;
export type CheminNotionArticle = z.output<typeof cheminSchema>;

export async function getNotionsVoisines(
  notionId: string,
): Promise<NotionVoisine[]> {
  return query(
    voisinesCypher,
    { notion_id: identifierSchema.parse(notionId) },
    voisineSchema,
  );
}

export async function getNotionsConnectees(
  limite: number,
): Promise<NotionConnectee[]> {
  const count = z.number().int().nonnegative().safe().parse(limite);
  return query(connecteesCypher, { limite: neo4j.int(count) }, connecteeSchema);
}

export async function getCheminsNotionArticles(
  notionId: string,
): Promise<CheminNotionArticle[]> {
  return query(
    cheminsCypher,
    { notion_id: identifierSchema.parse(notionId) },
    cheminSchema,
  );
}

export async function getClustersSituations(): Promise<ClusterSituation[]> {
  return query(clustersCypher, {}, clusterSchema);
}
