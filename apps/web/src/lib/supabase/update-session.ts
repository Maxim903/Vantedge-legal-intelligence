import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";
import { getClientEnv } from "@/lib/env";

/**
 * Rafraîchit la session Supabase et recopie les cookies mis à jour dans la requête
 * (pour les composants serveur) et dans la réponse (pour le navigateur).
 */
export async function updateSession(request: NextRequest) {
  let response = NextResponse.next({ request });
  const env = getClientEnv();

  const supabase = createServerClient(
    env.NEXT_PUBLIC_SUPABASE_URL,
    env.NEXT_PUBLIC_SUPABASE_ANON_KEY,
    {
      cookies: {
        getAll: () => request.cookies.getAll(),
        setAll: (cookiesToSet) => {
          cookiesToSet.forEach(({ name, value }) =>
            request.cookies.set(name, value),
          );
          response = NextResponse.next({ request });
          cookiesToSet.forEach(({ name, value, options }) =>
            response.cookies.set(name, value, options),
          );
        },
      },
    },
  );

  // getUser() valide le jeton auprès de Supabase ; getSession() ne le ferait pas.
  const { data } = await supabase.auth.getUser();

  const { pathname } = request.nextUrl;
  const protegee = pathname === "/app" || pathname.startsWith("/app/");
  if (protegee && !data?.user) {
    const url = request.nextUrl.clone();
    url.pathname = "/connexion";
    url.search = `?redirect=${encodeURIComponent(pathname + request.nextUrl.search)}`;
    const redirection = NextResponse.redirect(url);
    // Conserve les cookies de session éventuellement rafraîchis.
    response.cookies.getAll().forEach((c) => redirection.cookies.set(c));
    return redirection;
  }

  return response;
}
