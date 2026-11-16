import { beforeEach, describe, expect, it, vi } from "vitest";

const { getUser, from, select, eq, maybeSingle, create } = vi.hoisted(() => ({
  getUser: vi.fn(),
  from: vi.fn(),
  select: vi.fn(),
  eq: vi.fn(),
  maybeSingle: vi.fn(),
  create: vi.fn(),
}));

vi.mock("@/lib/supabase/server", () => ({
  createClient: async () => ({ auth: { getUser }, from }),
}));
vi.mock("@/lib/server/stripe", () => ({
  getStripe: () => ({ billingPortal: { sessions: { create } } }),
}));

import { POST } from "./route";

beforeEach(() => {
  vi.resetAllMocks();
  vi.stubEnv("APP_URL", "https://app.example.fr/");
  getUser.mockResolvedValue({ data: { user: { id: "user-a" } }, error: null });
  from.mockReturnValue({ select });
  select.mockReturnValue({ eq });
  eq.mockReturnValue({ maybeSingle });
  maybeSingle.mockResolvedValue({
    data: { stripe_customer_id: "cus_a" },
    error: null,
  });
  create.mockResolvedValue({ url: "https://billing.stripe.com/session" });
});

describe("POST /api/stripe/portal", () => {
  it("refuse les utilisateurs non authentifiés", async () => {
    getUser.mockResolvedValue({ data: { user: null }, error: null });
    expect((await POST()).status).toBe(401);
    expect(from).not.toHaveBeenCalled();
    expect(create).not.toHaveBeenCalled();
  });

  it("utilise le client Stripe de l'utilisateur et une URL de retour fixe", async () => {
    const response = await POST();
    expect(response.status).toBe(200);
    expect(await response.json()).toEqual({
      url: "https://billing.stripe.com/session",
    });
    expect(from).toHaveBeenCalledWith("subscriptions");
    expect(eq).toHaveBeenCalledWith("user_id", "user-a");
    expect(create).toHaveBeenCalledWith({
      customer: "cus_a",
      return_url: "https://app.example.fr/app/compte/abonnement",
    });
  });

  it("signale l'absence d'abonnement sans appeler Stripe", async () => {
    maybeSingle.mockResolvedValue({ data: null, error: null });
    expect((await POST()).status).toBe(404);
    expect(create).not.toHaveBeenCalled();
  });

  it("signale une erreur de lecture sans appeler Stripe", async () => {
    vi.spyOn(console, "error").mockImplementation(() => {});
    maybeSingle.mockResolvedValue({
      data: null,
      error: { message: "erreur privée" },
    });
    const response = await POST();
    expect(response.status).toBe(500);
    expect(JSON.stringify(await response.json())).not.toContain(
      "erreur privée",
    );
    expect(create).not.toHaveBeenCalled();
  });

  it("masque les erreurs Stripe", async () => {
    vi.spyOn(console, "error").mockImplementation(() => {});
    create.mockRejectedValue(new Error("erreur privée"));
    const response = await POST();
    expect(response.status).toBe(502);
    expect(JSON.stringify(await response.json())).not.toContain(
      "erreur privée",
    );
  });
});
