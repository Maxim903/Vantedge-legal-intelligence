import { act, render, screen } from "@testing-library/react";
import { use, type ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  getUser: vi.fn(),
  getScopedNotion: vi.fn(),
  getArticles: vi.fn(),
  getRequetes: vi.fn(),
  getVolumes: vi.fn(),
  getIntentions: vi.fn(),
  getSerp: vi.fn(),
  hasSavedAnalysis: vi.fn(),
  relatedSection: vi.fn(),
  from: vi.fn(),
  select: vi.fn(),
  eq: vi.fn(),
  order: vi.fn(),
  pending: Promise.resolve([] as unknown[]),
  redirect: vi.fn(),
  notFound: vi.fn(),
}));
vi.mock("@/lib/supabase/server", () => ({
  createClient: async () => ({
    auth: { getUser: mocks.getUser },
    from: mocks.from,
  }),
}));
vi.mock("next/navigation", () => ({
  redirect: mocks.redirect,
  notFound: mocks.notFound,
}));
vi.mock("@/features/analyse/detail-repository", () => mocks);
vi.mock("@/features/analyse/saved-analysis", () => ({
  hasSavedAnalysis: mocks.hasSavedAnalysis,
}));
vi.mock("@/features/analyse/open-form", () => ({
  OpenAnalysisForm: () => <p>Choix du projet</p>,
}));
vi.mock("@/features/graphe/notions-liees-section", () => ({
  NotionsLieesSection: (props: unknown) => mocks.relatedSection(props),
}));
vi.mock("@/features/analyse/detail-sections", () => ({
  DetailSection: ({
    title,
    children,
  }: {
    title: string;
    children: ReactNode;
  }) => (
    <section>
      <h2>{title}</h2>
      {children}
    </section>
  ),
  ArticlesSection: () => {
    use(mocks.pending);
    return <p>Aucun article source disponible.</p>;
  },
  RequetesSection: () => <p>Aucune requête associée disponible.</p>,
  VolumesSection: () => <p>Aucun volume mensuel disponible.</p>,
  IntentionsSection: () => <p>Aucune intention disponible.</p>,
  SerpSection: () => <p>Aucun résultat SERP disponible.</p>,
}));

import { NotionDetail } from "./page";

beforeEach(() => {
  vi.resetAllMocks();
  mocks.getUser.mockResolvedValue({ data: { user: { id: "u" } }, error: null });
  mocks.getScopedNotion.mockResolvedValue({
    notion_id: "n1",
    libelle: "Congé",
    definition_courte: null,
  });
  mocks.hasSavedAnalysis.mockResolvedValue(true);
  mocks.relatedSection.mockResolvedValue(<p>Aucune notion liée disponible.</p>);
  mocks.from.mockReturnValue({ select: mocks.select });
  mocks.select.mockReturnValue({ eq: mocks.eq });
  mocks.eq.mockReturnValue({ order: mocks.order });
  mocks.order.mockResolvedValue({
    data: [{ id: "11111111-1111-4111-8111-111111111111", nom: "Projet" }],
    error: null,
  });
  for (const fn of [
    mocks.getArticles,
    mocks.getRequetes,
    mocks.getVolumes,
    mocks.getIntentions,
    mocks.getSerp,
  ]) {
    fn.mockResolvedValue([]);
  }
  mocks.redirect.mockImplementation(() => {
    throw new Error("redirect");
  });
  mocks.notFound.mockImplementation(() => {
    throw new Error("not-found");
  });
});

describe("page détail de notion", () => {
  it("affiche les blocs séparément pendant le chargement puis leurs états", async () => {
    mocks.pending = new Promise(() => {});
    await act(async () => {
      render(
        await NotionDetail({
          notionId: "n1",
          projectId: "11111111-1111-4111-8111-111111111111",
        }),
      );
    });
    expect(screen.getByRole("heading", { name: "Congé" })).toBeInTheDocument();
    expect(
      screen.getByText("Chargement : Articles sources…"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Aucune requête associée disponible."),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Notions liées" }),
    ).toBeInTheDocument();
    expect(mocks.relatedSection).toHaveBeenCalledWith({
      notionId: "n1",
      libelle: "Congé",
      projectId: "11111111-1111-4111-8111-111111111111",
    });
  });

  it("redirige avant les lectures si la session est absente", async () => {
    mocks.getUser.mockResolvedValue({ data: { user: null }, error: null });
    await expect(NotionDetail({ notionId: "n1" })).rejects.toThrow("redirect");
    expect(mocks.redirect).toHaveBeenCalledWith(
      "/connexion?redirect=%2Fapp%2Fanalyse%2Fn1",
    );
    expect(mocks.getScopedNotion).not.toHaveBeenCalled();
    expect(mocks.relatedSection).not.toHaveBeenCalled();
  });

  it("attend le résultat des notions liées avant de rendre la page", async () => {
    let finish: (value: ReactNode) => void = () => {
      throw new Error("Résolveur indisponible");
    };
    const pending = new Promise<ReactNode>((resolve) => {
      finish = resolve;
    });
    mocks.relatedSection.mockReturnValueOnce(pending);
    let complete = false;
    const page = NotionDetail({
      notionId: "n1",
      projectId: "11111111-1111-4111-8111-111111111111",
    }).then((result) => {
      complete = true;
      return result;
    });
    await vi.waitFor(() => expect(mocks.relatedSection).toHaveBeenCalled());
    expect(complete).toBe(false);
    finish(<p>Liste rendue côté serveur</p>);
    render(await page);
    expect(screen.getByText("Liste rendue côté serveur")).toBeInTheDocument();
  });

  it("ne charge pas les blocs pour une notion hors périmètre", async () => {
    mocks.getScopedNotion.mockResolvedValue(null);
    await expect(
      NotionDetail({
        notionId: "n1",
        projectId: "11111111-1111-4111-8111-111111111111",
      }),
    ).rejects.toThrow("not-found");
    expect(mocks.getArticles).not.toHaveBeenCalled();
  });

  it("exige un projet et une analyse enregistrée avant de montrer les données", async () => {
    mocks.hasSavedAnalysis.mockResolvedValue(false);
    render(
      await NotionDetail({
        notionId: "n1",
        projectId: "11111111-1111-4111-8111-111111111111",
      }),
    );
    expect(screen.getByText("Choix du projet")).toBeInTheDocument();
    expect(mocks.hasSavedAnalysis).toHaveBeenCalledWith(
      expect.anything(),
      "u",
      "11111111-1111-4111-8111-111111111111",
      "n1",
    );
    expect(mocks.getScopedNotion).not.toHaveBeenCalled();
    expect(mocks.relatedSection).not.toHaveBeenCalled();
  });
});
