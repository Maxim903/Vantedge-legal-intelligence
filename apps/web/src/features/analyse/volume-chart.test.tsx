import { fireEvent, render, screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import type { ReactNode } from "react";

const { chartData } = vi.hoisted(() => ({ chartData: vi.fn() }));
vi.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: { children: ReactNode }) => (
    <div>{children}</div>
  ),
  LineChart: ({ data, children }: { data: unknown; children: ReactNode }) => {
    chartData(data);
    return <div>{children}</div>;
  },
  CartesianGrid: () => null,
  Line: () => null,
  Tooltip: () => null,
  XAxis: () => null,
  YAxis: () => null,
}));

import { VolumeChart } from "./volume-chart";

it("n'interpole pas les mois manquants et expose les valeurs en tableau", () => {
  render(
    <VolumeChart
      volumes={[
        { mois: "2026-01-01", volume: 12 },
        { mois: "2026-03-01", volume: 30 },
      ]}
    />,
  );
  expect(chartData).toHaveBeenCalledWith([
    { date: Date.parse("2026-01-01T00:00:00Z"), volume: 12 },
    { date: Date.parse("2026-02-01T00:00:00Z"), volume: null },
    { date: Date.parse("2026-03-01T00:00:00Z"), volume: 30 },
  ]);
  fireEvent.click(screen.getByText("Voir les données mensuelles"));
  const table = screen.getByRole("table", {
    name: "Volumes mensuels pondérés",
  });
  expect(table).toHaveTextContent("2026-01");
  expect(table).toHaveTextContent("2026-03");
});
