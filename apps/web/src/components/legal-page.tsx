import type { ReactNode } from "react";

export function LegalPage({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <main className="mx-auto w-full max-w-3xl flex-1 space-y-6 px-4 py-10">
      <h1 className="text-3xl font-semibold">{title}</h1>
      <div className="rounded border border-amber-600 p-4" role="note">
        <p className="font-bold">À VALIDER PAR UN JURISTE</p>
        <p>
          Gabarit incomplet, à compléter et à valider avant publication ou
          recueil d’acceptation. Ce document ne constitue pas un texte juridique
          en vigueur.
        </p>
        <p>
          Version et date d’entrée en vigueur : [à renseigner après validation].
        </p>
      </div>
      <div className="space-y-6 leading-relaxed [&_h2]:mb-2 [&_h2]:text-xl [&_h2]:font-semibold [&_ul]:list-disc [&_ul]:space-y-1 [&_ul]:pl-6">
        {children}
      </div>
    </main>
  );
}
