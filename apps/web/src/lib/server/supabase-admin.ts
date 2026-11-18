import "server-only";
import { createClient } from "@supabase/supabase-js";
import { getClientEnv } from "@/lib/env";
import { requireEnv } from "@/lib/server/env";

/** Client service role : contourne la RLS, à réserver aux traitements serveur de confiance. */
export function createAdminClient() {
  return createClient(
    getClientEnv().NEXT_PUBLIC_SUPABASE_URL,
    requireEnv("SUPABASE_SERVICE_ROLE_KEY"),
    { auth: { persistSession: false, autoRefreshToken: false } },
  );
}

export type AdminClient = ReturnType<typeof createAdminClient>;
