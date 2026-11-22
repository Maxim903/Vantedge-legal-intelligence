import "server-only";
import { BigQuery, type QueryResultsOptions } from "@google-cloud/bigquery";
import { z } from "zod";
import { requireEnv } from "@/lib/server/env";

const MAX_QUERY_DURATION_MS = 15_000;
const MAX_QUERY_ROWS = 1_000;
const DEFAULT_LOCATION = "europe-west9";
const datasetSchema = z.string().regex(/^[A-Za-z_][A-Za-z0-9_]{0,1023}$/);

type QueryParameterValue =
  | string
  | number
  | boolean
  | bigint
  | Date
  | Uint8Array
  | null
  | QueryParameterValue[]
  | { [key: string]: QueryParameterValue };

export type QueryParameters =
  QueryParameterValue[] | { [key: string]: QueryParameterValue };

let client: BigQuery | undefined;

function getLocation(): string {
  return process.env.BQ_LOCATION === undefined
    ? DEFAULT_LOCATION
    : requireEnv("BQ_LOCATION");
}

function getClient(): BigQuery {
  client ??= new BigQuery({
    projectId: requireEnv("GCP_PROJECT_ID"),
    location: getLocation(),
  });
  return client;
}

async function fetchRows(
  sql: string,
  params: QueryParameters,
): Promise<unknown[]> {
  const location = getLocation();
  const dataset = datasetSchema.parse(process.env.BQ_DATASET ?? "marts");
  const [job] = await getClient().createQueryJob({
    query: sql.replaceAll("`marts.", `\`${dataset}.`),
    params,
    location,
    jobTimeoutMs: MAX_QUERY_DURATION_MS,
    useLegacySql: false,
  });

  const rows: unknown[] = [];
  let options: QueryResultsOptions = {
    autoPaginate: false,
    maxResults: MAX_QUERY_ROWS + 1,
  };

  while (true) {
    const [page, nextPage] = await job.getQueryResults(options);
    rows.push(...page);
    if (rows.length > MAX_QUERY_ROWS) {
      throw new Error(`La requête BigQuery dépasse ${MAX_QUERY_ROWS} lignes.`);
    }
    if (!nextPage) {
      return rows;
    }
    options = {
      ...nextPage,
      autoPaginate: false,
      maxResults: MAX_QUERY_ROWS + 1 - rows.length,
    };
  }
}

/**
 * Exécute une requête SQL standard avec paramètres BigQuery et valide chaque ligne.
 * L'identité ADC de l'environnement d'exécution doit être `sa-app-reader`.
 */
export async function query<T>(
  sql: string,
  params: QueryParameters,
  schema: z.ZodType<T>,
): Promise<T[]> {
  const parsedSql = z
    .string()
    .refine((value) => value.trim().length > 0)
    .parse(sql);
  let timeout: ReturnType<typeof setTimeout> | undefined;
  const timeoutPromise = new Promise<never>((_, reject) => {
    timeout = setTimeout(
      () =>
        reject(new Error("La requête BigQuery a dépassé le délai maximal.")),
      MAX_QUERY_DURATION_MS,
    );
  });

  try {
    const rows = await Promise.race([
      fetchRows(parsedSql, params),
      timeoutPromise,
    ]);
    return schema.array().parse(rows);
  } finally {
    if (timeout) {
      clearTimeout(timeout);
    }
  }
}
