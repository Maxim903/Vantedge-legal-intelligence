import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Disclaimer } from "@/components/disclaimer";

describe("Disclaimer", () => {
  it("affiche la mention légale", () => {
    render(<Disclaimer />);
    expect(
      screen.getByText("Cet outil ne fournit aucun conseil juridique."),
    ).toBeDefined();
  });
});
