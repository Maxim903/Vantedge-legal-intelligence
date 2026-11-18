import "server-only";
import neo4j, { type Driver } from "neo4j-driver";
import { z } from "zod";
import { requireEnv } from "@/lib/server/env";

const MAX_QUERY_DURATION_MS = 15_000;

let driver: Driver | undefined;

function getDriver(): Driver {
  driver ??= neo4j.driver(
    requireEnv("NEO4J_URI"),
    neo4j.auth.basic(requireEnv("NEO4J_USER"), requireEnv("NEO4J_PASSWORD")),
    {
      connectionAcquisitionTimeout: MAX_QUERY_DURATION_MS,
      connectionTimeout: MAX_QUERY_DURATION_MS,
      maxTransactionRetryTime: 0,
    },
  );
  return driver;
}

export async function query<T>(
  cypher: string,
  params: Record<string, unknown>,
  schema: z.ZodType<T>,
): Promise<T[]> {
  const statement = z
    .string()
    .refine((value) => value.trim().length > 0)
    .parse(cypher);
  const database = process.env.NEO4J_DATABASE;
  if (database !== undefined && !database.trim()) {
    throw new Error("NEO4J_DATABASE ne doit pas être vide.");
  }
  const session = getDriver().session({
    defaultAccessMode: neo4j.session.READ,
    ...(database === undefined ? {} : { database }),
  });
  let closing: Promise<void> | undefined;
  const closeSession = () => {
    closing ??= Promise.resolve().then(() => session.close());
    return closing;
  };
  let timer: ReturnType<typeof setTimeout> | undefined;
  const deadline = new Promise<never>((_, reject) => {
    timer = setTimeout(() => {
      reject(new Error("La requête Neo4j a dépassé le délai maximal."));
      void closeSession().catch((error: unknown) => {
        console.error("Fermeture de la session Neo4j impossible", error);
      });
    }, MAX_QUERY_DURATION_MS);
  });
  const operation = (async () => {
    let rows: T[];
    try {
      const result = await session.run(statement, params, {
        timeout: MAX_QUERY_DURATION_MS,
      });
      rows = schema
        .array()
        .parse(result.records.map((record) => record.toObject()));
    } catch (error) {
      try {
        await closeSession();
      } catch (closeError) {
        throw new AggregateError(
          [error, closeError],
          "La requête Neo4j et la fermeture de session ont échoué.",
        );
      }
      throw error;
    }
    await closeSession();
    return rows;
  })();
  try {
    return await Promise.race([operation, deadline]);
  } finally {
    if (timer !== undefined) clearTimeout(timer);
  }
}
