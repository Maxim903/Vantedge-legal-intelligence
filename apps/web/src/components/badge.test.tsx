import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Badge } from "@/components/badge";

describe("Badge", () => {
  it("affiche son contenu", () => {
    render(<Badge>VIGUEUR</Badge>);
    expect(screen.getByText("VIGUEUR")).toBeInTheDocument();
  });
});
