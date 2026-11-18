import neo4j from "neo4j-driver";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { z } from "zod";

const { query } = vi.hoisted(() => ({ query: vi.fn() }));
vi.mock("@/lib/server/neo4j", () => ({ query }));

import {
  getCheminsNotionArticles,
  getClustersSituations,
  getNotionsConnectees,
  getNotionsVoisines,
} from "./repository";

let rows: unknown[];

beforeEach(() => {
  rows = [];
  query.mockReset();
  query.mockImplementation(
    async (_cypher: string, _params: unknown, schema: z.ZodType) =>
      schema.array().parse(rows),
  );
});

describe("repository graphe", () => {
  it("charge les notions voisines avec paramètres et entiers Neo4j", async () => {
    rows = [
      {
        notion_id: "n2",
        libelle: "Congé",
        nombre_articles_communs: neo4j.int(2),
        articles_communs: [{ article_id: "a1", numero: "1" }],
      },
    ];
    const notionId = "n1' MATCH (n) DETACH DELETE n //";
    await expect(getNotionsVoisines(notionId)).resolves.toEqual([
      {
        notion_id: "n2",
        libelle: "Congé",
        nombre_articles_communs: 2,
        articles_communs: [{ article_id: "a1", numero: "1" }],
      },
    ]);
    const [cypher, params] = query.mock.calls[0];
    expect(cypher).toContain("$notion_id");
    expect(cypher).not.toContain(notionId);
    expect(params).toEqual({ notion_id: notionId });
  });

  it("transmet la limite comme entier Neo4j et vérifie le degré", async () => {
    rows = [{ notion_id: "n1", libelle: "Congé", degre: neo4j.int(5) }];
    await expect(getNotionsConnectees(10)).resolves.toEqual([
      { notion_id: "n1", libelle: "Congé", degre: 5 },
    ]);
    expect(query.mock.calls[0][0]).toContain("LIMIT $limite");
    expect(query.mock.calls[0][1].limite.equals(neo4j.int(10))).toBe(true);
    await expect(getNotionsConnectees(-1)).rejects.toThrow();
    expect(query).toHaveBeenCalledTimes(1);
  });

  it("retourne les situations et leurs notions sous forme de données typées", async () => {
    rows = [
      {
        situation_id: "s1",
        libelle: "Vie",
        nombre_notions: neo4j.int(1),
        notions: [{ notion_id: "n1", libelle: "Congé" }],
      },
    ];
    await expect(getClustersSituations()).resolves.toEqual([
      {
        situation_id: "s1",
        libelle: "Vie",
        nombre_notions: 1,
        notions: [{ notion_id: "n1", libelle: "Congé" }],
      },
    ]);
    expect(query.mock.calls[0][1]).toEqual({});
  });

  it("convertit un chemin Neo4j en objets sérialisables", async () => {
    const notion = new neo4j.types.Node(neo4j.int(1), ["Notion"], {
      notion_id: "n1",
    });
    const article = new neo4j.types.Node(neo4j.int(2), ["Article"], {
      article_id: "a1",
      numero: "1",
    });
    const cible = new neo4j.types.Node(neo4j.int(3), ["Article"], {
      article_id: "a2",
      numero: "2",
    });
    const fondement = new neo4j.types.Relationship(
      neo4j.int(1),
      neo4j.int(1),
      neo4j.int(2),
      "SE_FONDE_SUR",
      {},
    );
    const renvoi = new neo4j.types.Relationship(
      neo4j.int(2),
      neo4j.int(2),
      neo4j.int(3),
      "RENVOIE_A",
      {},
    );
    const path = new neo4j.types.Path(notion, cible, [
      new neo4j.types.PathSegment(notion, fondement, article),
      new neo4j.types.PathSegment(article, renvoi, cible),
    ]);
    rows = [
      {
        article_id: "a2",
        numero: "2",
        nombre_liens_normatifs: neo4j.int(1),
        chemin: path,
      },
    ];
    await expect(getCheminsNotionArticles("n1")).resolves.toEqual([
      {
        article_id: "a2",
        numero: "2",
        nombre_liens_normatifs: 1,
        chemin: {
          notion_id: "n1",
          articles: [
            { article_id: "a1", numero: "1" },
            { article_id: "a2", numero: "2" },
          ],
          relations: ["SE_FONDE_SUR", "RENVOIE_A"],
        },
      },
    ]);
    expect(query.mock.calls[0][1]).toEqual({ notion_id: "n1" });
  });

  it("rejette les entrées invalides et les résultats incorrects", async () => {
    await expect(getNotionsVoisines(" ")).rejects.toThrow();
    await expect(getCheminsNotionArticles(" ")).rejects.toThrow();
    expect(query).not.toHaveBeenCalled();
    rows = [
      { notion_id: "n1", libelle: "x", degre: neo4j.int("9007199254740992") },
    ];
    await expect(getNotionsConnectees(1)).rejects.toThrow("hors plage sûre");
    rows = [
      {
        article_id: "a1",
        numero: "1",
        nombre_liens_normatifs: neo4j.int(0),
        chemin: {},
      },
    ];
    await expect(getCheminsNotionArticles("n1")).rejects.toThrow();
  });

  it("rejette les lignes mal formées et propage les erreurs du client", async () => {
    rows = [
      {
        notion_id: "n2",
        libelle: "x",
        nombre_articles_communs: neo4j.int(1),
        articles_communs: [{}],
      },
    ];
    await expect(getNotionsVoisines("n1")).rejects.toThrow();
    rows = [
      {
        situation_id: "s1",
        libelle: "x",
        nombre_notions: neo4j.int(1),
        notions: [{}],
      },
    ];
    await expect(getClustersSituations()).rejects.toThrow();
    query.mockRejectedValueOnce(new Error("Neo4j indisponible"));
    await expect(getClustersSituations()).rejects.toThrow("Neo4j indisponible");
  });
});
