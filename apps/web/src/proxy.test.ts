import { NextRequest, NextResponse } from "next/server";
import { beforeEach, expect, it, vi } from "vitest";

const updateSession = vi.hoisted(() => vi.fn());
vi.mock("@/lib/supabase/update-session", () => ({ updateSession }));
import { proxy } from "./proxy";

beforeEach(() => updateSession.mockReset());

it("sert les pages légales sans appeler Supabase", async () => {
  for (const path of ["/mentions-legales", "/cgu", "/confidentialite"]) {
    const response = await proxy(
      new NextRequest(`https://example.test${path}`),
    );
    expect(response.status).toBe(200);
  }
  expect(updateSession).not.toHaveBeenCalled();
});

it("conserve la protection des autres routes", async () => {
  updateSession.mockResolvedValue(NextResponse.next());
  const request = new NextRequest("https://example.test/app");
  await proxy(request);
  expect(updateSession).toHaveBeenCalledWith(request);
});
