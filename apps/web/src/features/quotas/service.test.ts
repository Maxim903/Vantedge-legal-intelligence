import { beforeEach, describe, expect, it, vi } from "vitest";

const { rpc } = vi.hoisted(() => ({ rpc: vi.fn() }));
vi.mock("@/lib/server/supabase-admin", () => ({
  createAdminClient: () => ({ rpc }),
}));

import { checkQuota, consumeQuota } from "./service";

const userId = "11111111-1111-4111-8111-111111111111";
const disponible = {
  autorise: true,
  motif: null,
  periode: "2026-11-01",
  plan: "pro",
  limite: 2,
  consomme: 1,
};

beforeEach(() => {
  rpc.mockReset();
});

describe("service des quotas", () => {
  it("vérifie sans consommer", async () => {
    rpc.mockResolvedValue({ data: disponible, error: null });
    expect(await checkQuota(userId)).toEqual(disponible);
    expect(rpc).toHaveBeenCalledWith("quota_mensuel", {
      p_user_id: userId,
      p_consume: false,
    });
  });

  it("réserve la dernière unité et refuse ensuite une limite atteinte", async () => {
    const limite = { ...disponible, consomme: 2 };
    rpc
      .mockResolvedValueOnce({ data: limite, error: null })
      .mockResolvedValueOnce({
        data: { ...limite, autorise: false, motif: "limite_atteinte" },
        error: null,
      });
    expect(await consumeQuota(userId)).toEqual(limite);
    expect(await consumeQuota(userId)).toMatchObject({
      autorise: false,
      motif: "limite_atteinte",
      consomme: 2,
    });
    expect(rpc).toHaveBeenCalledWith("quota_mensuel", {
      p_user_id: userId,
      p_consume: true,
    });
  });

  it("restitue le nouveau mois renvoyé par la base", async () => {
    rpc.mockResolvedValue({
      data: { ...disponible, periode: "2026-12-01", consomme: 0 },
      error: null,
    });
    expect(await checkQuota(userId)).toMatchObject({
      periode: "2026-12-01",
      consomme: 0,
    });
  });

  it("refuse explicitement un plan absent", async () => {
    const absent = {
      autorise: false,
      motif: "plan_absent",
      periode: "2026-11-01",
      plan: null,
      limite: null,
      consomme: null,
    };
    rpc.mockResolvedValue({ data: absent, error: null });
    expect(await consumeQuota(userId)).toEqual(absent);
  });

  it("propage les erreurs de base et refuse une réponse invalide", async () => {
    rpc.mockResolvedValueOnce({
      data: null,
      error: { message: "base indisponible" },
    });
    await expect(checkQuota(userId)).rejects.toThrow(
      "Impossible de vérifier le quota.",
    );
    rpc.mockResolvedValueOnce({ data: { autorise: true }, error: null });
    await expect(checkQuota(userId)).rejects.toThrow();
  });

  it("refuse un identifiant invalide sans appeler la base", async () => {
    await expect(consumeQuota("invalide")).rejects.toThrow();
    expect(rpc).not.toHaveBeenCalled();
  });

  it("consomme et enregistre une analyse dans une seule transaction", async () => {
    const projectId = "22222222-2222-4222-8222-222222222222";
    rpc.mockResolvedValue({
      data: { statut: "cree", quota: disponible },
      error: null,
    });
    expect(
      await consumeQuota(userId, { projectId, notionId: "notion-1" }),
    ).toMatchObject({ statut: "cree" });
    expect(rpc).toHaveBeenCalledWith("ouvrir_analyse", {
      p_user_id: userId,
      p_project_id: projectId,
      p_notion_id: "notion-1",
    });
    rpc.mockResolvedValue({
      data: {
        statut: "cree",
        quota: { ...disponible, autorise: false, motif: "limite_atteinte" },
      },
      error: null,
    });
    await expect(
      consumeQuota(userId, { projectId, notionId: "notion-1" }),
    ).rejects.toThrow();
  });
});
