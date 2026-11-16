"use client";

import { useActionState } from "react";
import {
  createProject,
  deleteProject,
  renameProject,
  type ProjectActionState,
} from "./project-actions";

const inputClass =
  "rounded border border-zinc-400 px-2 py-1 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 dark:bg-zinc-900";
const buttonClass =
  "rounded border px-3 py-1 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 disabled:opacity-50";

function Feedback({ state }: { state: ProjectActionState }) {
  return (
    <>
      {state.error && (
        <p role="alert" className="text-sm text-red-600">
          {state.error}
        </p>
      )}
      {state.message && (
        <p role="status" className="text-sm">
          {state.message}
        </p>
      )}
    </>
  );
}

export function CreateProjectForm() {
  const [state, action, pending] = useActionState(createProject, {});
  return (
    <form action={action} className="flex flex-col items-start gap-2">
      <label htmlFor="nouveau-projet">Nom du nouveau projet</label>
      <input
        id="nouveau-projet"
        name="nom"
        required
        maxLength={120}
        className={inputClass}
      />
      <button className={buttonClass} disabled={pending}>
        {pending ? "Création…" : "Créer un projet"}
      </button>
      <Feedback state={state} />
    </form>
  );
}

export function ProjectForms({ id, name }: { id: string; name: string }) {
  const [renameState, renameAction, renaming] = useActionState(
    renameProject,
    {},
  );
  const [deleteState, deleteAction, deleting] = useActionState(
    deleteProject,
    {},
  );
  return (
    <div className="flex flex-col gap-3">
      <form action={renameAction} className="flex flex-wrap items-end gap-2">
        <input type="hidden" name="id" value={id} />
        <label className="flex flex-col gap-1">
          Renommer {name}
          <input
            name="nom"
            defaultValue={name}
            required
            maxLength={120}
            className={inputClass}
          />
        </label>
        <button className={buttonClass} disabled={renaming}>
          {renaming ? "Enregistrement…" : "Renommer"}
        </button>
        <Feedback state={renameState} />
      </form>
      <form action={deleteAction} className="flex flex-wrap items-center gap-2">
        <input type="hidden" name="id" value={id} />
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            name="confirmer"
            value="oui"
            required
            className="focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600"
          />
          Confirmer la suppression de {name} et de ses analyses
        </label>
        <button className={buttonClass} disabled={deleting}>
          {deleting ? "Suppression…" : "Supprimer"}
        </button>
        <Feedback state={deleteState} />
      </form>
    </div>
  );
}
