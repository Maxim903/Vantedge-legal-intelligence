import { Suspense } from "react";
import { createClient } from "@/lib/supabase/server";

async function Utilisateur() {
  const supabase = await createClient();
  const { data } = await supabase.auth.getUser();
  return <p>Connecté en tant que {data.user?.email}.</p>;
}

export default function AppHome() {
  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-2xl font-semibold">Espace connecté</h1>
      <Suspense fallback={<p>Chargement…</p>}>
        <Utilisateur />
      </Suspense>
    </div>
  );
}
