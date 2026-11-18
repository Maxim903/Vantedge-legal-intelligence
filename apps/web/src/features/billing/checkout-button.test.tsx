import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";
import { CheckoutButton } from "./checkout-button";

afterEach(() => vi.unstubAllGlobals());

it("demande le plan pro et affiche une erreur de paiement accessible", async () => {
  const fetchMock = vi.fn().mockResolvedValue({
    ok: false,
    json: async () => ({ error: "Paiement indisponible." }),
  });
  vi.stubGlobal("fetch", fetchMock);
  render(<CheckoutButton />);
  await userEvent.click(
    screen.getByRole("button", { name: "Souscrire au plan pro" }),
  );
  expect(fetchMock).toHaveBeenCalledWith("/api/stripe/checkout", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ plan: "pro" }),
  });
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Paiement indisponible.",
  );
});
