"use client";

import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { VolumeMensuel } from "./detail-repository";

function timestamp(mois: string): number {
  return Date.parse(`${mois}T00:00:00Z`);
}

function graphData(volumes: VolumeMensuel[]) {
  return volumes.flatMap((item, index) => {
    const date = new Date(timestamp(item.mois));
    const previous = volumes[index - 1];
    if (!previous) return [{ date: date.getTime(), volume: item.volume }];
    const next = new Date(timestamp(previous.mois));
    next.setUTCMonth(next.getUTCMonth() + 1);
    return next.getTime() < date.getTime()
      ? [
          { date: next.getTime(), volume: null },
          { date: date.getTime(), volume: item.volume },
        ]
      : [{ date: date.getTime(), volume: item.volume }];
  });
}

const monthFormat = new Intl.DateTimeFormat("fr-FR", {
  month: "short",
  year: "numeric",
  timeZone: "UTC",
});
const formatMonth = (value: number) => monthFormat.format(value);

export function VolumeChart({ volumes }: { volumes: VolumeMensuel[] }) {
  return (
    <div className="space-y-4">
      <p>
        Moyenne des volumes disponibles, pondérée par le score de rattachement
        des requêtes. Les mois sans données ne sont pas interpolés.
      </p>
      <div className="h-72 w-full" aria-hidden="true">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={graphData(volumes)}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis
              dataKey="date"
              type="number"
              scale="time"
              domain={["dataMin", "dataMax"]}
              tickFormatter={formatMonth}
            />
            <YAxis width={50} />
            <Tooltip labelFormatter={(value) => formatMonth(Number(value))} />
            <Line
              type="linear"
              dataKey="volume"
              name="Volume moyen"
              stroke="#1d4ed8"
              connectNulls={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <details>
        <summary className="cursor-pointer underline">
          Voir les données mensuelles
        </summary>
        <table className="mt-2 text-left">
          <caption className="sr-only">Volumes mensuels pondérés</caption>
          <thead>
            <tr>
              <th scope="col" className="pr-4">
                Mois
              </th>
              <th scope="col">Volume moyen</th>
            </tr>
          </thead>
          <tbody>
            {volumes.map((item) => (
              <tr key={item.mois}>
                <th scope="row" className="pr-4 font-normal">
                  {item.mois.slice(0, 7)}
                </th>
                <td>
                  {item.volume.toLocaleString("fr-FR", {
                    maximumFractionDigits: 2,
                  })}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </div>
  );
}
