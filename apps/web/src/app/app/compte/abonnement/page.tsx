import type { Metadata } from "next";
import { Suspense } from "react";
import { Subscription } from "@/features/billing/subscription";

export const metadata: Metadata = { title: "Mon abonnement" };

export default function AbonnementPage() {
  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-semibold">Mon abonnement</h1>
      <Suspense fallback={<p>Chargement de votre abonnement…</p>}>
        <Subscription />
      </Suspense>
    </div>
  );
}
