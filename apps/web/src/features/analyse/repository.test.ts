import { beforeEach, describe, expect, it, vi } from "vitest";
import { z } from "zod";

const { query } = vi.hoisted(() => ({ query: vi.fn() }));
vi.mock("@/lib/server/bigquery", () => ({ query }));

import {
  getGapScores,
  getNotionDetail,
  listAnalysis,
  listNotions,
  listSituations,
} from "./repository";

const notion = {
  notion_id: "notion-1",
  libelle: "Congé",
  definition_courte: null,
  score_confiance: 0.9,
};

const gapScore = {
  gap_score_id: "gap-1",
  notion_id: "notion-1",
  code_id: "code-1",
  livre_id: null,
  pays_langue_id: "fr-fr",
  date_calcul: "2026-01-01",
  version_score: "v1",
  indice_demande: 20,
  indice_saturation: 30,
  indice_importance_normative: 40,
  score_ecart: 14,
  criticite_semantique: 50,
  taille_cohorte: 12,
};

let rows: unknown[];

beforeEach(() => {
  rows = [];
  query.mockReset();
  query.mockImplementation(
    async (_sql: string, _params: unknown, schema: z.ZodType) =>
      schema.array().parse(rows),
  );
});

describe("listNotions", () => {
  it("filtre et trie via des paramètres et calcule l'offset de la page", async () => {
    rows = [notion];
    const filtre = "congé' OR TRUE --";
    await expect(
      listNotions({ tri: "desc", filtre, page: 2 }),
    ).resolves.toEqual([notion]);
    const [sql, params] = query.mock.calls[0];
    expect(sql).toContain("`marts.dim_notion`");
    expect(sql).toContain("@filtre");
    expect(sql).not.toContain(filtre);
    expect(params).toEqual({ tri: "desc", filtre, limite: 20, offset: 20 });
  });

  it("rejette une page invalide avant toute requête", async () => {
    await expect(
      listNotions({ tri: "asc", filtre: "", page: 0 }),
    ).rejects.toThrow();
    expect(query).not.toHaveBeenCalled();
  });

  it("rejette une ligne de notion invalide", async () => {
    rows = [{ ...notion, score_confiance: 2 }];
    await expect(
      listNotions({ tri: "asc", filtre: "", page: 1 }),
    ).rejects.toThrow();
  });
});

describe("getNotionDetail", () => {
  it("retourne la notion demandée ou null si elle n'existe pas", async () => {
    rows = [notion];
    await expect(getNotionDetail("notion-1")).resolves.toEqual(notion);
    expect(query.mock.calls[0][0]).toContain("@notion_id");
    expect(query.mock.calls[0][1]).toEqual({ notion_id: "notion-1" });
    rows = [];
    await expect(getNotionDetail("absente")).resolves.toBeNull();
  });

  it("rejette les identifiants vides et les doublons en base", async () => {
    await expect(getNotionDetail(" ")).rejects.toThrow();
    expect(query).not.toHaveBeenCalled();
    rows = [notion, notion];
    await expect(getNotionDetail("notion-1")).rejects.toThrow(
      "Plusieurs notions",
    );
  });

  it("rejette une ligne de détail invalide", async () => {
    rows = [{ ...notion, definition_courte: 123 }];
    await expect(getNotionDetail("notion-1")).rejects.toThrow();
  });
});

describe("getGapScores", () => {
  it("retourne les scores avec leur périmètre et transmet les identifiants séparément", async () => {
    rows = [
      gapScore,
      { ...gapScore, gap_score_id: "gap-2", code_id: "code-2" },
    ];
    await expect(getGapScores(["notion-1", "notion-2"])).resolves.toEqual(rows);
    expect(query.mock.calls[0][0]).toContain("UNNEST(@notion_ids)");
    expect(query.mock.calls[0][1]).toEqual({
      notion_ids: ["notion-1", "notion-2"],
    });
  });

  it("ne lance pas de requête pour une liste vide et rejette un identifiant vide", async () => {
    await expect(getGapScores([])).resolves.toEqual([]);
    await expect(getGapScores([""])).rejects.toThrow();
    expect(query).not.toHaveBeenCalled();
  });

  it("rejette un score mal formé", async () => {
    rows = [{ ...gapScore, date_calcul: "invalide" }];
    await expect(getGapScores(["notion-1"])).rejects.toThrow();
  });
});

describe("liste d'analyse", () => {
  it("filtre et trie avant pagination et signale une page suivante", async () => {
    rows = Array.from({ length: 21 }, (_, index) => ({
      ...gapScore,
      gap_score_id: `gap-${index}`,
      notion_libelle: "Congé",
    }));
    const result = await listAnalysis({
      tri: "ecart",
      ordre: "desc",
      situation: "situation-1",
      page: 2,
    });
    expect(result.rows).toHaveLength(20);
    expect(result.hasNextPage).toBe(true);
    const [sql, params] = query.mock.calls[0];
    expect(sql).toContain("@situation");
    expect(sql).toContain("LEGITEXT000006072050");
    expect(sql).toContain("score.livre_id IS NULL");
    expect(params).toEqual({
      tri: "ecart",
      ordre: "desc",
      situation: "situation-1",
      limite: 21,
      offset: 20,
    });
  });

  it("rejette les paramètres et les résultats incorrects", async () => {
    await expect(
      listAnalysis({ tri: "ecart", ordre: "asc", situation: "", page: 0 }),
    ).rejects.toThrow();
    expect(query).not.toHaveBeenCalled();
    rows = [{ ...gapScore, notion_libelle: "Congé", score_ecart: 101 }];
    await expect(
      listAnalysis({ tri: "ecart", ordre: "asc", situation: "", page: 1 }),
    ).rejects.toThrow();
  });

  it("charge les situations du périmètre et valide leurs champs", async () => {
    rows = [{ situation_id: "s1", libelle: "Congé" }];
    await expect(listSituations()).resolves.toEqual(rows);
    expect(query.mock.calls[0][0]).toContain("`marts.pont_notion_situation`");
    expect(query.mock.calls[0][1]).toEqual({});
    rows = [{ situation_id: "", libelle: "Congé" }];
    await expect(listSituations()).rejects.toThrow();
  });
});
