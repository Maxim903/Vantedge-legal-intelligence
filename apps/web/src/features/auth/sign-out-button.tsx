import { signOut } from "./actions";

export function SignOutButton() {
  return (
    <form action={signOut}>
      <button
        type="submit"
        className="rounded border border-zinc-300 px-3 py-1 text-sm hover:bg-black/[.06] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 dark:border-zinc-700 dark:hover:bg-white/[.08]"
      >
        Déconnexion
      </button>
    </form>
  );
}
