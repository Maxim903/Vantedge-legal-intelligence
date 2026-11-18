import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  getUser: vi.fn(),
  from: vi.fn(),
  insert: vi.fn(),
  update: vi.fn(),
  remove: vi.fn(),
  eq: vi.fn(),
  select: vi.fn(),
  maybeSingle: vi.fn(),
  revalidatePath: vi.fn(),
}));
vi.mock("@/lib/supabase/server", () => ({
  createClient: async () => ({
    auth: { getUser: mocks.getUser },
    from: mocks.from,
  }),
}));
vi.mock("next/cache", () => ({ revalidatePath: mocks.revalidatePath }));

import { createProject, deleteProject, renameProject } from "./project-actions";

const userId = "11111111-1111-4111-8111-111111111111";
const projectId = "22222222-2222-4222-8222-222222222222";
function form(values: Record<string, string>) {
  const result = new FormData();
  for (const [key, value] of Object.entries(values)) result.set(key, value);
  return result;
}

beforeEach(() => {
  vi.resetAllMocks();
  mocks.getUser.mockResolvedValue({
    data: { user: { id: userId } },
    error: null,
  });
  mocks.from.mockReturnValue({
    insert: mocks.insert,
    update: mocks.update,
    delete: mocks.remove,
  });
  mocks.insert.mockResolvedValue({ error: null });
  mocks.update.mockReturnValue({ eq: mocks.eq });
  mocks.remove.mockReturnValue({ eq: mocks.eq });
  mocks.eq.mockReturnValue({ eq: mocks.eq, select: mocks.select });
  mocks.select.mockReturnValue({ maybeSingle: mocks.maybeSingle });
  mocks.maybeSingle.mockResolvedValue({ data: { id: projectId }, error: null });
});

describe("actions des projets", () => {
  it("crée un projet au nom de l'utilisateur authentifié", async () => {
    expect(
      await createProject({}, form({ nom: "  Projet A  ", user_id: "autre" })),
    ).toEqual({ message: "Projet créé." });
    expect(mocks.insert).toHaveBeenCalledWith({
      user_id: userId,
      nom: "Projet A",
    });
    expect(mocks.revalidatePath).toHaveBeenCalledWith("/app/compte");
  });

  it("refuse les noms vides et une session expirée", async () => {
    expect((await createProject({}, form({ nom: "  " }))).error).toBeDefined();
    expect(mocks.from).not.toHaveBeenCalled();
    mocks.getUser.mockResolvedValue({ data: { user: null }, error: null });
    expect((await createProject({}, form({ nom: "Projet" }))).error).toContain(
      "Session expirée",
    );
    expect(mocks.from).not.toHaveBeenCalled();
  });

  it("limite le renommage au projet de l'utilisateur", async () => {
    expect(
      await renameProject({}, form({ id: projectId, nom: "Nouveau" })),
    ).toEqual({ message: "Projet renommé." });
    expect(mocks.eq).toHaveBeenCalledWith("id", projectId);
    expect(mocks.eq).toHaveBeenCalledWith("user_id", userId);
    expect(mocks.update).toHaveBeenCalledWith({ nom: "Nouveau" });
  });

  it("ne prétend pas avoir modifié un projet inaccessible", async () => {
    mocks.maybeSingle.mockResolvedValue({ data: null, error: null });
    expect(
      (await renameProject({}, form({ id: projectId, nom: "Nouveau" }))).error,
    ).toContain("inaccessible");
    expect(mocks.revalidatePath).not.toHaveBeenCalled();
  });

  it("exige une confirmation avant de supprimer et limite la suppression au propriétaire", async () => {
    expect((await deleteProject({}, form({ id: projectId }))).error).toContain(
      "Confirmez",
    );
    expect(mocks.remove).not.toHaveBeenCalled();
    expect(
      await deleteProject({}, form({ id: projectId, confirmer: "oui" })),
    ).toEqual({ message: "Projet supprimé." });
    expect(mocks.eq).toHaveBeenCalledWith("user_id", userId);
    expect(mocks.revalidatePath).toHaveBeenCalledWith("/app/compte");
  });

  it("signale les erreurs de base sans divulguer leur contenu", async () => {
    vi.spyOn(console, "error").mockImplementation(() => {});
    mocks.insert.mockResolvedValue({
      error: { message: "détail confidentiel" },
    });
    const result = await createProject({}, form({ nom: "Projet" }));
    expect(result.error).toContain("Impossible");
    expect(JSON.stringify(result)).not.toContain("détail confidentiel");
    expect(mocks.revalidatePath).not.toHaveBeenCalled();
  });

  it("affiche une erreur récupérable si la connexion à la base échoue", async () => {
    vi.spyOn(console, "error").mockImplementation(() => {});
    mocks.insert.mockRejectedValue(new Error("réseau indisponible"));
    expect(await createProject({}, form({ nom: "Projet" }))).toEqual({
      error: "Opération impossible. Veuillez réessayer.",
    });
  });
});
