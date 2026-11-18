import "server-only";
import { z } from "zod";
import { query } from "@/lib/server/bigquery";
import { notionDetailInputSchema, notionSchema } from "./repository";
import articlesSql from "./sql/detail-articles.sql?raw";
import intentionsSql from "./sql/detail-intentions.sql?raw";
import notionSql from "./sql/detail-notion.sql?raw";
import requetesSql from "./sql/detail-requetes.sql?raw";
import serpSql from "./sql/detail-serp.sql?raw";
import volumesSql from "./sql/detail-volumes.sql?raw";

const id = z.string().min(1);
const articleSchema = z.object({
  article_id: z.string().regex(/^LEGIARTI[0-9]{12}$/),
  article_version_id: z.string().regex(/^LEGIARTI[0-9]{12}$/),
  numero: z.string(),
  etat: z.enum(["VIGUEUR", "MODIFIE", "ABROGE"]),
  date_debut: z.iso.date(),
  date_fin: z.iso.date().nullable(),
  en_vigueur: z.boolean(),
});
const requeteSchema = z.object({
  requete_id: id,
  texte: z.string(),
  score_rattachement: z.number().min(0).max(1),
});
const volumeSchema = z.object({
  mois: z.iso.date(),
  volume: z.number().nonnegative(),
});
const intentionSchema = z.object({
  intention_type: z
    .enum([
      "informationnelle",
      "transactionnelle",
      "navigationnelle",
      "commerciale",
    ])
    .nullable(),
  nombre_requetes: z.number().int().positive(),
});
const serpSchema = z.object({
  requete_id: id,
  texte: z.string(),
  date_resultat: z.iso.date(),
  position: z.number().int().min(1).max(10),
  domaine: z.string().nullable(),
  url: z.string().nullable(),
});

export type ArticleSource = z.infer<typeof articleSchema>;
export type RequeteAssociee = z.infer<typeof requeteSchema>;
export type VolumeMensuel = z.infer<typeof volumeSchema>;
export type Intention = z.infer<typeof intentionSchema>;
export type ResultatSerp = z.infer<typeof serpSchema>;

async function load<T>(
  sql: string,
  notionId: string,
  schema: z.ZodType<T>,
): Promise<T[]> {
  const notion_id = notionDetailInputSchema.parse(notionId);
  return query(sql, { notion_id }, schema);
}

export async function getScopedNotion(notionId: string) {
  const rows = await load(notionSql, notionId, notionSchema);
  if (rows.length > 1)
    throw new Error("Plusieurs notions portent le même identifiant.");
  return rows[0] ?? null;
}

export const getArticles = (notionId: string) =>
  load(articlesSql, notionId, articleSchema);
export const getRequetes = (notionId: string) =>
  load(requetesSql, notionId, requeteSchema);
export const getVolumes = (notionId: string) =>
  load(volumesSql, notionId, volumeSchema);
export const getIntentions = (notionId: string) =>
  load(intentionsSql, notionId, intentionSchema);
export const getSerp = (notionId: string) =>
  load(serpSql, notionId, serpSchema);
