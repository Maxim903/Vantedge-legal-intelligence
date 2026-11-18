import "server-only";
import { z } from "zod";
import { createAdminClient } from "@/lib/server/supabase-admin";

const quotaResultSchema = z.discriminatedUnion("motif", [
  z.object({
    autorise: z.literal(true),
    motif: z.null(),
    periode: z.iso.date(),
    plan: z.string().min(1),
    limite: z.number().int().nonnegative(),
    consomme: z.number().int().nonnegative(),
  }),
  z.object({
    autorise: z.literal(false),
    motif: z.literal("limite_atteinte"),
    periode: z.iso.date(),
    plan: z.string().min(1),
    limite: z.number().int().nonnegative(),
    consomme: z.number().int().nonnegative(),
  }),
  z.object({
    autorise: z.literal(false),
    motif: z.literal("plan_absent"),
    periode: z.iso.date(),
    plan: z.null(),
    limite: z.null(),
    consomme: z.null(),
  }),
]);

export type QuotaResult = z.infer<typeof quotaResultSchema>;

const analysisConsumptionSchema = z.discriminatedUnion("statut", [
  z.object({ statut: z.literal("existante") }),
  z.object({
    statut: z.literal("cree"),
    quota: quotaResultSchema.refine((result) => result.autorise),
  }),
  z.object({
    statut: z.literal("refusee"),
    quota: quotaResultSchema.refine((result) => !result.autorise),
  }),
]);

export type AnalysisConsumption = z.infer<typeof analysisConsumptionSchema>;
type AnalysisRequest = { projectId: string; notionId: string };

async function quota(userId: string, consume: boolean): Promise<QuotaResult> {
  const parsedUserId = z.uuid().parse(userId);
  const { data, error } = await createAdminClient().rpc("quota_mensuel", {
    p_user_id: parsedUserId,
    p_consume: consume,
  });
  if (error) {
    throw new Error("Impossible de vérifier le quota.", { cause: error });
  }
  return quotaResultSchema.parse(data);
}

/** Lecture indicative : seule consumeQuota réserve effectivement une unité. */
export async function checkQuota(userId: string): Promise<QuotaResult> {
  return quota(userId, false);
}

/** Réserve une unité si la limite n'est pas atteinte, en une transaction SQL. */
export function consumeQuota(userId: string): Promise<QuotaResult>;
export function consumeQuota(
  userId: string,
  analysis: AnalysisRequest,
): Promise<AnalysisConsumption>;
export async function consumeQuota(
  userId: string,
  analysis?: AnalysisRequest,
): Promise<QuotaResult | AnalysisConsumption> {
  if (!analysis) return quota(userId, true);
  const parsedUserId = z.uuid().parse(userId);
  const projectId = z.uuid().parse(analysis.projectId);
  const notionId = z.string().trim().min(1).parse(analysis.notionId);
  const { data, error } = await createAdminClient().rpc("ouvrir_analyse", {
    p_user_id: parsedUserId,
    p_project_id: projectId,
    p_notion_id: notionId,
  });
  if (error) {
    throw new Error("Impossible d'ouvrir l'analyse.", { cause: error });
  }
  return analysisConsumptionSchema.parse(data);
}
