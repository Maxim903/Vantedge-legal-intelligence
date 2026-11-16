import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";
import { PortalButton } from "./portal-button";

afterEach(() => vi.unstubAllGlobals());

it("affiche une erreur accessible lorsque le portail ne peut pas être ouvert", async () => {
  const fetchMock = vi.fn().mockResolvedValue({
    ok: false,
    json: async () => ({ error: "Aucun abonnement trouvé." }),
  });
  vi.stubGlobal("fetch", fetchMock);
  render(<PortalButton />);
  await userEvent.click(
    screen.getByRole("button", { name: "Gérer mon abonnement" }),
  );
  expect(fetchMock).toHaveBeenCalledWith("/api/stripe/portal", {
    method: "POST",
  });
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Aucun abonnement trouvé.",
  );
});
