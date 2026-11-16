import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import Cgu from "./cgu/page";
import Confidentialite from "./confidentialite/page";
import MentionsLegales from "./mentions-legales/page";

describe("gabarits légaux", () => {
  it.each([
    ["Mentions légales", MentionsLegales],
    ["Conditions générales d’utilisation", Cgu],
    ["Politique de confidentialité", Confidentialite],
  ])("%s indique clairement que le document est à valider", (title, Page) => {
    render(<Page />);
    expect(
      screen.getByRole("heading", { name: title, level: 1 }),
    ).toBeInTheDocument();
    expect(screen.getByText("À VALIDER PAR UN JURISTE")).toBeInTheDocument();
    expect(
      screen.getByText(/ne constitue pas un texte juridique en vigueur/),
    ).toBeInTheDocument();
  });

  it("inclut les clauses demandées dans les CGU", () => {
    render(<Cgu />);
    expect(
      screen.getByText("Cet outil ne fournit aucun conseil juridique."),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Limitation de responsabilité" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Usages autorisés des données" }),
    ).toBeInTheDocument();
  });
});
