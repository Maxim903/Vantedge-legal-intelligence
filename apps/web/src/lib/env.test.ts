import { describe, expect, it } from "vitest";
import { parseClientEnv, parseServerEnv } from "@/lib/env";

const serveurValide = {
  GCP_PROJECT_ID: "projet",
  NEO4J_URI: "neo4j+s://exemple.databases.neo4j.io",
  NEO4J_USER: "neo4j",
  NEO4J_PASSWORD: "secret",
  SUPABASE_SERVICE_ROLE_KEY: "cle-service",
};

const clientValide = {
  NEXT_PUBLIC_SUPABASE_URL: "https://exemple.supabase.co",
  NEXT_PUBLIC_SUPABASE_ANON_KEY: "cle-anon",
};

describe("parseServerEnv", () => {
  it("accepte une configuration complète et applique la localisation par défaut", () => {
    expect(parseServerEnv(serveurValide).BQ_LOCATION).toBe("europe-west9");
  });

  it.each(Object.keys(serveurValide))("échoue si %s est absente", (nom) => {
    const source: Record<string, string | undefined> = { ...serveurValide };
    delete source[nom];
    expect(() => parseServerEnv(source)).toThrow(nom);
  });

  it("échoue si une variable est vide", () => {
    expect(() =>
      parseServerEnv({ ...serveurValide, NEO4J_PASSWORD: "  " }),
    ).toThrow("NEO4J_PASSWORD");
  });
});

describe("parseClientEnv", () => {
  it("accepte une configuration complète", () => {
    expect(parseClientEnv(clientValide)).toEqual(clientValide);
  });

  it.each(Object.keys(clientValide))("échoue si %s est absente", (nom) => {
    const source: Record<string, string | undefined> = { ...clientValide };
    delete source[nom];
    expect(() => parseClientEnv(source)).toThrow(nom);
  });

  it("échoue si l'URL est invalide", () => {
    expect(() =>
      parseClientEnv({
        ...clientValide,
        NEXT_PUBLIC_SUPABASE_URL: "pas-une-url",
      }),
    ).toThrow("NEXT_PUBLIC_SUPABASE_URL");
  });

  it("ignore les secrets serveur", () => {
    expect(parseClientEnv({ ...clientValide, ...serveurValide })).toEqual(
      clientValide,
    );
  });
});
