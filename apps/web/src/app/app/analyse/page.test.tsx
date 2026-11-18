import { fireEvent, render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  getUser: vi.fn(),
  listAnalysis: vi.fn(),
  listSituations: vi.fn(),
  redirect: vi.fn(),
}));

vi.mock("@/lib/supabase/server", () => ({
  createClient: async () => ({ auth: { getUser: mocks.getUser } }),
}));
vi.mock("next/navigation", () => ({ redirect: mocks.redirect }));
vi.mock("@/features/analyse/repository", async (importOriginal) => {
  const original =
    await importOriginal<typeof import("@/features/analyse/repository")>();
  return {
    ...original,
    listAnalysis: mocks.listAnalysis,
    listSituations: mocks.listSituations,
  };
});

import { Analyse } from "./page";

const row = {
  gap_score_id: "gap-1",
  notion_id: "notion-1",
  notion_libelle: "Congé",
  code_id: "code-1",
  livre_id: null,
  pays_langue_id: "fr-fr",
  date_calcul: "2026-01-01",
  version_score: "v1",
  indice_demande: 20,
  indice_saturation: 30,
  indice_importance_normative: 40,
  score_ecart: 14,
  criticite_semantique: 50,
  taille_cohorte: 12,
};

beforeEach(() => {
  vi.resetAllMocks();
  mocks.getUser.mockResolvedValue({
    data: { user: { id: "user-1" } },
    error: null,
  });
  mocks.listAnalysis.mockResolvedValue({ rows: [row], hasNextPage: true });
  mocks.listSituations.mockResolvedValue([
    { situation_id: "s1", libelle: "Naissance" },
  ]);
  mocks.redirect.mockImplementation(() => {
    throw new Error("redirect");
  });
});

describe("analyse loi vs marché", () => {
  it("affiche les scores datés, les définitions et les paramètres sélectionnés", async () => {
    render(
      await Analyse({
        searchParams: Promise.resolve({
          tri: "ecart",
          ordre: "desc",
          situation: "s1",
          page: "2",
        }),
      }),
    );
    expect(mocks.listAnalysis).toHaveBeenCalledWith({
      tri: "ecart",
      ordre: "desc",
      situation: "s1",
      page: 2,
    });
    expect(screen.getByLabelText("Situation de vie")).toHaveValue("s1");
    expect(screen.getByLabelText("Trier par")).toHaveValue("ecart");
    const table = screen.getByRole("table");
    expect(
      within(table).getByRole("rowheader", { name: "Congé" }),
    ).toBeInTheDocument();
    for (const value of ["20", "30", "40", "14", "50", "2026-01-01"]) {
      expect(within(table).getByText(value)).toBeInTheDocument();
    }
    expect(within(table).getByText(/^v1/)).toBeInTheDocument();
    for (const name of [
      "demande",
      "saturation",
      "importance normative",
      "écart",
      "criticité sémantique",
    ]) {
      expect(screen.getByLabelText(`Définition : ${name}`)).toBeInTheDocument();
    }
    const definition = screen.getByLabelText("Définition : demande");
    fireEvent.click(definition);
    expect(definition.closest("details")).toHaveAttribute("open");
    expect(
      screen.getByRole("button", { name: "Appliquer" }).closest("form"),
    ).not.toHaveFormValues({ page: "2" });
    expect(
      screen.getByText(/calcul par livre n’est pas encore disponible/),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Page précédente" }),
    ).toHaveAttribute(
      "href",
      "/app/analyse?tri=ecart&ordre=desc&situation=s1&page=1",
    );
    expect(screen.getByRole("link", { name: "Page suivante" })).toHaveAttribute(
      "href",
      "/app/analyse?tri=ecart&ordre=desc&situation=s1&page=3",
    );
  });

  it("affiche un état vide sans page suivante", async () => {
    mocks.listAnalysis.mockResolvedValue({ rows: [], hasNextPage: false });
    render(await Analyse({ searchParams: Promise.resolve({}) }));
    expect(screen.getByText(/Aucune analyse disponible/)).toBeInTheDocument();
    expect(
      screen.queryByRole("link", { name: "Page suivante" }),
    ).not.toBeInTheDocument();
  });

  it("affiche séparément plusieurs scores pour une même notion", async () => {
    mocks.listAnalysis.mockResolvedValue({
      rows: [row, { ...row, gap_score_id: "gap-2", date_calcul: "2026-02-01" }],
      hasNextPage: false,
    });
    render(await Analyse({ searchParams: Promise.resolve({}) }));
    expect(screen.getAllByRole("rowheader", { name: "Congé" })).toHaveLength(2);
    expect(screen.getByText("2026-01-01")).toBeInTheDocument();
    expect(screen.getByText("2026-02-01")).toBeInTheDocument();
  });

  it("signale des paramètres invalides avant d'interroger BigQuery", async () => {
    render(await Analyse({ searchParams: Promise.resolve({ page: "0" }) }));
    expect(screen.getByRole("alert")).toHaveTextContent("paramètres");
    expect(mocks.listAnalysis).not.toHaveBeenCalled();
    expect(mocks.listSituations).not.toHaveBeenCalled();
  });

  it("affiche une erreur récupérable sans révéler l'erreur technique", async () => {
    vi.spyOn(console, "error").mockImplementation(() => {});
    mocks.listAnalysis.mockRejectedValue(new Error("détail confidentiel"));
    render(await Analyse({ searchParams: Promise.resolve({}) }));
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Impossible de charger",
    );
    expect(screen.getByRole("link", { name: "Réessayer" })).toBeInTheDocument();
    expect(screen.queryByText(/détail confidentiel/)).not.toBeInTheDocument();
  });

  it("redirige les visiteurs non authentifiés sans lire les données", async () => {
    mocks.getUser.mockResolvedValue({ data: { user: null }, error: null });
    await expect(
      Analyse({ searchParams: Promise.resolve({}) }),
    ).rejects.toThrow("redirect");
    expect(mocks.redirect).toHaveBeenCalledWith(
      "/connexion?redirect=%2Fapp%2Fanalyse",
    );
    expect(mocks.listAnalysis).not.toHaveBeenCalled();
  });
});
