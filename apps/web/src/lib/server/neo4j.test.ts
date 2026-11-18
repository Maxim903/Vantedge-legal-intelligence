import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { z } from "zod";

const mocks = vi.hoisted(() => ({
  driver: vi.fn(),
  basic: vi.fn(),
  session: vi.fn(),
  run: vi.fn(),
  close: vi.fn(),
}));

vi.mock("neo4j-driver", () => ({
  default: {
    driver: mocks.driver,
    auth: { basic: mocks.basic },
    session: { READ: "READ" },
  },
}));

let query: typeof import("./neo4j").query;
const schema = z.object({ id: z.string() });

beforeEach(async () => {
  vi.resetModules();
  vi.resetAllMocks();
  vi.stubEnv("NEO4J_URI", "bolt://localhost:7687");
  vi.stubEnv("NEO4J_USER", "reader");
  vi.stubEnv("NEO4J_PASSWORD", "test-password");
  vi.stubEnv("NEO4J_DATABASE", "neo4j");
  mocks.basic.mockReturnValue({ scheme: "basic" });
  mocks.driver.mockReturnValue({ session: mocks.session });
  mocks.session.mockReturnValue({ run: mocks.run, close: mocks.close });
  mocks.close.mockResolvedValue(undefined);
  mocks.run.mockResolvedValue({
    records: [{ toObject: () => ({ id: "n1" }) }],
  });
  ({ query } = await import("./neo4j"));
});

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllEnvs();
  vi.restoreAllMocks();
});

describe("query Neo4j", () => {
  it("utilise une session en lecture et transmet les paramètres séparément", async () => {
    const cypher = "MATCH (n:Notion {notion_id: $id}) RETURN n.notion_id AS id";
    const params = { id: "n1' MATCH (n) DETACH DELETE n //" };
    await expect(query(cypher, params, schema)).resolves.toEqual([
      { id: "n1" },
    ]);
    expect(mocks.basic).toHaveBeenCalledWith("reader", "test-password");
    expect(mocks.driver).toHaveBeenCalledWith(
      "bolt://localhost:7687",
      { scheme: "basic" },
      {
        connectionAcquisitionTimeout: 15_000,
        connectionTimeout: 15_000,
        maxTransactionRetryTime: 0,
      },
    );
    expect(mocks.session).toHaveBeenCalledWith({
      defaultAccessMode: "READ",
      database: "neo4j",
    });
    expect(mocks.run).toHaveBeenCalledWith(cypher, params, { timeout: 15_000 });
    expect(mocks.close).toHaveBeenCalledTimes(1);
  });

  it("réutilise le pilote et ouvre une session distincte par requête", async () => {
    await Promise.all([
      query("RETURN $id", { id: "a" }, schema),
      query("RETURN $id", { id: "b" }, schema),
    ]);
    expect(mocks.driver).toHaveBeenCalledTimes(1);
    expect(mocks.session).toHaveBeenCalledTimes(2);
    expect(mocks.close).toHaveBeenCalledTimes(2);
  });

  it("ferme la session et propage les erreurs de requête ou de validation", async () => {
    mocks.run.mockRejectedValueOnce(new Error("Neo4j indisponible"));
    await expect(query("RETURN 1", {}, schema)).rejects.toThrow(
      "Neo4j indisponible",
    );
    mocks.run.mockResolvedValueOnce({
      records: [{ toObject: () => ({ id: 42 }) }],
    });
    await expect(query("RETURN 1", {}, schema)).rejects.toThrow();
    expect(mocks.close).toHaveBeenCalledTimes(2);
  });

  it("ne masque pas une erreur de fermeture ni la combinaison de deux erreurs", async () => {
    mocks.close.mockRejectedValueOnce(new Error("fermeture impossible"));
    await expect(query("RETURN 1", {}, schema)).rejects.toThrow(
      "fermeture impossible",
    );
    mocks.run.mockRejectedValueOnce(new Error("requête impossible"));
    mocks.close.mockRejectedValueOnce(new Error("fermeture impossible"));
    const error = await query("RETURN 1", {}, schema).catch(
      (cause: unknown) => cause,
    );
    if (!(error instanceof AggregateError))
      throw new Error("AggregateError attendu");
    expect(error.errors).toEqual([
      expect.objectContaining({ message: "requête impossible" }),
      expect.objectContaining({ message: "fermeture impossible" }),
    ]);
  });

  it("respecte le délai même si la requête et la fermeture restent bloquées", async () => {
    vi.useFakeTimers();
    mocks.run.mockReturnValue(new Promise(() => {}));
    mocks.close.mockReturnValue(new Promise(() => {}));
    const result = query("RETURN 1", {}, schema);
    const rejection = expect(result).rejects.toThrow("délai maximal");
    await vi.advanceTimersByTimeAsync(15_000);
    await rejection;
    expect(mocks.close).toHaveBeenCalledTimes(1);
  });

  it("respecte le délai si seule la fermeture reste bloquée", async () => {
    vi.useFakeTimers();
    mocks.close.mockReturnValue(new Promise(() => {}));
    const result = query("RETURN 1", {}, schema);
    const rejection = expect(result).rejects.toThrow("délai maximal");
    await vi.advanceTimersByTimeAsync(15_000);
    await rejection;
    expect(mocks.close).toHaveBeenCalledTimes(1);
  });

  it("signale une erreur tardive de fermeture après expiration", async () => {
    vi.useFakeTimers();
    const log = vi.spyOn(console, "error").mockImplementation(() => {});
    mocks.run.mockReturnValue(new Promise(() => {}));
    mocks.close.mockRejectedValue(new Error("échec de fermeture"));
    const result = query("RETURN 1", {}, schema);
    const rejection = expect(result).rejects.toThrow("délai maximal");
    await vi.advanceTimersByTimeAsync(15_000);
    await rejection;
    expect(log).toHaveBeenCalledWith(
      "Fermeture de la session Neo4j impossible",
      expect.any(Error),
    );
  });

  it("rejette une requête vide et une base explicitement vide", async () => {
    await expect(query(" ", {}, schema)).rejects.toThrow();
    vi.stubEnv("NEO4J_DATABASE", " ");
    await expect(query("RETURN 1", {}, schema)).rejects.toThrow(
      "NEO4J_DATABASE",
    );
    expect(mocks.driver).not.toHaveBeenCalled();
  });
});
