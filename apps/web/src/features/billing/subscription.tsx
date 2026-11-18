import "server-only";
import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { CheckoutButton } from "./checkout-button";
import { PortalButton } from "./portal-button";

export async function Subscription() {
  const supabase = await createClient();
  const {
    data: { user },
    error: authError,
  } = await supabase.auth.getUser();
  if (authError || !user)
    redirect("/connexion?redirect=%2Fapp%2Fcompte%2Fabonnement");

  const { data: subscription, error } = await supabase
    .from("subscriptions")
    .select("plan_code, statut, periode_fin")
    .eq("user_id", user.id)
    .maybeSingle();

  if (error) {
    console.error("Lecture de l'abonnement impossible", error);
    return (
      <p role="alert">
        Impossible de charger votre abonnement. Veuillez réessayer.
      </p>
    );
  }
  if (!subscription)
    return (
      <div className="space-y-4">
        <p>Vous n’avez pas encore d’abonnement.</p>
        <CheckoutButton />
      </div>
    );

  const periodEnd = subscription.periode_fin
    ? new Date(subscription.periode_fin)
    : null;
  const date =
    periodEnd && !Number.isNaN(periodEnd.getTime())
      ? `${String(periodEnd.getUTCDate()).padStart(2, "0")}/${String(periodEnd.getUTCMonth() + 1).padStart(2, "0")}/${periodEnd.getUTCFullYear()}`
      : "Non disponible";

  return (
    <div className="flex flex-col items-start gap-4">
      <dl className="space-y-2">
        <div>
          <dt className="font-semibold">Plan actuel</dt>
          <dd>{subscription.plan_code}</dd>
        </div>
        <div>
          <dt className="font-semibold">Statut</dt>
          <dd>{subscription.statut}</dd>
        </div>
        <div>
          <dt className="font-semibold">Fin de période / renouvellement</dt>
          <dd>{date}</dd>
        </div>
      </dl>
      <PortalButton />
      {!["trialing", "active", "past_due"].includes(subscription.statut) && (
        <CheckoutButton />
      )}
    </div>
  );
}
