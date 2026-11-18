import "server-only";
import { parseServerEnv, type ServerEnv } from "@/lib/env";

/** Lit une variable d'environnement obligatoire (code serveur uniquement). */
export function requireEnv(name: string): string {
  const value = process.env[name];
  if (!value) {
    throw new Error(`Variable d'environnement manquante : ${name}`);
  }
  return value;
}

/** Variables serveur validées par `serverEnvSchema` (secrets inclus). */
export function getServerEnv(): ServerEnv {
  return parseServerEnv(process.env);
}
