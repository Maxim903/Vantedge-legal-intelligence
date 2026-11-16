"use client";

import { useState } from "react";

export function PortalButton() {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");

  async function openPortal() {
    setPending(true);
    setError("");
    try {
      const response = await fetch("/api/stripe/portal", { method: "POST" });
      const result: unknown = await response.json();
      if (!response.ok) {
        const message =
          typeof result === "object" &&
          result !== null &&
          "error" in result &&
          typeof result.error === "string"
            ? result.error
            : "Impossible d'ouvrir le portail de facturation.";
        setError(message);
        return;
      }
      if (
        typeof result !== "object" ||
        result === null ||
        !("url" in result) ||
        typeof result.url !== "string"
      ) {
        throw new Error("URL du portail absente");
      }
      window.location.assign(result.url);
    } catch (error) {
      console.error("Ouverture du portail de facturation impossible", error);
      setError(
        "Impossible d'ouvrir le portail de facturation. Veuillez réessayer.",
      );
    } finally {
      setPending(false);
    }
  }

  return (
    <div>
      <button
        type="button"
        onClick={openPortal}
        disabled={pending}
        className="rounded border border-zinc-300 px-4 py-2 hover:bg-black/[.06] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 disabled:opacity-50 dark:border-zinc-700 dark:hover:bg-white/[.08]"
      >
        {pending ? "Ouverture…" : "Gérer mon abonnement"}
      </button>
      {error && (
        <p role="alert" className="mt-2 text-sm text-red-600">
          {error}
        </p>
      )}
    </div>
  );
}
