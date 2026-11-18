import { afterEach, describe, expect, it, vi } from "vitest";
import { getServerEnv, requireEnv } from "@/lib/server/env";

describe("requireEnv", () => {
  afterEach(() => {
    delete process.env.VIL_TEST_VAR;
  });

  it("retourne la valeur définie", () => {
    process.env.VIL_TEST_VAR = "valeur";
    expect(requireEnv("VIL_TEST_VAR")).toBe("valeur");
  });

  it("échoue si la variable est absente", () => {
    expect(() => requireEnv("VIL_TEST_VAR")).toThrow("VIL_TEST_VAR");
  });
});

describe("getServerEnv", () => {
  it("échoue si les variables serveur sont absentes", () => {
    vi.stubEnv("GCP_PROJECT_ID", "");
    expect(() => getServerEnv()).toThrow("GCP_PROJECT_ID");
    vi.unstubAllEnvs();
  });
});
