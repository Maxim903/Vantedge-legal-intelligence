import "server-only";
import type Stripe from "stripe";
import type { AdminClient } from "@/lib/server/supabase-admin";
import { planForPriceId } from "@/lib/server/stripe";

type Deps = { admin: AdminClient; stripe: Stripe };

function customerId(customer: Stripe.Subscription["customer"]): string {
  return typeof customer === "string" ? customer : customer.id;
}

function throwIfError(error: { message: string } | null, contexte: string) {
  if (error) throw new Error(`${contexte} : ${error.message}`);
}

/** Recopie l'état d'un abonnement Stripe dans `subscriptions`. */
async function syncSubscription(
  { admin }: Deps,
  sub: Stripe.Subscription,
  userId?: string,
) {
  const item = sub.items.data[0];
  const plan = item ? planForPriceId(item.price.id) : undefined;
  if (!item || !plan) {
    throw new Error(`Prix Stripe hors liste blanche (abonnement ${sub.id}).`);
  }
  const champs = {
    stripe_customer_id: customerId(sub.customer),
    stripe_subscription_id: sub.id,
    plan_code: plan,
    statut: sub.status,
    periode_fin: new Date(item.current_period_end * 1000).toISOString(),
  };

  const user = userId ?? sub.metadata?.user_id;
  if (user) {
    const { error } = await admin
      .from("subscriptions")
      .upsert({ user_id: user, ...champs }, { onConflict: "user_id" });
    throwIfError(error, "Écriture de l'abonnement");
    return;
  }
  const { error } = await admin
    .from("subscriptions")
    .update(champs)
    .eq("stripe_subscription_id", sub.id);
  throwIfError(error, "Mise à jour de l'abonnement");
}

export async function handleStripeEvent(event: Stripe.Event, deps: Deps) {
  switch (event.type) {
    case "checkout.session.completed": {
      const session = event.data.object;
      if (session.mode !== "subscription" || !session.subscription) return;
      const userId = session.client_reference_id ?? session.metadata?.user_id;
      if (!userId) throw new Error(`Session ${session.id} sans user_id.`);
      const subId =
        typeof session.subscription === "string"
          ? session.subscription
          : session.subscription.id;
      const sub = await deps.stripe.subscriptions.retrieve(subId);
      await syncSubscription(deps, sub, userId);
      return;
    }
    case "customer.subscription.updated":
      await syncSubscription(deps, event.data.object);
      return;
    case "customer.subscription.deleted": {
      const sub = event.data.object;
      const { error } = await deps.admin
        .from("subscriptions")
        .update({ statut: "canceled" })
        .eq("stripe_subscription_id", sub.id);
      throwIfError(error, "Résiliation de l'abonnement");
      return;
    }
    default:
      return;
  }
}
