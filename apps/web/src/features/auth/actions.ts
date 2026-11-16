"use server";

import { headers } from "next/headers";
import { redirect } from "next/navigation";
import type { ZodError } from "zod";
import { createClient } from "@/lib/supabase/server";
import { authErrorMessage } from "./messages";
import {
  forgotPasswordSchema,
  safeRedirectPath,
  signInSchema,
  signUpSchema,
} from "./schemas";

export type AuthFormState = {
  error?: string;
  message?: string;
  fieldErrors?: Record<string, string[]>;
};

function formValues(formData: FormData): Record<string, unknown> {
  return Object.fromEntries(
    [...formData.entries()].filter(([, v]) => typeof v === "string"),
  );
}

function invalid(error: ZodError): AuthFormState {
  const fieldErrors: Record<string, string[]> = {};
  for (const issue of error.issues) {
    const key = String(issue.path[0] ?? "");
    (fieldErrors[key] ??= []).push(issue.message);
  }
  return { error: "Veuillez corriger les champs en erreur.", fieldErrors };
}

async function siteUrl(): Promise<string> {
  const h = await headers();
  const origin = h.get("origin");
  if (origin) return origin;
  const host = h.get("x-forwarded-host") ?? h.get("host");
  const proto = h.get("x-forwarded-proto") ?? "http";
  return `${proto}://${host}`;
}

export async function signIn(
  _prev: AuthFormState,
  formData: FormData,
): Promise<AuthFormState> {
  const parsed = signInSchema.safeParse(formValues(formData));
  if (!parsed.success) return invalid(parsed.error);

  const supabase = await createClient();
  const { error } = await supabase.auth.signInWithPassword(parsed.data);
  if (error) return { error: authErrorMessage(error) };

  redirect(safeRedirectPath(formData.get("redirect")));
}

export async function signUp(
  _prev: AuthFormState,
  formData: FormData,
): Promise<AuthFormState> {
  const parsed = signUpSchema.safeParse(formValues(formData));
  if (!parsed.success) return invalid(parsed.error);

  const { email, password, displayName } = parsed.data;
  const supabase = await createClient();
  const { data, error } = await supabase.auth.signUp({
    email,
    password,
    options: {
      data: displayName ? { display_name: displayName } : {},
      emailRedirectTo: `${await siteUrl()}/auth/callback`,
    },
  });
  if (error) return { error: authErrorMessage(error) };

  // Avec la confirmation par e-mail active, aucune session n'est ouverte.
  if (!data.session) {
    return {
      message:
        "Compte créé. Un e-mail de confirmation vient de vous être envoyé.",
    };
  }
  redirect("/app");
}

export async function requestPasswordReset(
  _prev: AuthFormState,
  formData: FormData,
): Promise<AuthFormState> {
  const parsed = forgotPasswordSchema.safeParse(formValues(formData));
  if (!parsed.success) return invalid(parsed.error);

  const supabase = await createClient();
  const { error } = await supabase.auth.resetPasswordForEmail(
    parsed.data.email,
    { redirectTo: `${await siteUrl()}/auth/callback` },
  );
  if (error) return { error: authErrorMessage(error) };

  // Même réponse que le compte existe ou non, pour ne pas révéler les adresses inscrites.
  return {
    message:
      "Si un compte existe avec cette adresse, un e-mail de réinitialisation vient d'être envoyé.",
  };
}

export async function signOut(): Promise<void> {
  const supabase = await createClient();
  await supabase.auth.signOut();
  redirect("/connexion");
}
