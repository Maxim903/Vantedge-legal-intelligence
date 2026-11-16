import type { ReactNode } from "react";
import { AppHeader } from "@/components/app-header";

export default function AppLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex flex-1 flex-col">
      <a
        href="#contenu"
        className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-10 focus:rounded focus:bg-white focus:px-3 focus:py-2 focus:text-black focus-visible:outline-2 focus-visible:outline-blue-600"
      >
        Aller au contenu
      </a>
      <AppHeader />
      <main id="contenu" className="mx-auto w-full max-w-5xl flex-1 px-4 py-8">
        {children}
      </main>
    </div>
  );
}
