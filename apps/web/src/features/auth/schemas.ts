import { z } from "zod";

const email = z
  .string()
  .trim()
  .min(1, "L'adresse e-mail est obligatoire.")
  .pipe(z.email("L'adresse e-mail n'est pas valide."));

export const signInSchema = z.object({
  email,
  password: z.string().min(1, "Le mot de passe est obligatoire."),
});

export const signUpSchema = z
  .object({
    displayName: z
      .string()
      .trim()
      .max(80, "Le nom ne doit pas dépasser 80 caractères.")
      .optional(),
    email,
    password: z
      .string()
      .min(10, "Le mot de passe doit contenir au moins 10 caractères.")
      .max(128, "Le mot de passe ne doit pas dépasser 128 caractères."),
    confirmPassword: z.string(),
  })
  .refine((d) => d.password === d.confirmPassword, {
    path: ["confirmPassword"],
    message: "Les mots de passe ne correspondent pas.",
  });

export const forgotPasswordSchema = z.object({ email });

/** N'accepte que des chemins internes, pour éviter une redirection ouverte. */
export function safeRedirectPath(value: unknown, fallback = "/app"): string {
  if (
    typeof value === "string" &&
    value.startsWith("/") &&
    !value.startsWith("//") &&
    !value.includes("\\")
  ) {
    return value;
  }
  return fallback;
}
