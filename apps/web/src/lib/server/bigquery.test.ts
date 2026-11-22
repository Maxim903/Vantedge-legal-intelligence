import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { z } from "zod";

const { bigQueryConstructor, createQueryJob, getQueryResults } = vi.hoisted(
  () => ({
    bigQueryConstructor: vi.fn(),
    createQueryJob: vi.fn(),
    getQueryResults: vi.fn(),
  }),
);

vi.mock("@google-cloud/bigquery", () => ({
  BigQuery: bigQueryConstructor,
}));

import { query } from "@/lib/server/bigquery";

const rowSchema = z.object({ id: z.number() });

beforeEach(() => {
  vi.resetAllMocks();
  vi.stubEnv("GCP_PROJECT_ID", "test-project");
  vi.stubEnv("BQ_LOCATION", "europe-west1");
  vi.stubEnv("BQ_DATASET", undefined);
  bigQueryConstructor.mockImplementation(function BigQueryMock() {
    return { createQueryJob };
  });
  createQueryJob.mockResolvedValue([{ getQueryResults }]);
  getQueryResults.mockResolvedValue([[{ id: 1 }], null]);
});

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllEnvs();
});

describe("query BigQuery", () => {
  it("transmet le SQL sans interpolation et passe les paramètres séparément", async () => {
    const sql = "SELECT id FROM `test-project.marts.articles` WHERE id = @id";
    const params = { id: 42 };

    await expect(query(sql, params, rowSchema)).resolves.toEqual([{ id: 1 }]);

    expect(bigQueryConstructor).toHaveBeenCalledWith({
      projectId: "test-project",
      location: "europe-west1",
    });
    expect(createQueryJob).toHaveBeenCalledWith({
      query: sql,
      params,
      location: "europe-west1",
      jobTimeoutMs: 15_000,
      useLegacySql: false,
    });
    expect(getQueryResults).toHaveBeenCalledWith({
      autoPaginate: false,
      maxResults: 1_001,
    });
  });

  it("rejette les lignes qui ne correspondent pas au schéma Zod", async () => {
    getQueryResults.mockResolvedValue([[{ id: "invalide" }], null]);

    await expect(query("SELECT id", {}, rowSchema)).rejects.toThrow();
  });

  it("utilise le dataset configuré pour les tables marts", async () => {
    vi.stubEnv("BQ_DATASET", "marts_e2e");
    await query("SELECT * FROM `marts.dim_notion`", {}, rowSchema);
    expect(createQueryJob).toHaveBeenCalledWith(
      expect.objectContaining({ query: "SELECT * FROM `marts_e2e.dim_notion`" }),
    );
  });

  it("rejette un identifiant de dataset invalide avant toute requête", async () => {
    vi.stubEnv("BQ_DATASET", "marts` WHERE true; --");
    await expect(query("SELECT * FROM `marts.dim_notion`", {}, rowSchema)).rejects.toThrow();
    expect(createQueryJob).not.toHaveBeenCalled();
  });

  it("rejette les résultats au-delà de la limite sans charger les pages suivantes", async () => {
    getQueryResults.mockResolvedValue([
      Array.from({ length: 1_001 }, (_, id) => ({ id })),
      { pageToken: "next" },
    ]);

    await expect(query("SELECT id", {}, rowSchema)).rejects.toThrow(
      "dépasse 1000 lignes",
    );
    expect(getQueryResults).toHaveBeenCalledTimes(1);
  });

  it("applique la limite de lignes pendant la pagination", async () => {
    getQueryResults
      .mockResolvedValueOnce([
        Array.from({ length: 1_000 }, (_, id) => ({ id })),
        { pageToken: "next" },
      ])
      .mockResolvedValueOnce([[{ id: 1_000 }], null]);

    await expect(query("SELECT id", {}, rowSchema)).rejects.toThrow(
      "dépasse 1000 lignes",
    );
    expect(getQueryResults).toHaveBeenNthCalledWith(2, {
      pageToken: "next",
      autoPaginate: false,
      maxResults: 1,
    });
  });

  it("rejette lorsque l'exécution dépasse le délai maximal", async () => {
    vi.useFakeTimers();
    createQueryJob.mockReturnValue(new Promise(() => {}));

    const result = query("SELECT id", {}, rowSchema);
    const rejection = expect(result).rejects.toThrow("délai maximal");
    await vi.advanceTimersByTimeAsync(15_000);

    await rejection;
  });
});
