"use client";

import dynamic from "next/dynamic";
import { Component, type ErrorInfo, type ReactNode } from "react";
import type { NotionVoisine } from "./repository";

export type NotionGraphItem = Pick<
  NotionVoisine,
  "notion_id" | "libelle" | "nombre_articles_communs"
>;

const Graphique = dynamic(() => import("./notions-graphique"), {
  ssr: false,
});

class GraphErrorBoundary extends Component<
  { children: ReactNode },
  { failed: boolean }
> {
  state = { failed: false };

  static getDerivedStateFromError() {
    return { failed: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("Affichage du graphique des notions impossible", error, info);
  }

  render() {
    if (this.state.failed)
      return (
        <p role="status">Graphique indisponible ; la liste reste accessible.</p>
      );
    return this.props.children;
  }
}

export function NotionsGraph({
  libelle,
  notions,
}: {
  libelle: string;
  notions: NotionGraphItem[];
}) {
  return (
    <GraphErrorBoundary key={libelle}>
      <Graphique libelle={libelle} notions={notions} />
    </GraphErrorBoundary>
  );
}
