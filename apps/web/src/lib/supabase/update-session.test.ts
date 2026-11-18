import { NextRequest } from "next/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

const getUser = vi.fn();
let setAll: (
  cookies: { name: string; value: string; options?: object }[],
) => void;

vi.mock("@supabase/ssr", () => ({
  createServerClient: (
    _url: string,
    _key: string,
    options: { cookies: { setAll: typeof setAll } },
  ) => {
    setAll = options.cookies.setAll;
    return { auth: { getUser } };
  },
}));

import { updateSession } from "@/lib/supabase/update-session";

describe("updateSession", () => {
  beforeEach(() => {
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", "https://exemple.supabase.co");
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_ANON_KEY", "cle-anon");
    getUser.mockReset();
  });

  it("valide la session auprès de Supabase", async () => {
    getUser.mockResolvedValue({ data: { user: null } });
    await updateSession(new NextRequest("http://localhost:3000/"));
    expect(getUser).toHaveBeenCalledOnce();
  });

  it("recopie les cookies rafraîchis dans la réponse", async () => {
    getUser.mockImplementation(async () => {
      setAll([{ name: "sb-token", value: "nouveau" }]);
      return { data: { user: null } };
    });
    const response = await updateSession(
      new NextRequest("http://localhost:3000/"),
    );
    expect(response.cookies.get("sb-token")?.value).toBe("nouveau");
  });

  it("échoue si l'URL Supabase est absente", async () => {
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", "");
    await expect(
      updateSession(new NextRequest("http://localhost:3000/")),
    ).rejects.toThrow("NEXT_PUBLIC_SUPABASE_URL");
  });
});

describe("updateSession : protection de /app", () => {
  beforeEach(() => {
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", "https://exemple.supabase.co");
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_ANON_KEY", "cle-anon");
    getUser.mockReset();
  });

  it("redirige un anonyme vers /connexion en conservant la destination", async () => {
    getUser.mockResolvedValue({ data: { user: null } });
    const response = await updateSession(
      new NextRequest("http://localhost:3000/app/projets?x=1"),
    );
    expect(response.status).toBe(307);
    const location = new URL(response.headers.get("location") ?? "");
    expect(location.pathname).toBe("/connexion");
    expect(location.searchParams.get("redirect")).toBe("/app/projets?x=1");
  });

  it("laisse passer un utilisateur connecté", async () => {
    getUser.mockResolvedValue({ data: { user: { id: "u1" } } });
    const response = await updateSession(
      new NextRequest("http://localhost:3000/app"),
    );
    expect(response.headers.get("location")).toBeNull();
  });

  it("ne protège pas les pages publiques ni /application", async () => {
    getUser.mockResolvedValue({ data: { user: null } });
    for (const path of ["/connexion", "/application"]) {
      const response = await updateSession(
        new NextRequest(`http://localhost:3000${path}`),
      );
      expect(response.headers.get("location")).toBeNull();
    }
  });
});
