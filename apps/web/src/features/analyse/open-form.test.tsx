import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";

const { openAnalysis } = vi.hoisted(() => ({ openAnalysis: vi.fn() }));
vi.mock("./open-action", () => ({ openAnalysis }));
import { OpenAnalysisForm } from "./open-form";

it("invite à passer au plan supérieur après un refus de quota", async () => {
  openAnalysis.mockResolvedValue({
    error: "Votre quota d’analyses est épuisé.",
    upgrade: true,
  });
  const user = userEvent.setup();
  render(
    <OpenAnalysisForm notionId="n1" projects={[{ id: "p1", nom: "Projet" }]} />,
  );
  await user.selectOptions(screen.getByLabelText("Projet"), "p1");
  await user.click(screen.getByRole("button", { name: "Ouvrir l’analyse" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("quota");
  expect(
    screen.getByRole("link", { name: "Passer à un plan supérieur" }),
  ).toHaveAttribute("href", "/app/compte/abonnement");
  const submitted = openAnalysis.mock.calls[0][1] as FormData;
  expect(submitted.get("project_id")).toBe("p1");
  expect(submitted.get("notion_id")).toBe("n1");
});
