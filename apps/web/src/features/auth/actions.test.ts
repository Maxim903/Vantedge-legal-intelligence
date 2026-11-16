import { beforeEach, describe, expect, it, vi } from "vitest";

const auth = {
  signInWithPassword: vi.fn(),
  signUp: vi.fn(),
  resetPasswordForEmail: vi.fn(),
  signOut: vi.fn(),
};

vi.mock("@/lib/supabase/server", () => ({
  createClient: async () => ({ auth }),
}));
vi.mock("next/headers", () => ({
  headers: async () => new Headers({ origin: "https://app.exemple.fr" }),
}));
vi.mock("next/navigation", () => ({
  redirect: (url: string) => {
    throw new Error(`REDIRECT:${url}`);
  },
}));

import {
  requestPasswordReset,
  signIn,
  signOut,
  signUp,
} from "@/features/auth/actions";

function form(values: Record<string, string>) {
  const fd = new FormData();
  Object.entries(values).forEach(([k, v]) => fd.set(k, v));
  return fd;
}

const valid = {
  email: "a@exemple.fr",
  password: "mot-de-passe-long",
  confirmPassword: "mot-de-passe-long",
};

beforeEach(() => {
  Object.values(auth).forEach((m) => m.mockReset());
});

describe("signIn", () => {
  it("rejette les champs invalides sans appeler Supabase", async () => {
    const state = await signIn(
      {},
      form({ email: "pas-un-email", password: "" }),
    );
    expect(state.fieldErrors?.email).toEqual([
      "L'adresse e-mail n'est pas valide.",
    ]);
    expect(state.fieldErrors?.password).toBeDefined();
    expect(auth.signInWithPassword).not.toHaveBeenCalled();
  });

  it("traduit une erreur d'identifiants", async () => {
    auth.signInWithPassword.mockResolvedValue({
      error: { code: "invalid_credentials", status: 400 },
    });
    const state = await signIn({}, form(valid));
    expect(state.error).toBe("E-mail ou mot de passe incorrect.");
  });

  it("redirige vers /app après connexion", async () => {
    auth.signInWithPassword.mockResolvedValue({ error: null });
    await expect(signIn({}, form(valid))).rejects.toThrow("REDIRECT:/app");
  });

  it("refuse une redirection externe", async () => {
    auth.signInWithPassword.mockResolvedValue({ error: null });
    await expect(
      signIn({}, form({ ...valid, redirect: "https://evil.example" })),
    ).rejects.toThrow("REDIRECT:/app");
    await expect(
      signIn({}, form({ ...valid, redirect: "/app/projets" })),
    ).rejects.toThrow("REDIRECT:/app/projets");
  });
});

describe("signUp", () => {
  it("exige 10 caractères et deux mots de passe identiques", async () => {
    const court = await signUp(
      {},
      form({ ...valid, password: "court", confirmPassword: "court" }),
    );
    expect(court.fieldErrors?.password).toBeDefined();
    const diff = await signUp(
      {},
      form({ ...valid, confirmPassword: "autre-mot-de-passe" }),
    );
    expect(diff.fieldErrors?.confirmPassword).toEqual([
      "Les mots de passe ne correspondent pas.",
    ]);
    expect(auth.signUp).not.toHaveBeenCalled();
  });

  it("transmet le nom affiché et l'URL de retour", async () => {
    auth.signUp.mockResolvedValue({ data: { session: null }, error: null });
    const state = await signUp({}, form({ ...valid, displayName: "Alice" }));
    expect(auth.signUp).toHaveBeenCalledWith({
      email: "a@exemple.fr",
      password: "mot-de-passe-long",
      options: {
        data: { display_name: "Alice" },
        emailRedirectTo: "https://app.exemple.fr/auth/callback",
      },
    });
    expect(state.message).toContain("e-mail de confirmation");
  });

  it("signale un compte existant", async () => {
    auth.signUp.mockResolvedValue({
      data: { session: null },
      error: { code: "user_already_exists", status: 422 },
    });
    const state = await signUp({}, form(valid));
    expect(state.error).toContain("Un compte existe déjà");
  });

  it("redirige si une session est ouverte directement", async () => {
    auth.signUp.mockResolvedValue({ data: { session: {} }, error: null });
    await expect(signUp({}, form(valid))).rejects.toThrow("REDIRECT:/app");
  });
});

describe("requestPasswordReset", () => {
  it("valide l'adresse e-mail", async () => {
    const state = await requestPasswordReset({}, form({ email: "" }));
    expect(state.fieldErrors?.email).toBeDefined();
    expect(auth.resetPasswordForEmail).not.toHaveBeenCalled();
  });

  it("envoie le lien avec l'URL de retour", async () => {
    auth.resetPasswordForEmail.mockResolvedValue({ error: null });
    const state = await requestPasswordReset(
      {},
      form({ email: "a@exemple.fr" }),
    );
    expect(auth.resetPasswordForEmail).toHaveBeenCalledWith("a@exemple.fr", {
      redirectTo: "https://app.exemple.fr/auth/callback",
    });
    expect(state.message).toContain("Si un compte existe");
  });

  it("affiche un message générique pour une erreur inconnue", async () => {
    auth.resetPasswordForEmail.mockResolvedValue({ error: { status: 500 } });
    const state = await requestPasswordReset(
      {},
      form({ email: "a@exemple.fr" }),
    );
    expect(state.error).toBe("Une erreur est survenue. Veuillez réessayer.");
  });
});

describe("signOut", () => {
  it("ferme la session puis redirige vers /connexion", async () => {
    auth.signOut.mockResolvedValue({ error: null });
    await expect(signOut()).rejects.toThrow("REDIRECT:/connexion");
    expect(auth.signOut).toHaveBeenCalledOnce();
  });
});
