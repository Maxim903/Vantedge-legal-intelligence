"use server";

import { revalidatePath } from "next/cache";
import { z } from "zod";
import { createClient } from "@/lib/supabase/server";

export type ProjectActionState = { error?: string; message?: string };

const nameSchema = z
  .string()
  .trim()
  .min(1, "Le nom du projet est obligatoire.")
  .max(120, "Le nom ne doit pas dépasser 120 caractères.");
const idSchema = z.uuid();

async function authenticatedClient() {
  const supabase = await createClient();
  const {
    data: { user },
    error,
  } = await supabase.auth.getUser();
  if (error || !user) return null;
  return { supabase, user };
}

async function executeProjectAction(
  action: string,
  operation: () => Promise<ProjectActionState>,
): Promise<ProjectActionState> {
  try {
    return await operation();
  } catch (error) {
    console.error(`Erreur lors de ${action}`, error);
    return { error: "Opération impossible. Veuillez réessayer." };
  }
}

export async function createProject(
  _state: ProjectActionState,
  form: FormData,
): Promise<ProjectActionState> {
  const name = nameSchema.safeParse(form.get("nom"));
  if (!name.success)
    return { error: name.error.issues[0]?.message ?? "Nom invalide." };
  return executeProjectAction("la création du projet", async () => {
    const context = await authenticatedClient();
    if (!context) return { error: "Session expirée. Reconnectez-vous." };

    const { error } = await context.supabase
      .from("projects")
      .insert({ user_id: context.user.id, nom: name.data });
    if (error) {
      console.error("Création du projet impossible", error);
      return { error: "Impossible de créer le projet. Veuillez réessayer." };
    }
    revalidatePath("/app/compte");
    return { message: "Projet créé." };
  });
}

export async function renameProject(
  _state: ProjectActionState,
  form: FormData,
): Promise<ProjectActionState> {
  const id = idSchema.safeParse(form.get("id"));
  const name = nameSchema.safeParse(form.get("nom"));
  if (!id.success) return { error: "Projet invalide." };
  if (!name.success)
    return { error: name.error.issues[0]?.message ?? "Nom invalide." };
  return executeProjectAction("le renommage du projet", async () => {
    const context = await authenticatedClient();
    if (!context) return { error: "Session expirée. Reconnectez-vous." };

    const { data, error } = await context.supabase
      .from("projects")
      .update({ nom: name.data })
      .eq("id", id.data)
      .eq("user_id", context.user.id)
      .select("id")
      .maybeSingle();
    if (error) {
      console.error("Renommage du projet impossible", error);
      return { error: "Impossible de renommer le projet. Veuillez réessayer." };
    }
    if (!data) return { error: "Projet introuvable ou inaccessible." };
    revalidatePath("/app/compte");
    return { message: "Projet renommé." };
  });
}

export async function deleteProject(
  _state: ProjectActionState,
  form: FormData,
): Promise<ProjectActionState> {
  const id = idSchema.safeParse(form.get("id"));
  if (!id.success) return { error: "Projet invalide." };
  if (form.get("confirmer") !== "oui")
    return { error: "Confirmez la suppression du projet et de ses analyses." };
  return executeProjectAction("la suppression du projet", async () => {
    const context = await authenticatedClient();
    if (!context) return { error: "Session expirée. Reconnectez-vous." };

    const { data, error } = await context.supabase
      .from("projects")
      .delete()
      .eq("id", id.data)
      .eq("user_id", context.user.id)
      .select("id")
      .maybeSingle();
    if (error) {
      console.error("Suppression du projet impossible", error);
      return {
        error: "Impossible de supprimer le projet. Veuillez réessayer.",
      };
    }
    if (!data) return { error: "Projet introuvable ou inaccessible." };
    revalidatePath("/app/compte");
    return { message: "Projet supprimé." };
  });
}
