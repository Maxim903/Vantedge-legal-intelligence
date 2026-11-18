"use server";

import { redirect } from "next/navigation";
import { z } from "zod";
import { checkQuota, consumeQuota } from "@/features/quotas/service";
import { createClient } from "@/lib/supabase/server";
import { getScopedNotion } from "./detail-repository";
import { notionDetailInputSchema } from "./repository";
import { hasSavedAnalysis } from "./saved-analysis";

export type OpenAnalysisState = { error?: string; upgrade?: boolean };

export async function openAnalysis(
  _state: OpenAnalysisState,
  form: FormData,
): Promise<OpenAnalysisState> {
  const projectId = z.uuid().safeParse(form.get("project_id"));
  const notionId = notionDetailInputSchema.safeParse(form.get("notion_id"));
  if (!projectId.success || !notionId.success) {
    return { error: "Projet ou notion invalide." };
  }
  const destination = `/app/analyse/${encodeURIComponent(notionId.data)}?projet=${encodeURIComponent(projectId.data)}`;
  let allowed = false;
  try {
    const supabase = await createClient();
    const {
      data: { user },
      error: authError,
    } = await supabase.auth.getUser();
    if (authError || !user)
      return { error: "Session expirée. Reconnectez-vous." };

    const { data: project, error: projectError } = await supabase
      .from("projects")
      .select("id")
      .eq("id", projectId.data)
      .eq("user_id", user.id)
      .maybeSingle();
    if (projectError) throw projectError;
    if (!project) return { error: "Projet introuvable ou inaccessible." };

    if (
      await hasSavedAnalysis(supabase, user.id, projectId.data, notionId.data)
    ) {
      allowed = true;
    } else {
      if (!(await getScopedNotion(notionId.data))) {
        return { error: "Notion introuvable ou hors périmètre." };
      }
      const quota = await checkQuota(user.id);
      if (!quota.autorise) {
        if (
          await hasSavedAnalysis(
            supabase,
            user.id,
            projectId.data,
            notionId.data,
          )
        ) {
          allowed = true;
        } else if (quota.motif === "limite_atteinte") {
          return { error: "Votre quota d’analyses est épuisé.", upgrade: true };
        } else {
          return { error: "Aucun plan n’est associé à votre compte." };
        }
      } else {
        const result = await consumeQuota(user.id, {
          projectId: projectId.data,
          notionId: notionId.data,
        });
        if (result.statut === "refusee") {
          return result.quota.motif === "limite_atteinte"
            ? { error: "Votre quota d’analyses est épuisé.", upgrade: true }
            : { error: "Aucun plan n’est associé à votre compte." };
        }
        allowed = true;
      }
    }
  } catch (error) {
    console.error("Ouverture de l'analyse impossible", error);
    return { error: "Impossible d’ouvrir l’analyse. Veuillez réessayer." };
  }
  if (allowed) redirect(destination);
  return { error: "Impossible d’ouvrir l’analyse." };
}
