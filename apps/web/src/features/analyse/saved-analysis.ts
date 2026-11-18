import "server-only";
import { createClient } from "@/lib/supabase/server";

type UserClient = Awaited<ReturnType<typeof createClient>>;

export async function hasSavedAnalysis(
  supabase: UserClient,
  userId: string,
  projectId: string,
  notionId: string,
): Promise<boolean> {
  const { data, error } = await supabase
    .from("analyses")
    .select("id")
    .eq("user_id", userId)
    .eq("project_id", projectId)
    .eq("quota_verifie", true)
    .contains("parametres", { notion_id: notionId })
    .limit(1)
    .maybeSingle();
  if (error)
    throw new Error("Impossible de vérifier l'analyse enregistrée.", {
      cause: error,
    });
  return data !== null;
}
