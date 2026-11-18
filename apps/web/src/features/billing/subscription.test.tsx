import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const { getUser, maybeSingle, eq } = vi.hoisted(() => ({
  getUser: vi.fn(),
  maybeSingle: vi.fn(),
  eq: vi.fn(),
}));
vi.mock("@/lib/supabase/server", () => ({
  createClient: async () => ({
    auth: { getUser },
    from: () => ({ select: () => ({ eq }) }),
  }),
}));
vi.mock("next/navigation", () => ({
  redirect: (url: string) => {
    throw new Error(`REDIRECT:${url}`);
  },
}));

import { Subscription } from "./subscription";

beforeEach(() => {
  vi.resetAllMocks();
  getUser.mockResolvedValue({ data: { user: { id: "user-a" } }, error: null });
  eq.mockReturnValue({ maybeSingle });
});

describe("Subscription", () => {
  it("affiche le plan, la fin de période et le bouton", async () => {
    maybeSingle.mockResolvedValue({
      data: {
        plan_code: "pro",
        statut: "active",
        periode_fin: "2027-01-15T12:00:00Z",
      },
      error: null,
    });
    render(await Subscription());
    expect(eq).toHaveBeenCalledWith("user_id", "user-a");
    expect(screen.getByText("pro")).toBeInTheDocument();
    expect(screen.getByText("15/01/2027")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Gérer mon abonnement" }),
    ).toBeInTheDocument();
  });

  it("distingue l'absence d'abonnement d'une erreur de lecture", async () => {
    maybeSingle.mockResolvedValue({ data: null, error: null });
    const view = render(await Subscription());
    expect(screen.getByText(/pas encore d’abonnement/)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Souscrire au plan pro" }),
    ).toBeInTheDocument();
    view.unmount();
    vi.spyOn(console, "error").mockImplementation(() => {});
    maybeSingle.mockResolvedValue({ data: null, error: { message: "DB" } });
    render(await Subscription());
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Impossible de charger",
    );
  });

  it("affiche une date indisponible lorsque la période est absente", async () => {
    maybeSingle.mockResolvedValue({
      data: { plan_code: "pro", statut: "canceled", periode_fin: null },
      error: null,
    });
    render(await Subscription());
    expect(screen.getByText("Non disponible")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Souscrire au plan pro" }),
    ).toBeInTheDocument();
  });

  it("redirige si la session a expiré", async () => {
    getUser.mockResolvedValue({ data: { user: null }, error: null });
    await expect(Subscription()).rejects.toThrow(
      "REDIRECT:/connexion?redirect=%2Fapp%2Fcompte%2Fabonnement",
    );
    expect(eq).not.toHaveBeenCalled();
  });
});
