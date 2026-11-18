import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  getUser: vi.fn(),
  from: vi.fn(),
  select: vi.fn(),
  eq: vi.fn(),
  maybeSingle: vi.fn(),
  hasSavedAnalysis: vi.fn(),
  getScopedNotion: vi.fn(),
  checkQuota: vi.fn(),
  consumeQuota: vi.fn(),
  redirect: vi.fn(),
}));
vi.mock("@/lib/supabase/server", () => ({
  createClient: async () => ({
    auth: { getUser: mocks.getUser },
    from: mocks.from,
  }),
}));
vi.mock("next/navigation", () => ({ redirect: mocks.redirect }));
vi.mock("@/features/quotas/service", () => ({
  checkQuota: mocks.checkQuota,
  consumeQuota: mocks.consumeQuota,
}));
vi.mock("./saved-analysis", () => ({
  hasSavedAnalysis: mocks.hasSavedAnalysis,
}));
vi.mock("./detail-repository", () => ({
  getScopedNotion: mocks.getScopedNotion,
}));

import { openAnalysis } from "./open-action";

const userId = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
const projectId = "11111111-1111-4111-8111-111111111111";
const quota = {
  autorise: true,
  motif: null,
  periode: "2026-11-01",
  plan: "pro",
  limite: 1,
  consomme: 0,
};

function form() {
  const data = new FormData();
  data.set("project_id", projectId);
  data.set("notion_id", "notion-1");
  return data;
}

beforeEach(() => {
  vi.resetAllMocks();
  mocks.getUser.mockResolvedValue({
    data: { user: { id: userId } },
    error: null,
  });
  mocks.from.mockReturnValue({ select: mocks.select });
  mocks.select.mockReturnValue({ eq: mocks.eq });
  mocks.eq.mockReturnValue({ eq: mocks.eq, maybeSingle: mocks.maybeSingle });
  mocks.maybeSingle.mockResolvedValue({ data: { id: projectId }, error: null });
  mocks.hasSavedAnalysis.mockResolvedValue(false);
  mocks.getScopedNotion.mockResolvedValue({ notion_id: "notion-1" });
  mocks.checkQuota.mockResolvedValue(quota);
  mocks.consumeQuota.mockResolvedValue({ statut: "cree", quota });
  mocks.redirect.mockImplementation(() => {
    throw new Error("redirect");
  });
});

describe("ouverture d'analyse", () => {
  it("vérifie puis consomme le quota pour le projet choisi avant de rediriger", async () => {
    await expect(openAnalysis({}, form())).rejects.toThrow("redirect");
    expect(mocks.checkQuota).toHaveBeenCalledWith(userId);
    expect(mocks.consumeQuota).toHaveBeenCalledWith(userId, {
      projectId,
      notionId: "notion-1",
    });
    expect(mocks.checkQuota.mock.invocationCallOrder[0]).toBeLessThan(
      mocks.consumeQuota.mock.invocationCallOrder[0],
    );
    expect(mocks.redirect).toHaveBeenCalledWith(
      `/app/analyse/notion-1?projet=${projectId}`,
    );
  });

  it("rouvre une analyse enregistrée sans consommer", async () => {
    mocks.hasSavedAnalysis.mockResolvedValue(true);
    await expect(openAnalysis({}, form())).rejects.toThrow("redirect");
    expect(mocks.checkQuota).not.toHaveBeenCalled();
    expect(mocks.consumeQuota).not.toHaveBeenCalled();
  });

  it("invite à changer de plan lorsque le quota est épuisé", async () => {
    mocks.checkQuota.mockResolvedValue({
      ...quota,
      autorise: false,
      motif: "limite_atteinte",
    });
    expect(await openAnalysis({}, form())).toMatchObject({ upgrade: true });
    expect(mocks.consumeQuota).not.toHaveBeenCalled();
    expect(mocks.redirect).not.toHaveBeenCalled();
  });

  it("refuse aussi si la dernière unité est prise après la vérification", async () => {
    mocks.consumeQuota.mockResolvedValue({
      statut: "refusee",
      quota: { ...quota, autorise: false, motif: "limite_atteinte" },
    });
    expect(await openAnalysis({}, form())).toMatchObject({ upgrade: true });
    expect(mocks.redirect).not.toHaveBeenCalled();
  });

  it("réutilise l'analyse créée par une ouverture concurrente même si le quota est épuisé", async () => {
    mocks.hasSavedAnalysis
      .mockResolvedValueOnce(false)
      .mockResolvedValueOnce(true);
    mocks.checkQuota.mockResolvedValue({
      ...quota,
      autorise: false,
      motif: "limite_atteinte",
    });
    await expect(openAnalysis({}, form())).rejects.toThrow("redirect");
    expect(mocks.consumeQuota).not.toHaveBeenCalled();
  });

  it("refuse un projet étranger et une notion inexistante avant consommation", async () => {
    mocks.maybeSingle.mockResolvedValueOnce({ data: null, error: null });
    expect(await openAnalysis({}, form())).toHaveProperty("error");
    expect(mocks.checkQuota).not.toHaveBeenCalled();
    mocks.getScopedNotion.mockResolvedValueOnce(null);
    expect(await openAnalysis({}, form())).toHaveProperty("error");
    expect(mocks.consumeQuota).not.toHaveBeenCalled();
  });

  it("refuse une session absente ou un projet mal formé avant les lectures", async () => {
    mocks.getUser.mockResolvedValueOnce({ data: { user: null }, error: null });
    expect(await openAnalysis({}, form())).toHaveProperty("error");
    expect(mocks.from).not.toHaveBeenCalled();
    const invalid = form();
    invalid.set("project_id", "invalide");
    expect(await openAnalysis({}, invalid)).toHaveProperty("error");
    expect(mocks.checkQuota).not.toHaveBeenCalled();
  });

  it("signale un échec technique sans rediriger", async () => {
    vi.spyOn(console, "error").mockImplementation(() => {});
    mocks.consumeQuota.mockRejectedValue(new Error("détail privé"));
    const result = await openAnalysis({}, form());
    expect(result.error).toContain("Impossible");
    expect(JSON.stringify(result)).not.toContain("détail privé");
    expect(mocks.redirect).not.toHaveBeenCalled();
  });
});
