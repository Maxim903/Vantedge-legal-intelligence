import { NextResponse } from "next/server";
import { handleStripeEvent } from "@/features/billing/webhook";
import { requireEnv } from "@/lib/server/env";
import { getStripe } from "@/lib/server/stripe";
import { createAdminClient } from "@/lib/server/supabase-admin";

const UNIQUE_VIOLATION = "23505";

export async function POST(request: Request) {
  const signature = request.headers.get("stripe-signature");
  if (!signature) {
    return NextResponse.json(
      { error: "Signature manquante." },
      { status: 400 },
    );
  }

  // Le corps brut est indispensable : toute reformulation invaliderait la signature.
  const payload = await request.text();
  const stripe = getStripe();
  let event;
  try {
    event = stripe.webhooks.constructEvent(
      payload,
      signature,
      requireEnv("STRIPE_WEBHOOK_SECRET"),
    );
  } catch {
    return NextResponse.json({ error: "Signature invalide." }, { status: 400 });
  }

  const admin = createAdminClient();
  const { error: insertError } = await admin
    .from("stripe_events")
    .insert({ event_id: event.id });
  if (insertError?.code === UNIQUE_VIOLATION) {
    return NextResponse.json({ received: true, duplicate: true });
  }
  if (insertError) {
    console.error("Journal des évènements Stripe indisponible", insertError);
    return NextResponse.json({ error: "Erreur interne." }, { status: 500 });
  }

  try {
    await handleStripeEvent(event, { admin, stripe });
  } catch (e) {
    console.error(`Échec du traitement de l'évènement ${event.id}`, e);
    // On libère l'évènement pour que la nouvelle tentative de Stripe soit traitée.
    await admin.from("stripe_events").delete().eq("event_id", event.id);
    return NextResponse.json({ error: "Erreur interne." }, { status: 500 });
  }
  return NextResponse.json({ received: true });
}
