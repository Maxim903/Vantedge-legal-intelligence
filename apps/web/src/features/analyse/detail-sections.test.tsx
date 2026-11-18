import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  getArticles: vi.fn(),
  getRequetes: vi.fn(),
  getVolumes: vi.fn(),
  getIntentions: vi.fn(),
  getSerp: vi.fn(),
}));
vi.mock("./detail-repository", () => mocks);
vi.mock("./volume-chart", () => ({
  VolumeChart: () => <p>Courbe mensuelle</p>,
}));

import {
  ArticlesSection,
  RequetesSection,
  VolumesSection,
  IntentionsSection,
  SerpSection,
} from "./detail-sections";

beforeEach(() => {
  vi.resetAllMocks();
  Object.values(mocks).forEach((fn) => fn.mockResolvedValue([]));
});

describe("blocs du détail", () => {
  it.each([
    ["articles", ArticlesSection, mocks.getArticles, "Aucun article"],
    ["requêtes", RequetesSection, mocks.getRequetes, "Aucune requête"],
    ["volumes", VolumesSection, mocks.getVolumes, "Aucun volume"],
    ["intentions", IntentionsSection, mocks.getIntentions, "Aucune intention"],
    ["SERP", SerpSection, mocks.getSerp, "Aucun résultat SERP"],
  ])("%s distingue vide et erreur", async (_label, section, mock, empty) => {
    const view = render(await section({ notionId: "n1", projectId: "p1" }));
    expect(screen.getByText(new RegExp(empty))).toBeInTheDocument();
    view.unmount();
    vi.spyOn(console, "error").mockImplementation(() => {});
    mock.mockRejectedValue(new Error("secret"));
    render(await section({ notionId: "n1", projectId: "p1" }));
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Impossible de charger",
    );
    expect(screen.getByRole("link", { name: "Réessayer" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Réessayer" })).toHaveAttribute(
      "href",
      "/app/analyse/n1?projet=p1",
    );
    expect(screen.queryByText("secret")).not.toBeInTheDocument();
  });

  it("affiche la version et le lien Légifrance d'un article", async () => {
    mocks.getArticles.mockResolvedValue([
      {
        article_id: "LEGIARTI000000000001",
        article_version_id: "LEGIARTI000000000002",
        numero: "L1",
        etat: "ABROGE",
        date_debut: "2020-01-01",
        date_fin: "2021-01-01",
        en_vigueur: false,
      },
    ]);
    render(await ArticlesSection({ notionId: "n1", projectId: "p1" }));
    expect(screen.getByRole("link", { name: /Article L1/ })).toHaveAttribute(
      "href",
      "https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000000000002",
    );
    expect(
      screen.getByText(/aucune version actuellement en vigueur/),
    ).toBeInTheDocument();
  });

  it("affiche les requêtes, volumes et intentions disponibles", async () => {
    mocks.getRequetes.mockResolvedValue([
      { requete_id: "r1", texte: "congé", score_rattachement: 0.8 },
    ]);
    mocks.getVolumes.mockResolvedValue([{ mois: "2026-01-01", volume: 20 }]);
    mocks.getIntentions.mockResolvedValue([
      { intention_type: null, nombre_requetes: 2 },
    ]);
    render(
      <>
        {await RequetesSection({ notionId: "n1", projectId: "p1" })}
        {await VolumesSection({ notionId: "n1", projectId: "p1" })}
        {await IntentionsSection({ notionId: "n1", projectId: "p1" })}
      </>,
    );
    expect(screen.getByText(/congé — rattachement/)).toBeInTheDocument();
    expect(screen.getByText("Courbe mensuelle")).toBeInTheDocument();
    expect(
      screen.getByText(/Intention inconnue : 2 requêtes/),
    ).toBeInTheDocument();
  });

  it("groupe les résultats SERP et neutralise les liens non HTTP", async () => {
    mocks.getSerp.mockResolvedValue([
      {
        requete_id: "r1",
        texte: "congé",
        date_resultat: "2026-01-01",
        position: 1,
        domaine: "exemple.fr",
        url: "https://exemple.fr/a",
      },
      {
        requete_id: "r1",
        texte: "congé",
        date_resultat: "2026-01-01",
        position: 3,
        domaine: "suspect",
        url: "javascript:alert(1)",
      },
    ]);
    render(await SerpSection({ notionId: "n1", projectId: "p1" }));
    expect(screen.getByText("Dernière SERP : 2026-01-01")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "exemple.fr" })).toHaveAttribute(
      "href",
      "https://exemple.fr/a",
    );
    expect(screen.getByText(/suspect — lien indisponible/)).toBeInTheDocument();
    expect(
      screen.queryByRole("link", { name: "suspect" }),
    ).not.toBeInTheDocument();
  });
});
