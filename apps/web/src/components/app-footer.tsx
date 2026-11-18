import Link from "next/link";
import { Disclaimer } from "@/components/disclaimer";

export function AppFooter() {
  return (
    <footer className="border-t border-zinc-200 dark:border-zinc-800">
      <div className="mx-auto flex max-w-5xl flex-col gap-3 px-4 py-4 text-sm text-zinc-600 dark:text-zinc-400">
        <Disclaimer />
        <nav aria-label="Informations légales">
          <ul className="flex flex-wrap gap-x-4 gap-y-2">
            {[
              { href: "/mentions-legales", label: "Mentions légales" },
              { href: "/cgu", label: "CGU" },
              { href: "/confidentialite", label: "Confidentialité" },
            ].map(({ href, label }) => (
              <li key={href}>
                <Link
                  href={href}
                  className="rounded underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600"
                >
                  {label}
                </Link>
              </li>
            ))}
          </ul>
        </nav>
      </div>
    </footer>
  );
}
