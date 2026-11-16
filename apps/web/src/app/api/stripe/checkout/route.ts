import { NextResponse } from "next/server";
import { z } from "zod";
import { createClient } from "@/lib/supabase/server";
import {
  checkoutPlanCodes,
  checkoutReturnUrls,
  getStripe,
  priceIdForPlan,
} from "@/lib/server/stripe";

const bodySchema = z.object({ plan: z.enum(checkoutPlanCodes) });

const STATUTS_ACTIFS = ["trialing", "active", "past_due"];

function error(message: string, status: number) {
  return NextResponse.json({ error: message }, { status });
}

export async function POST(request: Request) {
  const supabase = await createClient();
  const { data } = await supabase.auth.getUser();
  const user = data?.user;
  if (!user) return error("Authentification requise.", 401);

  const body = bodySchema.safeParse(await request.json().catch(() => null));
  if (!body.success) return error("Plan invalide.", 400);

  // Lecture soumise à la RLS : seule la ligne de l'utilisateur est visible.
  const { data: abonnement } = await supabase
    .from("subscriptions")
    .select("stripe_customer_id, statut")
    .eq("user_id", user.id)
    .maybeSingle();
  if (abonnement && STATUTS_ACTIFS.includes(abonnement.statut)) {
    return error("Un abonnement est déjà actif.", 409);
  }

  try {
    const urls = checkoutReturnUrls();
    const session = await getStripe().checkout.sessions.create({
      mode: "subscription",
      line_items: [{ price: priceIdForPlan(body.data.plan), quantity: 1 }],
      success_url: urls.success,
      cancel_url: urls.cancel,
      client_reference_id: user.id,
      metadata: { user_id: user.id },
      subscription_data: { metadata: { user_id: user.id } },
      ...(abonnement?.stripe_customer_id
        ? { customer: abonnement.stripe_customer_id }
        : { customer_email: user.email }),
    });
    if (!session.url) return error("Session de paiement indisponible.", 502);
    return NextResponse.json({ url: session.url });
  } catch (e) {
    console.error("Échec de création de la session Stripe", e);
    return error("Le paiement est momentanément indisponible.", 502);
  }
}
