import { beforeEach, describe, expect, it, vi } from "vitest";
import { z } from "zod";

const { query } = vi.hoisted(() => ({ query: vi.fn() }));
vi.mock("@/lib/server/bigquery", () => ({ query }));

import {
  getArticles,
  getIntentions,
  getRequetes,
  getScopedNotion,
  getSerp,
  getVolumes,
} from "./detail-repository";

let rows: unknown[];
beforeEach(() => {
  rows = [];
  query.mockReset();
  query.mockImplementation(
    async (_sql: string, _params: unknown, schema: z.ZodType) =>
      schema.array().parse(rows),
  );
});

describe("repository du détail", () => {
  it("limite la notion au périmètre de l'analyse", async () => {
    rows = [
      {
        notion_id: "n1",
        libelle: "Congé",
        definition_courte: null,
        score_confiance: 0.9,
      },
    ];
    expect(await getScopedNotion("n1")).toEqual(rows[0]);
    expect(query.mock.calls[0][0]).toContain("LEGITEXT000006072050");
    expect(query.mock.calls[0][1]).toEqual({ notion_id: "n1" });
    rows = [];
    expect(await getScopedNotion("n1")).toBeNull();
  });

  it("valide les identifiants Légifrance et les dates des versions", async () => {
    rows = [
      {
        article_id: "LEGIARTI000000000001",
        article_version_id: "LEGIARTI000000000002",
        numero: "L1",
        etat: "VIGUEUR",
        date_debut: "2020-01-01",
        date_fin: null,
        en_vigueur: true,
      },
    ];
    expect(await getArticles("n1")).toEqual(rows);
    expect(query.mock.calls[0][0]).toContain("en_vigueur DESC");
    rows = [{ ...(rows[0] as object), article_version_id: "../autre" }];
    await expect(getArticles("n1")).rejects.toThrow();
  });

  it.each([
    [
      "requêtes",
      getRequetes,
      { requete_id: "r1", texte: "congé", score_rattachement: 0.7 },
      { requete_id: "r1", texte: "congé", score_rattachement: 2 },
    ],
    [
      "volumes",
      getVolumes,
      { mois: "2026-01-01", volume: 12.5 },
      { mois: "2026-01-01", volume: -1 },
    ],
    [
      "intentions",
      getIntentions,
      { intention_type: null, nombre_requetes: 2 },
      { intention_type: "invalide", nombre_requetes: 2 },
    ],
    [
      "SERP",
      getSerp,
      {
        requete_id: "r1",
        texte: "congé",
        date_resultat: "2026-01-01",
        position: 1,
        domaine: "exemple.fr",
        url: null,
      },
      {
        requete_id: "r1",
        texte: "congé",
        date_resultat: "2026-01-01",
        position: 11,
        domaine: null,
        url: null,
      },
    ],
  ])(
    "valide les données %s et transmet le paramètre séparément",
    async (_name, operation, valid, invalid) => {
      rows = [valid];
      expect(await operation("n1")).toEqual(rows);
      expect(query.mock.calls[0][0]).toContain("@notion_id");
      expect(query.mock.calls[0][1]).toEqual({ notion_id: "n1" });
      rows = [invalid];
      await expect(operation("n1")).rejects.toThrow();
    },
  );
});
