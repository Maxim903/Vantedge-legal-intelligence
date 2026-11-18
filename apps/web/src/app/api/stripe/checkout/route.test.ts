import { beforeEach, describe, expect, it, vi } from "vitest";

const getUser = vi.fn();
const maybeSingle = vi.fn();
const create = vi.fn();

vi.mock("@/lib/supabase/server", () => ({
  createClient: async () => ({
    auth: { getUser },
    from: () => ({
      select: () => ({ eq: () => ({ maybeSingle }) }),
    }),
  }),
}));
vi.mock("stripe", () => ({
  default: class {
    checkout = { sessions: { create } };
  },
}));

import { POST } from "./route";

function req(body: unknown) {
  return new Request("http://localhost/api/stripe/checkout", {
    method: "POST",
    body: typeof body === "string" ? body : JSON.stringify(body),
  });
}

beforeEach(() => {
  vi.stubEnv("STRIPE_SECRET_KEY", "sk_test_x");
  vi.stubEnv("STRIPE_PRICE_PRO", "price_serveur_pro");
  vi.stubEnv("APP_URL", "https://app.exemple.fr/");
  getUser.mockReset().mockResolvedValue({
    data: { user: { id: "u1", email: "a@exemple.fr" } },
  });
  maybeSingle.mockReset().mockResolvedValue({ data: null });
  create
    .mockReset()
    .mockResolvedValue({ url: "https://checkout.stripe.com/s" });
  vi.spyOn(console, "error").mockImplementation(() => {});
});

describe("POST /api/stripe/checkout", () => {
  it("refuse un utilisateur non authentifié", async () => {
    getUser.mockResolvedValue({ data: { user: null } });
    const res = await POST(req({ plan: "pro" }));
    expect(res.status).toBe(401);
    expect(create).not.toHaveBeenCalled();
  });

  it("refuse un plan hors liste blanche, y compris un identifiant de prix", async () => {
    for (const body of [
      { plan: "gratuit" },
      { plan: "price_pirate" },
      {},
      "pas du json",
    ]) {
      const res = await POST(req(body));
      expect(res.status).toBe(400);
    }
    expect(create).not.toHaveBeenCalled();
  });

  it("utilise le prix serveur et les URLs fixes, ignorant les champs du client", async () => {
    const res = await POST(
      req({
        plan: "pro",
        price: "price_pirate",
        success_url: "https://evil.example",
        priceId: "price_pirate",
      }),
    );
    expect(res.status).toBe(200);
    expect(await res.json()).toEqual({ url: "https://checkout.stripe.com/s" });
    const args = create.mock.calls[0][0];
    expect(args.line_items).toEqual([
      { price: "price_serveur_pro", quantity: 1 },
    ]);
    expect(args.success_url).toBe(
      "https://app.exemple.fr/app/compte?checkout=succes",
    );
    expect(args.cancel_url).toBe(
      "https://app.exemple.fr/app/compte?checkout=annule",
    );
    expect(args.client_reference_id).toBe("u1");
    expect(args.customer_email).toBe("a@exemple.fr");
  });

  it("réutilise le client Stripe existant", async () => {
    maybeSingle.mockResolvedValue({
      data: { stripe_customer_id: "cus_1", statut: "canceled" },
    });
    await POST(req({ plan: "pro" }));
    const args = create.mock.calls[0][0];
    expect(args.customer).toBe("cus_1");
    expect(args.customer_email).toBeUndefined();
  });

  it("refuse un second abonnement actif", async () => {
    maybeSingle.mockResolvedValue({
      data: { stripe_customer_id: "cus_1", statut: "active" },
    });
    const res = await POST(req({ plan: "pro" }));
    expect(res.status).toBe(409);
    expect(create).not.toHaveBeenCalled();
  });

  it("masque l'erreur Stripe", async () => {
    create.mockRejectedValue(new Error("secret interne"));
    const res = await POST(req({ plan: "pro" }));
    expect(res.status).toBe(502);
    expect(JSON.stringify(await res.json())).not.toContain("secret interne");
  });
});
