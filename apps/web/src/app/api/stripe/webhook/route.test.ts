import Stripe from "stripe";
import { beforeEach, describe, expect, it, vi } from "vitest";

const SECRET = "whsec_test";

type Call = { table: string; op: string; args: unknown[] };
let calls: Call[];
let seen: Set<string>;
let failWrite: boolean;

function fakeAdmin() {
  return {
    from: (table: string) => ({
      insert: async (row: { event_id: string }) => {
        calls.push({ table, op: "insert", args: [row] });
        if (seen.has(row.event_id))
          return { error: { code: "23505", message: "dup" } };
        seen.add(row.event_id);
        return { error: null };
      },
      delete: () => ({
        eq: async (_c: string, id: string) => {
          calls.push({ table, op: "delete", args: [id] });
          seen.delete(id);
          return { error: null };
        },
      }),
      upsert: async (row: unknown, opts: unknown) => {
        calls.push({ table, op: "upsert", args: [row, opts] });
        return { error: failWrite ? { message: "boom" } : null };
      },
      update: (row: unknown) => ({
        eq: async (col: string, val: string) => {
          calls.push({ table, op: "update", args: [row, col, val] });
          return { error: null };
        },
      }),
    }),
  };
}

vi.mock("@/lib/server/supabase-admin", () => ({
  createAdminClient: fakeAdmin,
}));

import { getStripe } from "@/lib/server/stripe";
import { POST } from "./route";

const PERIOD_END = 1_800_000_000;

function subscription(overrides: Record<string, unknown> = {}) {
  return {
    id: "sub_1",
    object: "subscription",
    customer: "cus_1",
    status: "active",
    metadata: { user_id: "u1" },
    items: {
      data: [
        { price: { id: "price_serveur_pro" }, current_period_end: PERIOD_END },
      ],
    },
    ...overrides,
  };
}

function event(type: string, object: unknown, id = "evt_1") {
  return { id, object: "event", type, data: { object } };
}

function request(evt: unknown, signed = true) {
  const payload = JSON.stringify(evt);
  const headers: Record<string, string> = {};
  if (signed) {
    headers["stripe-signature"] = Stripe.webhooks.generateTestHeaderString({
      payload,
      secret: SECRET,
    });
  }
  return new Request("http://localhost/api/stripe/webhook", {
    method: "POST",
    body: payload,
    headers,
  });
}

const subWrites = () => calls.filter((c) => c.table === "subscriptions");

beforeEach(() => {
  calls = [];
  seen = new Set();
  failWrite = false;
  vi.stubEnv("STRIPE_SECRET_KEY", "sk_test_x");
  vi.stubEnv("STRIPE_WEBHOOK_SECRET", SECRET);
  vi.stubEnv("STRIPE_PRICE_PRO", "price_serveur_pro");
  vi.spyOn(console, "error").mockImplementation(() => {});
  vi.spyOn(getStripe().subscriptions, "retrieve").mockResolvedValue(
    subscription() as never,
  );
});

describe("POST /api/stripe/webhook", () => {
  it("rejette une requête sans signature ou mal signée", async () => {
    const evt = event("customer.subscription.updated", subscription());
    expect((await POST(request(evt, false))).status).toBe(400);
    const forged = request(evt);
    const bad = new Request(forged.url, {
      method: "POST",
      body: JSON.stringify({ ...evt, id: "evt_forge" }),
      headers: forged.headers,
    });
    expect((await POST(bad)).status).toBe(400);
    expect(calls).toEqual([]);
  });

  it("checkout.session.completed crée l'abonnement de l'utilisateur", async () => {
    const res = await POST(
      request(
        event("checkout.session.completed", {
          id: "cs_1",
          mode: "subscription",
          client_reference_id: "u1",
          subscription: "sub_1",
        }),
      ),
    );
    expect(res.status).toBe(200);
    expect(subWrites()).toEqual([
      {
        table: "subscriptions",
        op: "upsert",
        args: [
          {
            user_id: "u1",
            stripe_customer_id: "cus_1",
            stripe_subscription_id: "sub_1",
            plan_code: "pro",
            statut: "active",
            periode_fin: new Date(PERIOD_END * 1000).toISOString(),
          },
          { onConflict: "user_id" },
        ],
      },
    ]);
  });

  it("customer.subscription.updated met à jour le statut", async () => {
    await POST(
      request(
        event(
          "customer.subscription.updated",
          subscription({ status: "past_due" }),
        ),
      ),
    );
    const [write] = subWrites();
    expect(write.op).toBe("upsert");
    expect((write.args[0] as { statut: string }).statut).toBe("past_due");
  });

  it("customer.subscription.updated sans user_id met à jour par identifiant d'abonnement", async () => {
    await POST(
      request(
        event("customer.subscription.updated", subscription({ metadata: {} })),
      ),
    );
    const [write] = subWrites();
    expect(write.op).toBe("update");
    expect(write.args.slice(1)).toEqual(["stripe_subscription_id", "sub_1"]);
  });

  it("customer.subscription.deleted marque l'abonnement comme résilié", async () => {
    await POST(
      request(
        event(
          "customer.subscription.deleted",
          subscription({ status: "canceled" }),
        ),
      ),
    );
    expect(subWrites()).toEqual([
      {
        table: "subscriptions",
        op: "update",
        args: [{ statut: "canceled" }, "stripe_subscription_id", "sub_1"],
      },
    ]);
  });

  it("ignore un évènement déjà vu", async () => {
    const evt = event("customer.subscription.deleted", subscription());
    await POST(request(evt));
    const res = await POST(request(evt));
    expect(await res.json()).toEqual({ received: true, duplicate: true });
    expect(subWrites()).toHaveLength(1);
  });

  it("accepte sans effet un type d'évènement non géré", async () => {
    const res = await POST(request(event("invoice.paid", { id: "in_1" })));
    expect(res.status).toBe(200);
    expect(subWrites()).toEqual([]);
  });

  it("répond 500 et libère l'évènement si l'écriture échoue, pour permettre le rejeu", async () => {
    failWrite = true;
    const evt = event("customer.subscription.updated", subscription());
    expect((await POST(request(evt))).status).toBe(500);
    expect(seen.has("evt_1")).toBe(false);
    failWrite = false;
    expect((await POST(request(evt))).status).toBe(200);
    expect(subWrites().at(-1)?.op).toBe("upsert");
  });

  it("refuse un prix hors liste blanche", async () => {
    const evt = event(
      "customer.subscription.updated",
      subscription({
        items: {
          data: [
            { price: { id: "price_inconnu" }, current_period_end: PERIOD_END },
          ],
        },
      }),
    );
    expect((await POST(request(evt))).status).toBe(500);
    expect(subWrites()).toEqual([]);
  });
});
