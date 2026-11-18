import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";
import Home from "./page";

it("présente l'application et donne accès aux pages existantes", () => {
  render(<Home />);
  expect(
    screen.getByRole("heading", { name: "Analyse loi vs marché" }),
  ).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Se connecter" })).toHaveAttribute(
    "href",
    "/connexion",
  );
  expect(screen.getByRole("link", { name: "Créer un compte" })).toHaveAttribute(
    "href",
    "/inscription",
  );
  expect(screen.getByRole("link", { name: "Mon compte" })).toHaveAttribute(
    "href",
    "/app/compte",
  );
});
