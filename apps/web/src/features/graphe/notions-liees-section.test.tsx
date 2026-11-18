import { render, screen } from "@testing-library/react";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({ getNotionsVoisines: vi.fn() }));
vi.mock("./repository", () => mocks);
vi.mock("./notions-graph", () => ({ NotionsGraph: () => null }));

import { NotionsLieesSection } from "./notions-liees-section";

const props = { notionId: "n1", libelle: "Congé", projectId: "p1" };

beforeEach(() => {
  vi.resetAllMocks();
});

describe("notions liées", () => {
  it("affiche les notions et leurs articles communs dans le HTML serveur", async () => {
    mocks.getNotionsVoisines.mockResolvedValue([
      {
        notion_id: "n2",
        libelle: "Absence",
        nombre_articles_communs: 2,
        articles_communs: [],
      },
      {
        notion_id: "n3",
        libelle: "Repos",
        nombre_articles_communs: 1,
        articles_communs: [],
      },
    ]);
    const section = await NotionsLieesSection(props);
    const html = renderToStaticMarkup(section);
    expect(html).toContain("<ul");
    expect(html).toContain("Absence");
    expect(html).toContain("2 articles en commun");
    render(section);
    expect(screen.getAllByRole("listitem")).toHaveLength(2);
    expect(screen.getByText(/Repos — 1 article en commun/)).toBeInTheDocument();
    expect(screen.getByText(/tous codes confondus/)).toBeInTheDocument();
    expect(mocks.getNotionsVoisines).toHaveBeenCalledWith("n1");
  });

  it("distingue l'état vide d'une erreur de lecture et permet de réessayer", async () => {
    mocks.getNotionsVoisines.mockResolvedValueOnce([]);
    const first = render(await NotionsLieesSection(props));
    expect(
      screen.getByText("Aucune notion liée disponible."),
    ).toBeInTheDocument();
    first.unmount();
    vi.spyOn(console, "error").mockImplementation(() => {});
    mocks.getNotionsVoisines.mockRejectedValueOnce(new Error("secret"));
    render(await NotionsLieesSection(props));
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Impossible de charger les notions liées",
    );
    expect(screen.getByRole("link", { name: "Réessayer" })).toHaveAttribute(
      "href",
      "/app/analyse/n1?projet=p1",
    );
    expect(screen.queryByText("secret")).not.toBeInTheDocument();
    vi.restoreAllMocks();
  });
});
