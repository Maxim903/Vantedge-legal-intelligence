import "server-only";
import Stripe from "stripe";
import { requireEnv } from "@/lib/server/env";

/**
 * Liste blanche des offres vendables : code de plan -> variable d'environnement
 * contenant l'identifiant de prix Stripe. Le client n'envoie que le code du plan.
 */
export const CHECKOUT_PLANS = {
  pro: "STRIPE_PRICE_PRO",
} as const;

export type CheckoutPlan = keyof typeof CHECKOUT_PLANS;

export const checkoutPlanCodes = Object.keys(CHECKOUT_PLANS) as [
  CheckoutPlan,
  ...CheckoutPlan[],
];

/** Identifiant de prix Stripe d'un plan de la liste blanche. */
export function priceIdForPlan(plan: CheckoutPlan): string {
  return requireEnv(CHECKOUT_PLANS[plan]);
}

/** Plan de la liste blanche correspondant à un identifiant de prix Stripe, s'il existe. */
export function planForPriceId(priceId: string): CheckoutPlan | undefined {
  return checkoutPlanCodes.find(
    (plan) => process.env[CHECKOUT_PLANS[plan]] === priceId,
  );
}

/** URLs de retour fixes, construites à partir de l'URL publique de l'application. */
export function checkoutReturnUrls(): { success: string; cancel: string } {
  const base = requireEnv("APP_URL").replace(/\/+$/, "");
  return {
    success: `${base}/app/compte?checkout=succes`,
    cancel: `${base}/app/compte?checkout=annule`,
  };
}

let client: Stripe | undefined;

export function getStripe(): Stripe {
  client ??= new Stripe(requireEnv("STRIPE_SECRET_KEY"));
  return client;
}
