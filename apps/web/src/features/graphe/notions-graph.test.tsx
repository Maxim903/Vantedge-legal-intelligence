import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("next/dynamic", () => ({
  default: () => () => {
    throw new Error("graphique indisponible");
  },
}));

import NotionsGraphique from "./notions-graphique";
import { NotionsLieesContent } from "./notions-liees-section";

const notions = Array.from({ length: 14 }, (_, index) => ({
  notion_id: `n${index}`,
  libelle: `Notion ${index}`,
  nombre_articles_communs: 1,
}));

describe("graphique des notions liées", () => {
  it("représente les douze premières notions et annonce la liste complète", () => {
    const { container } = render(
      <NotionsGraphique libelle="Source" notions={notions} />,
    );
    expect(container.querySelector("svg")).toHaveAttribute(
      "aria-hidden",
      "true",
    );
    expect(container.querySelectorAll("path")).toHaveLength(12);
    expect(
      screen.getByText(/liste complète figure ci-dessous/),
    ).toBeInTheDocument();
  });

  it("conserve la liste si le graphique échoue", () => {
    const log = vi.spyOn(console, "error").mockImplementation(() => {});
    render(<NotionsLieesContent libelle="Source" notions={notions} />);
    expect(screen.getByRole("status")).toHaveTextContent(
      "Graphique indisponible",
    );
    expect(screen.getAllByRole("listitem")).toHaveLength(14);
    expect(log).toHaveBeenCalled();
    log.mockRestore();
  });
});
