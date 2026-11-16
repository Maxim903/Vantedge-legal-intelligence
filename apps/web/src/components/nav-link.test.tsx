import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

const pathname = vi.fn();
vi.mock("next/navigation", () => ({ usePathname: () => pathname() }));

import { NavLink } from "@/components/nav-link";

describe("NavLink", () => {
  it("marque la page courante avec aria-current", () => {
    pathname.mockReturnValue("/app/projets/42");
    render(<NavLink href="/app/projets">Projets</NavLink>);
    expect(
      screen
        .getByRole("link", { name: "Projets" })
        .getAttribute("aria-current"),
    ).toBe("page");
  });

  it("ne marque pas les autres pages", () => {
    pathname.mockReturnValue("/app/compte");
    render(<NavLink href="/app/projets">Projets</NavLink>);
    expect(
      screen
        .getByRole("link", { name: "Projets" })
        .getAttribute("aria-current"),
    ).toBeNull();
  });
});
