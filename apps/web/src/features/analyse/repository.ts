import "server-only";
import { z } from "zod";
import { query } from "@/lib/server/bigquery";
import gapScoresSql from "./sql/gap-scores.sql?raw";
import listAnalysisSql from "./sql/list-analysis.sql?raw";
import listNotionsSql from "./sql/list-notions.sql?raw";
import listSituationsSql from "./sql/list-situations.sql?raw";
import notionDetailSql from "./sql/notion-detail.sql?raw";

const PAGE_SIZE = 20;
const identifierSchema = z.string().trim().min(1);
const scoreSchema = z.number().min(0).max(100);

export const notionSchema = z.object({
  notion_id: identifierSchema,
  libelle: z.string(),
  definition_courte: z.string().nullable(),
  score_confiance: z.number().min(0).max(1),
});

export const listNotionsInputSchema = z.object({
  tri: z.enum(["asc", "desc"]),
  filtre: z.string().trim(),
  page: z
    .number()
    .int()
    .min(1)
    .max(Math.floor(Number.MAX_SAFE_INTEGER / PAGE_SIZE)),
});

export const notionDetailInputSchema = identifierSchema;

export const gapScoresInputSchema = z.array(identifierSchema);
export const gapScoreSchema = z.object({
  gap_score_id: identifierSchema,
  notion_id: identifierSchema,
  code_id: identifierSchema,
  livre_id: identifierSchema.nullable(),
  pays_langue_id: identifierSchema,
  date_calcul: z.iso.date(),
  version_score: identifierSchema,
  indice_demande: scoreSchema,
  indice_saturation: scoreSchema,
  indice_importance_normative: scoreSchema,
  score_ecart: scoreSchema,
  criticite_semantique: scoreSchema,
  taille_cohorte: z.number().int().positive(),
});

export type Notion = z.infer<typeof notionSchema>;
export type GapScore = z.infer<typeof gapScoreSchema>;
export type ListNotionsInput = z.input<typeof listNotionsInputSchema>;

export const analysisInputSchema = z.object({
  tri: z.enum([
    "notion",
    "demande",
    "saturation",
    "importance",
    "ecart",
    "criticite",
  ]),
  ordre: z.enum(["asc", "desc"]),
  situation: z.string().trim(),
  page: listNotionsInputSchema.shape.page,
});
const analysisRowSchema = gapScoreSchema.extend({
  notion_libelle: z.string(),
});
const situationSchema = z.object({
  situation_id: identifierSchema,
  libelle: z.string(),
});

export type AnalysisInput = z.infer<typeof analysisInputSchema>;
export type AnalysisRow = z.infer<typeof analysisRowSchema>;
export type Situation = z.infer<typeof situationSchema>;

export async function listAnalysis(input: AnalysisInput): Promise<{
  rows: AnalysisRow[];
  hasNextPage: boolean;
}> {
  const { tri, ordre, situation, page } = analysisInputSchema.parse(input);
  const rows = await query(
    listAnalysisSql,
    {
      tri,
      ordre,
      situation,
      limite: PAGE_SIZE + 1,
      offset: (page - 1) * PAGE_SIZE,
    },
    analysisRowSchema,
  );
  return {
    rows: rows.slice(0, PAGE_SIZE),
    hasNextPage: rows.length > PAGE_SIZE,
  };
}

export async function listSituations(): Promise<Situation[]> {
  return query(listSituationsSql, {}, situationSchema);
}

export async function listNotions(input: ListNotionsInput): Promise<Notion[]> {
  const { tri, filtre, page } = listNotionsInputSchema.parse(input);
  return query(
    listNotionsSql,
    { tri, filtre, limite: PAGE_SIZE, offset: (page - 1) * PAGE_SIZE },
    notionSchema,
  );
}

export async function getNotionDetail(
  notionId: string,
): Promise<Notion | null> {
  const notion_id = notionDetailInputSchema.parse(notionId);
  const notions = await query(notionDetailSql, { notion_id }, notionSchema);
  if (notions.length > 1) {
    throw new Error("Plusieurs notions portent le même identifiant.");
  }
  return notions[0] ?? null;
}

export async function getGapScores(notionIds: string[]): Promise<GapScore[]> {
  const notion_ids = gapScoresInputSchema.parse(notionIds);
  if (notion_ids.length === 0) {
    return [];
  }
  return query(gapScoresSql, { notion_ids }, gapScoreSchema);
}
