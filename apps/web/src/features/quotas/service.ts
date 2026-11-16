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
export async function consumeQuota(userId: string): Promise<QuotaResult> {
  return quota(userId, true);
}
