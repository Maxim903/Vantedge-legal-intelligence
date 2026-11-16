"use client";

import Link from "next/link";
import { useActionState } from "react";
import type { AuthFormState } from "./actions";

type Field = {
  name: string;
  label: string;
  type: "text" | "email" | "password";
  autoComplete: string;
  required?: boolean;
};

type AuthFormProps = {
  action: (prev: AuthFormState, formData: FormData) => Promise<AuthFormState>;
  fields: Field[];
  submitLabel: string;
  hidden?: Record<string, string>;
  links?: { href: string; label: string }[];
};

export function AuthForm({
  action,
  fields,
  submitLabel,
  hidden,
  links,
}: AuthFormProps) {
  const [state, formAction, pending] = useActionState(action, {});

  return (
    <form action={formAction} className="flex flex-col gap-4" noValidate>
      {Object.entries(hidden ?? {}).map(([name, value]) => (
        <input key={name} type="hidden" name={name} value={value} />
      ))}
      {fields.map((f) => {
        const errors = state.fieldErrors?.[f.name];
        return (
          <label key={f.name} className="flex flex-col gap-1 text-sm">
            {f.label}
            <input
              name={f.name}
              type={f.type}
              autoComplete={f.autoComplete}
              required={f.required}
              aria-invalid={errors ? true : undefined}
              aria-describedby={errors ? `${f.name}-erreur` : undefined}
              className="rounded border border-zinc-300 px-3 py-2 dark:border-zinc-700 dark:bg-zinc-900"
            />
            {errors && (
              <span id={`${f.name}-erreur`} className="text-red-600">
                {errors[0]}
              </span>
            )}
          </label>
        );
      })}
      {state.error && (
        <p role="alert" className="text-sm text-red-600">
          {state.error}
        </p>
      )}
      {state.message && (
        <p role="status" className="text-sm text-green-700">
          {state.message}
        </p>
      )}
      <button
        type="submit"
        disabled={pending}
        className="rounded bg-black px-4 py-2 text-white disabled:opacity-50 dark:bg-white dark:text-black"
      >
        {pending ? "Veuillez patienter…" : submitLabel}
      </button>
      {links && (
        <ul className="flex flex-col gap-1 text-sm">
          {links.map((l) => (
            <li key={l.href}>
              <Link href={l.href} className="underline">
                {l.label}
              </Link>
            </li>
          ))}
        </ul>
      )}
    </form>
  );
}
