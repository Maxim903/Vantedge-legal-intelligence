import type { Metadata } from "next";
import { AuthForm } from "@/features/auth/auth-form";
import { AuthPage } from "@/features/auth/auth-page";
import { signUp } from "@/features/auth/actions";

export const metadata: Metadata = { title: "Inscription" };

export default function InscriptionPage() {
  return (
    <AuthPage title="Créer un compte">
      <AuthForm
        action={signUp}
        submitLabel="S'inscrire"
        fields={[
          {
            name: "displayName",
            label: "Nom affiché (facultatif)",
            type: "text",
            autoComplete: "name",
          },
          {
            name: "email",
            label: "Adresse e-mail",
            type: "email",
            autoComplete: "email",
            required: true,
          },
          {
            name: "password",
            label: "Mot de passe (10 caractères minimum)",
            type: "password",
            autoComplete: "new-password",
            required: true,
          },
          {
            name: "confirmPassword",
            label: "Confirmer le mot de passe",
            type: "password",
            autoComplete: "new-password",
            required: true,
          },
        ]}
        links={[{ href: "/connexion", label: "J'ai déjà un compte" }]}
      />
    </AuthPage>
  );
}
