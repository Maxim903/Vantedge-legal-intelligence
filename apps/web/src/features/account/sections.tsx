import "server-only";
import Link from "next/link";
import { checkQuota } from "@/features/quotas/service";
import { createClient } from "@/lib/supabase/server";
import { CreateProjectForm, ProjectForms } from "./project-forms";

const linkClass =
  "rounded underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600";

function SectionError({ name }: { name: string }) {
  return (
    <div role="alert">
      <p>Impossible de charger {name}.</p>
      <a href="/app/compte" className={linkClass}>
        Réessayer
      </a>
    </div>
  );
}

async function load<T>(
  name: string,
  operation: () => Promise<T>,
): Promise<{ ok: true; data: T } | { ok: false }> {
  try {
    return { ok: true, data: await operation() };
  } catch (error) {
    console.error(`Chargement ${name} impossible`, error);
    return { ok: false };
  }
}

export async function ProfileSection({
  userId,
  email,
}: {
  userId: string;
  email?: string;
}) {
  const result = await load("du profil", async () => {
    const supabase = await createClient();
    const { data, error } = await supabase
      .from("profiles")
      .select("display_name")
      .eq("id", userId)
      .maybeSingle();
    if (error) throw error;
    return data;
  });
  if (!result.ok) return <SectionError name="le profil" />;
  const data = result.data;
  if (!data) return <p>Votre profil n’est pas encore disponible.</p>;
  return (
    <dl className="space-y-2">
      <div>
        <dt className="font-semibold">Nom affiché</dt>
        <dd>{data.display_name || "Non renseigné"}</dd>
      </div>
      <div>
        <dt className="font-semibold">Adresse e-mail</dt>
        <dd>{email || "Non renseignée"}</dd>
      </div>
    </dl>
  );
}

export async function SubscriptionSection({ userId }: { userId: string }) {
  const result = await load("de l'abonnement", async () => {
    const supabase = await createClient();
    const { data, error } = await supabase
      .from("subscriptions")
      .select("plan_code, statut")
      .eq("user_id", userId)
      .maybeSingle();
    if (error) throw error;
    return data;
  });
  if (!result.ok) return <SectionError name="l’abonnement" />;
  const data = result.data;
  return (
    <div className="space-y-2">
      {data ? (
        <dl>
          <div>
            <dt className="font-semibold">Plan</dt>
            <dd>{data.plan_code}</dd>
          </div>
          <div>
            <dt className="font-semibold">Statut</dt>
            <dd>{data.statut}</dd>
          </div>
        </dl>
      ) : (
        <p>Vous n’avez pas encore d’abonnement.</p>
      )}
      <Link href="/app/compte/abonnement" className={linkClass}>
        Voir et gérer mon abonnement
      </Link>
    </div>
  );
}

export async function QuotaSection({ userId }: { userId: string }) {
  const result = await load("du quota", () => checkQuota(userId));
  if (!result.ok) return <SectionError name="les quotas" />;
  const quota = result.data;
  if (quota.motif === "plan_absent")
    return <p>Aucun quota disponible : aucun plan associé à votre compte.</p>;
  return (
    <div className="space-y-2">
      <p>
        Analyses restantes :{" "}
        <strong>{Math.max(0, quota.limite - quota.consomme)}</strong> sur{" "}
        {quota.limite}.
      </p>
      <p>
        Consommées ce mois : {quota.consomme}. Période depuis le {quota.periode}{" "}
        (UTC).
      </p>
      {!quota.autorise && (
        <p>
          Quota atteint.{" "}
          <Link href="/app/compte/abonnement" className={linkClass}>
            Gérer mon abonnement
          </Link>
        </p>
      )}
      <p>Les crédits ne sont pas encore disponibles.</p>
    </div>
  );
}

export async function ProjectsSection({ userId }: { userId: string }) {
  const result = await load("des projets", async () => {
    const supabase = await createClient();
    const { data, error } = await supabase
      .from("projects")
      .select("id, nom")
      .eq("user_id", userId)
      .order("nom");
    if (error) throw error;
    return data;
  });
  if (!result.ok) return <SectionError name="les projets" />;
  const data = result.data;
  return (
    <div className="space-y-4">
      {data.length === 0 ? (
        <p>Vous n’avez pas encore de projet. Créez votre premier projet.</p>
      ) : (
        <ul className="space-y-4">
          {data.map((project) => (
            <li
              key={project.id}
              className="rounded border border-zinc-300 p-3 dark:border-zinc-700"
            >
              <h3 className="mb-2 font-semibold">{project.nom}</h3>
              <ProjectForms id={project.id} name={project.nom} />
            </li>
          ))}
        </ul>
      )}
      <CreateProjectForm />
    </div>
  );
}

export async function HistorySection({ userId }: { userId: string }) {
  const result = await load("de l'historique", async () => {
    const supabase = await createClient();
    const [analyses, projects] = await Promise.all([
      supabase
        .from("analyses")
        .select("id, project_id, created_at, parametres, quota_verifie")
        .eq("user_id", userId)
        .order("created_at", { ascending: false }),
      supabase.from("projects").select("id, nom").eq("user_id", userId),
    ]);
    if (analyses.error) throw analyses.error;
    if (projects.error) throw projects.error;
    const names = new Map(
      projects.data.map((project) => [project.id, project.nom]),
    );
    return analyses.data.map((analysis) => ({
      ...analysis,
      projectName: names.get(analysis.project_id) ?? "Projet indisponible",
    }));
  });
  if (!result.ok) return <SectionError name="l’historique" />;
  const data = result.data;
  return (
    <div className="space-y-3">
      {data.length === 0 ? (
        <p>
          Aucune analyse enregistrée. Accédez à l’analyse loi vs marché pour
          commencer.
        </p>
      ) : (
        <ul className="space-y-3">
          {data.map((analysis) => (
            <li
              key={analysis.id}
              className="rounded border border-zinc-300 p-3 dark:border-zinc-700"
            >
              <p className="font-semibold">{analysis.projectName}</p>
              <p>
                <time dateTime={analysis.created_at}>
                  {new Date(analysis.created_at)
                    .toISOString()
                    .replace("T", " ")
                    .slice(0, 16)}{" "}
                  UTC
                </time>
              </p>
              {analysis.quota_verifie &&
                typeof analysis.parametres === "object" &&
                analysis.parametres !== null &&
                "notion_id" in analysis.parametres &&
                typeof analysis.parametres.notion_id === "string" &&
                analysis.parametres.notion_id.length > 0 && (
                  <Link
                    className={linkClass}
                    href={`/app/analyse/${encodeURIComponent(analysis.parametres.notion_id)}?projet=${encodeURIComponent(analysis.project_id)}`}
                  >
                    Ouvrir cette analyse
                  </Link>
                )}
              <details>
                <summary className="cursor-pointer rounded focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600">
                  Paramètres de l’analyse
                </summary>
                <pre className="overflow-auto whitespace-pre-wrap break-words text-sm">
                  {JSON.stringify(analysis.parametres, null, 2)}
                </pre>
              </details>
            </li>
          ))}
        </ul>
      )}
      <Link href="/app/analyse" className={linkClass}>
        Accéder à Analyse loi vs marché
      </Link>
    </div>
  );
}
