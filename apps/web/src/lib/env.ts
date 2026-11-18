import { z } from "zod";

/**
 * Schémas des variables d'environnement. Ce fichier ne lit jamais `process.env` pour
 * les secrets : le schéma serveur est appliqué uniquement par `lib/server/env.ts`.
 */

const nonEmpty = z.string().trim().min(1);

export const serverEnvSchema = z.object({
  GCP_PROJECT_ID: nonEmpty,
  BQ_LOCATION: nonEmpty.default("europe-west9"),
  NEO4J_URI: z.string().trim().min(1),
  NEO4J_USER: nonEmpty,
  NEO4J_PASSWORD: nonEmpty,
  SUPABASE_SERVICE_ROLE_KEY: nonEmpty,
});

export const clientEnvSchema = z.object({
  NEXT_PUBLIC_SUPABASE_URL: z.url(),
  NEXT_PUBLIC_SUPABASE_ANON_KEY: nonEmpty,
});

export type ServerEnv = z.infer<typeof serverEnvSchema>;
export type ClientEnv = z.infer<typeof clientEnvSchema>;

function formatIssues(error: z.ZodError): string {
  return error.issues
    .map((issue) => `${issue.path.join(".")} : ${issue.message}`)
    .join("; ");
}

export function parseServerEnv(
  source: Record<string, string | undefined>,
): ServerEnv {
  const result = serverEnvSchema.safeParse(source);
  if (!result.success) {
    throw new Error(
      `Variables serveur invalides : ${formatIssues(result.error)}`,
    );
  }
  return result.data;
}

export function parseClientEnv(
  source: Record<string, string | undefined>,
): ClientEnv {
  const result = clientEnvSchema.safeParse(source);
  if (!result.success) {
    throw new Error(
      `Variables client invalides : ${formatIssues(result.error)}`,
    );
  }
  return result.data;
}

/**
 * Next.js n'injecte les NEXT_PUBLIC_* dans le bundle client que pour les accès
 * littéraux `process.env.NEXT_PUBLIC_X` : un `process.env` complet serait vide.
 */
export function getClientEnv(): ClientEnv {
  return parseClientEnv({
    NEXT_PUBLIC_SUPABASE_URL: process.env.NEXT_PUBLIC_SUPABASE_URL,
    NEXT_PUBLIC_SUPABASE_ANON_KEY: process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY,
  });
}
