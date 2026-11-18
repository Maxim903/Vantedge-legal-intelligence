import { render, screen, within } from "@testing-library/react";
import { expect, it } from "vitest";
import { AppFooter } from "./app-footer";

it("propose les documents légaux et la mention de non-conseil", () => {
  render(<AppFooter />);
  const nav = screen.getByRole("navigation", { name: "Informations légales" });
  expect(
    within(nav).getByRole("link", { name: "Mentions légales" }),
  ).toHaveAttribute("href", "/mentions-legales");
  expect(within(nav).getByRole("link", { name: "CGU" })).toHaveAttribute(
    "href",
    "/cgu",
  );
  expect(
    within(nav).getByRole("link", { name: "Confidentialité" }),
  ).toHaveAttribute("href", "/confidentialite");
  expect(
    screen.getByText("Cet outil ne fournit aucun conseil juridique."),
  ).toBeInTheDocument();
});
