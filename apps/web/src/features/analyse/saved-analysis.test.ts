import { createClient } from "@supabase/supabase-js";
import { describe, expect, it, vi } from "vitest";
import { hasSavedAnalysis } from "./saved-analysis";

describe("analyse enregistrée", () => {
  it("n'autorise que les analyses vérifiées du projet et de l'utilisateur", async () => {
    const fetch = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify([{ id: "a" }]), { status: 200 }),
      )
      .mockResolvedValueOnce(new Response("[]", { status: 200 }))
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ message: "erreur" }), { status: 500 }),
      );
    const client = createClient("https://example.test", "test-key", {
      global: { fetch },
      auth: { persistSession: false },
    });
    expect(await hasSavedAnalysis(client, "u1", "p1", "n1")).toBe(true);
    const url = new URL(String(fetch.mock.calls[0][0]));
    expect(url.searchParams.get("user_id")).toBe("eq.u1");
    expect(url.searchParams.get("project_id")).toBe("eq.p1");
    expect(url.searchParams.get("quota_verifie")).toBe("eq.true");
    expect(url.searchParams.get("parametres")).toBe('cs.{"notion_id":"n1"}');
    expect(await hasSavedAnalysis(client, "u1", "p1", "n1")).toBe(false);
    await expect(hasSavedAnalysis(client, "u1", "p1", "n1")).rejects.toThrow();
  });
});
