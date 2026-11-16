import type { ReactNode } from "react";

type BadgeProps = { children: ReactNode };

export function Badge({ children }: BadgeProps) {
  return (
    <span className="rounded-full bg-black/[.06] px-2 py-0.5 text-xs dark:bg-white/[.08]">
      {children}
    </span>
  );
}
