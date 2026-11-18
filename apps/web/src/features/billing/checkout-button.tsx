"use client";

import { useState } from "react";

export function CheckoutButton() {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");

  async function checkout() {
    setPending(true);
    setError("");
    try {
      const response = await fetch("/api/stripe/checkout", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ plan: "pro" }),
      });
      const result: unknown = await response.json();
      if (!response.ok) {
        const message =
          typeof result === "object" &&
          result !== null &&
          "error" in result &&
          typeof result.error === "string"
            ? result.error
            : "Impossible d’ouvrir le paiement.";
        setError(message);
        return;
      }
      if (
        typeof result !== "object" ||
        result === null ||
        !("url" in result) ||
        typeof result.url !== "string"
      ) {
        throw new Error("URL de paiement absente");
      }
      window.location.assign(result.url);
    } catch (error) {
      console.error("Ouverture du paiement impossible", error);
      setError("Impossible d’ouvrir le paiement. Veuillez réessayer.");
    } finally {
      setPending(false);
    }
  }

  return (
    <div>
      <button
        type="button"
        onClick={checkout}
        disabled={pending}
        className="rounded border border-zinc-500 px-4 py-2 hover:bg-black/[.06] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 disabled:opacity-50 dark:border-zinc-400 dark:hover:bg-white/[.08]"
      >
        {pending ? "Ouverture…" : "Souscrire au plan pro"}
      </button>
      {error && (
        <p role="alert" className="mt-2 text-sm text-red-600 dark:text-red-400">
          {error}
        </p>
      )}
    </div>
  );
}
