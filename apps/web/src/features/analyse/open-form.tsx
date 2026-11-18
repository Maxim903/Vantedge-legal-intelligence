"use client";

import Link from "next/link";
import { useActionState } from "react";
import { openAnalysis } from "./open-action";

export function OpenAnalysisForm({
  notionId,
  projects,
  selectedProject,
}: {
  notionId: string;
  projects: { id: string; nom: string }[];
  selectedProject?: string;
}) {
  const [state, action, pending] = useActionState(openAnalysis, {});
  return (
    <form action={action} className="space-y-4">
      <input type="hidden" name="notion_id" value={notionId} />
      <label className="grid gap-1">
        Projet
        <select
          name="project_id"
          defaultValue={selectedProject ?? ""}
          required
          className="rounded border border-zinc-500 bg-transparent p-2 dark:border-zinc-400"
        >
          <option value="">Choisir un projet</option>
          {projects.map((project) => (
            <option key={project.id} value={project.id}>
              {project.nom}
            </option>
          ))}
        </select>
      </label>
      <p>
        La première ouverture dans ce projet consomme une unité de quota. Les
        réouvertures sont gratuites.
      </p>
      <button
        disabled={pending}
        className="rounded bg-blue-700 px-4 py-2 text-white disabled:opacity-50"
      >
        {pending ? "Ouverture…" : "Ouvrir l’analyse"}
      </button>
      {state.error && <p role="alert">{state.error}</p>}
      {state.upgrade && (
        <p>
          <Link className="underline" href="/app/compte/abonnement">
            Passer à un plan supérieur
          </Link>
        </p>
      )}
    </form>
  );
}
