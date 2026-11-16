import type { Metadata } from "next";
import { Suspense } from "react";
import { AuthForm } from "@/features/auth/auth-form";
import { AuthPage } from "@/features/auth/auth-page";
import { signIn } from "@/features/auth/actions";
import { safeRedirectPath } from "@/features/auth/schemas";

export const metadata: Metadata = { title: "Connexion" };

async function Formulaire({
  searchParams,
}: {
  searchParams: Promise<{ redirect?: string; erreur?: string }>;
}) {
  const { redirect, erreur } = await searchParams;
  return (
    <>
      {erreur === "lien-invalide" && (
        <p role="alert" className="text-sm text-red-600">
          Ce lien est invalide ou a expiré. Veuillez recommencer.
        </p>
      )}
      <AuthForm
        action={signIn}
        submitLabel="Se connecter"
        hidden={{ redirect: safeRedirectPath(redirect) }}
        fields={[
          {
            name: "email",
            label: "Adresse e-mail",
            type: "email",
            autoComplete: "email",
            required: true,
          },
          {
            name: "password",
            label: "Mot de passe",
            type: "password",
            autoComplete: "current-password",
            required: true,
          },
        ]}
        links={[
          { href: "/mot-de-passe-oublie", label: "Mot de passe oublié ?" },
          { href: "/inscription", label: "Créer un compte" },
        ]}
      />
    </>
  );
}

export default function ConnexionPage({
  searchParams,
}: {
  searchParams: Promise<{ redirect?: string; erreur?: string }>;
}) {
  return (
    <AuthPage title="Connexion">
      <Suspense>
        <Formulaire searchParams={searchParams} />
      </Suspense>
    </AuthPage>
  );
}
