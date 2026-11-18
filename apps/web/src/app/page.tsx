import Link from "next/link";

const linkStyle =
  "rounded px-5 py-3 text-center font-medium focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600";

export default function Home() {
  return (
    <main className="mx-auto flex w-full max-w-5xl flex-1 flex-col justify-center gap-8 px-4 py-16">
      <div className="max-w-2xl space-y-4">
        <p className="text-sm font-semibold uppercase tracking-wide">
          Vantedge Legal Intelligence
        </p>
        <h1 className="text-3xl font-semibold sm:text-5xl">
          Analyse loi vs marché
        </h1>
        <p className="text-lg text-zinc-600 dark:text-zinc-400">
          Retrouvez votre compte, vos projets et vos analyses dans votre espace
          personnel.
        </p>
        <p>La fonctionnalité d’analyse est encore en cours de développement.</p>
      </div>
      <nav aria-label="Accès à l’application" className="flex flex-wrap gap-3">
        <Link
          href="/connexion"
          className={`${linkStyle} bg-black text-white dark:bg-white dark:text-black`}
        >
          Se connecter
        </Link>
        <Link
          href="/inscription"
          className={`${linkStyle} border border-zinc-500 dark:border-zinc-400`}
        >
          Créer un compte
        </Link>
        <Link
          href="/app/compte"
          className={`${linkStyle} border border-zinc-500 dark:border-zinc-400`}
        >
          Mon compte
        </Link>
      </nav>
    </main>
  );
}
