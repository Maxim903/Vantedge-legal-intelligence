import { NextResponse } from "next/server";
import { requireEnv } from "@/lib/server/env";
import { getStripe } from "@/lib/server/stripe";
import { createClient } from "@/lib/supabase/server";

export async function POST() {
  const supabase = await createClient();
  const {
    data: { user },
    error: authError,
  } = await supabase.auth.getUser();
  if (authError || !user) {
    return NextResponse.json(
      { error: "Authentification requise." },
      { status: 401 },
    );
  }

  const { data: abonnement, error } = await supabase
    .from("subscriptions")
    .select("stripe_customer_id")
    .eq("user_id", user.id)
    .maybeSingle();

  if (error) {
    console.error("Lecture de l'abonnement impossible", error);
    return NextResponse.json(
      { error: "Impossible de charger l'abonnement." },
      { status: 500 },
    );
  }
  if (!abonnement?.stripe_customer_id) {
    return NextResponse.json(
      { error: "Aucun abonnement trouvé." },
      { status: 404 },
    );
  }

  try {
    const base = requireEnv("APP_URL").replace(/\/+$/, "");
    const session = await getStripe().billingPortal.sessions.create({
      customer: abonnement.stripe_customer_id,
      return_url: `${base}/app/compte/abonnement`,
    });
    return NextResponse.json({ url: session.url });
  } catch (error) {
    console.error("Création du portail de facturation impossible", error);
    return NextResponse.json(
      { error: "Le portail de facturation est momentanément indisponible." },
      { status: 502 },
    );
  }
}
