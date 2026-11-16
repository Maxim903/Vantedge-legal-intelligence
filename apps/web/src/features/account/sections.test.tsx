import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  from: vi.fn(),
  select: vi.fn(),
  eq: vi.fn(),
  maybeSingle: vi.fn(),
  order: vi.fn(),
  checkQuota: vi.fn(),
}));
vi.mock("@/lib/supabase/server", () => ({
  createClient: async () => ({ from: mocks.from }),
}));
vi.mock("@/features/quotas/service", () => ({ checkQuota: mocks.checkQuota }));

import {
  HistorySection,
  ProfileSection,
  ProjectsSection,
  QuotaSection,
  SubscriptionSection,
} from "./sections";

const userId = "11111111-1111-4111-8111-111111111111";
beforeEach(() => {
  vi.resetAllMocks();
  mocks.from.mockReturnValue({ select: mocks.select });
  mocks.select.mockReturnValue({ eq: mocks.eq });
  mocks.eq.mockReturnValue({
    maybeSingle: mocks.maybeSingle,
    order: mocks.order,
    then: undefined,
  });
});

describe("blocs du compte", () => {
  it("affiche le profil et l'abonnement", async () => {
    mocks.maybeSingle
      .mockResolvedValueOnce({ data: { display_name: "Alice" }, error: null })
      .mockResolvedValueOnce({
        data: { plan_code: "pro", statut: "active" },
        error: null,
      });
    render(
      <>
        {await ProfileSection({ userId, email: "alice@example.test" })}
        {await SubscriptionSection({ userId })}
      </>,
    );
    expect(screen.getByText("Alice")).toBeInTheDocument();
    expect(screen.getByText("alice@example.test")).toBeInTheDocument();
    expect(screen.getByText("pro")).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: /gérer mon abonnement/ }),
    ).toHaveAttribute("href", "/app/compte/abonnement");
  });

  it("affiche le quota restant et le parcours de gestion si épuisé", async () => {
    mocks.checkQuota.mockResolvedValue({
      autorise: false,
      motif: "limite_atteinte",
      periode: "2026-11-01",
      plan: "pro",
      limite: 3,
      consomme: 3,
    });
    render(await QuotaSection({ userId }));
    expect(screen.getByText("0", { selector: "strong" })).toBeInTheDocument();
    expect(screen.getByText(/Quota atteint/)).toBeInTheDocument();
  });

  it("ne présente pas un quota supposé en cas d'erreur", async () => {
    vi.spyOn(console, "error").mockImplementation(() => {});
    mocks.checkQuota.mockRejectedValue(new Error("erreur"));
    render(await QuotaSection({ userId }));
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Impossible de charger les quotas",
    );
    expect(screen.getByRole("link", { name: "Réessayer" })).toHaveAttribute(
      "href",
      "/app/compte",
    );
    expect(screen.queryByText(/Analyses restantes/)).not.toBeInTheDocument();
  });

  it("propose la création lorsque les projets sont vides", async () => {
    mocks.order.mockResolvedValue({ data: [], error: null });
    render(await ProjectsSection({ userId }));
    expect(screen.getByText(/pas encore de projet/)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Créer un projet" }),
    ).toBeInTheDocument();
  });

  it("affiche l'historique vide et un lien vers l'analyse", async () => {
    mocks.order.mockResolvedValue({ data: [], error: null });
    mocks.eq
      .mockReturnValueOnce({ order: mocks.order })
      .mockResolvedValueOnce({ data: [], error: null });
    render(await HistorySection({ userId }));
    expect(screen.getByText(/Aucune analyse enregistrée/)).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: /Accéder à Analyse/ }),
    ).toHaveAttribute("href", "/app/analyse");
  });

  it("affiche les analyses et le nom du projet associé", async () => {
    mocks.order.mockResolvedValue({
      data: [
        {
          id: "analyse-1",
          project_id: "projet-1",
          created_at: "2026-11-16T12:30:00Z",
          parametres: { recherche: "licenciement" },
        },
      ],
      error: null,
    });
    mocks.eq
      .mockReturnValueOnce({ order: mocks.order })
      .mockResolvedValueOnce({
        data: [{ id: "projet-1", nom: "Projet A" }],
        error: null,
      });
    render(await HistorySection({ userId }));
    expect(screen.getByText("Projet A")).toBeInTheDocument();
    expect(screen.getByText(/2026-11-16 12:30/)).toBeInTheDocument();
    expect(screen.getByText(/licenciement/)).toBeInTheDocument();
  });

  it("distingue l'absence de plan d'une erreur de quota", async () => {
    mocks.checkQuota.mockResolvedValue({
      autorise: false,
      motif: "plan_absent",
      periode: "2026-11-01",
      plan: null,
      limite: null,
      consomme: null,
    });
    render(await QuotaSection({ userId }));
    expect(screen.getByText(/aucun plan associé/)).toBeInTheDocument();
    expect(screen.queryByText(/Analyses restantes/)).not.toBeInTheDocument();
  });

  it("affiche une erreur récupérable pour un projet inaccessible", async () => {
    vi.spyOn(console, "error").mockImplementation(() => {});
    mocks.order.mockResolvedValue({
      data: null,
      error: { message: "base indisponible" },
    });
    render(await ProjectsSection({ userId }));
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Impossible de charger les projets",
    );
    expect(screen.getByRole("link", { name: "Réessayer" })).toBeInTheDocument();
  });
});
