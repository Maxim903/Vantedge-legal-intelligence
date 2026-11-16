import Link from "next/link";
import { SignOutButton } from "@/features/auth/sign-out-button";
import { NavLink } from "@/components/nav-link";

export const PRODUCT_NAME = "Vantedge Legal Intelligence";

export function AppHeader() {
  return (
    <header className="border-b border-zinc-200 dark:border-zinc-800">
      <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-x-6 gap-y-2 px-4 py-3">
        <Link
          href="/app"
          className="rounded font-semibold focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600"
        >
          {PRODUCT_NAME}
        </Link>
        <nav
          aria-label="Navigation principale"
          className="flex flex-wrap items-center gap-1"
        >
          <NavLink href="/app/compte">Mon compte</NavLink>
          <NavLink href="/app/projets">Projets</NavLink>
          <NavLink href="/app/analyse">Analyse loi vs marché</NavLink>
          <SignOutButton />
        </nav>
      </div>
    </header>
  );
}
