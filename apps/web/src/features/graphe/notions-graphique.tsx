"use client";

import { linkHorizontal } from "d3-shape";
import type { NotionGraphItem } from "./notions-graph";

const MAX_NODES = 12;
const link = linkHorizontal<
  { source: [number, number]; target: [number, number] },
  [number, number]
>()
  .x((point) => point[0])
  .y((point) => point[1]);

function shorten(value: string) {
  return value.length > 32 ? `${value.slice(0, 31)}…` : value;
}

export default function NotionsGraphique({
  libelle,
  notions,
}: {
  libelle: string;
  notions: NotionGraphItem[];
}) {
  const shown = notions.slice(0, MAX_NODES);
  const height = Math.max(100, shown.length * 52);
  const centerY = height / 2;
  return (
    <div>
      <p>
        Vue des {shown.length} premières notions liées
        {notions.length > shown.length
          ? " ; la liste complète figure ci-dessous"
          : ""}
        .
      </p>
      <svg
        aria-hidden="true"
        focusable="false"
        viewBox={`0 0 720 ${height}`}
        className="w-full"
      >
        {shown.map((notion, index) => {
          const y = index * 52 + 26;
          const path = link({ source: [260, centerY], target: [425, y] });
          if (path === null) throw new Error("Tracé du lien impossible.");
          return (
            <g key={notion.notion_id}>
              <path d={path} fill="none" stroke="currentColor" />
              <rect
                x="425"
                y={y - 19}
                width="285"
                height="38"
                rx="6"
                fill="var(--background)"
                stroke="currentColor"
              />
              <text
                x="437"
                y={y}
                dominantBaseline="middle"
                fill="currentColor"
                fontSize="14"
              >
                {shorten(notion.libelle)}
              </text>
            </g>
          );
        })}
        <rect
          x="10"
          y={centerY - 19}
          width="250"
          height="38"
          rx="6"
          fill="var(--background)"
          stroke="currentColor"
        />
        <text
          x="22"
          y={centerY}
          dominantBaseline="middle"
          fill="currentColor"
          fontSize="14"
        >
          {shorten(libelle)}
        </text>
      </svg>
    </div>
  );
}
