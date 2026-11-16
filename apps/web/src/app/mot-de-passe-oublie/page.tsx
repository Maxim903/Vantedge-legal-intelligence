import type { Metadata } from "next";
import { AuthForm } from "@/features/auth/auth-form";
import { AuthPage } from "@/features/auth/auth-page";
import { requestPasswordReset } from "@/features/auth/actions";

export const metadata: Metadata = { title: "Mot de passe oublié" };

export default function MotDePasseOubliePage() {
  return (
    <AuthPage title="Mot de passe oublié">
      <AuthForm
        action={requestPasswordReset}
        submitLabel="Envoyer le lien"
        fields={[
          {
            name: "email",
            label: "Adresse e-mail",
            type: "email",
            autoComplete: "email",
            required: true,
          },
        ]}
        links={[{ href: "/connexion", label: "Retour à la connexion" }]}
      />
    </AuthPage>
  );
}
