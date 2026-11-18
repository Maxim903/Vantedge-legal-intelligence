type AuthErrorLike = { code?: string; status?: number; message?: string };

const RATE_LIMIT =
  "Trop de tentatives. Patientez quelques minutes avant de réessayer.";

const MESSAGES: Record<string, string> = {
  invalid_credentials: "E-mail ou mot de passe incorrect.",
  email_not_confirmed:
    "Votre adresse e-mail n'est pas encore confirmée. Consultez votre boîte de réception.",
  user_already_exists: "Un compte existe déjà avec cette adresse e-mail.",
  email_exists: "Un compte existe déjà avec cette adresse e-mail.",
  weak_password:
    "Ce mot de passe est trop faible. Choisissez-en un plus long ou plus varié.",
  over_request_rate_limit: RATE_LIMIT,
  over_email_send_rate_limit:
    "Trop d'e-mails envoyés. Patientez quelques minutes avant de réessayer.",
  signup_disabled: "Les inscriptions sont momentanément fermées.",
};

const GENERIC = "Une erreur est survenue. Veuillez réessayer.";

/** Traduit une erreur Supabase Auth en message clair, sans exposer le détail technique. */
export function authErrorMessage(error: AuthErrorLike): string {
  if (error.code && MESSAGES[error.code]) return MESSAGES[error.code];
  if (error.status === 429) return RATE_LIMIT;
  return GENERIC;
}
