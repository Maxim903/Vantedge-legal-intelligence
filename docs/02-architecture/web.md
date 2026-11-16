# Application web (`apps/web`)

Application Next.js (App Router, TypeScript, Tailwind) située dans `apps/web`.

## Structure de `src/`

```text
src/
├── app/         Routes, layouts et pages (App Router).
├── components/  Composants d'interface purs.
├── features/    Logique par domaine fonctionnel.
├── lib/         Utilitaires transverses.
│   └── server/  Code exécuté uniquement côté serveur.
└── types/       Types TypeScript partagés.
```

Les dépendances vont dans un seul sens : `app` → `features` → `components` / `lib` / `types`. Un composant de `components/` n'importe jamais `features/`.

### `app/`

Routes, layouts, pages, handlers de route. Les pages composent des éléments de `features/` et de `components/` et restent minces : pas de logique métier.

### `features/` : logique par domaine

Un dossier par domaine métier (par exemple `features/notions/`, `features/articles/`). Chaque dossier regroupe ce qui est propre au domaine : composants liés au domaine, hooks, accès aux données, schémas de validation, types locaux et tests.

Une feature n'importe pas une autre feature directement ; le code partagé remonte dans `components/`, `lib/` ou `types/`.

### `lib/server/` : code serveur uniquement

Tout fichier de `lib/server/` commence par :

```ts
import "server-only";
```

Cet import fait échouer la compilation si le module est importé depuis un composant client. Il protège les secrets, les clients BigQuery et tout accès aux données. Exemple : `lib/server/env.ts`. Le reste de `lib/` doit rester utilisable côté client et côté serveur.

### Variables d'environnement

`lib/env.ts` définit les schémas zod : `serverEnvSchema` (secrets) et `clientEnvSchema` (`NEXT_PUBLIC_*` uniquement). Il ne lit pas `process.env` pour les secrets. Le code serveur lit la configuration validée via `getServerEnv()` (`lib/server/env.ts`) ; le code client passe par `getClientEnv()`, qui référence chaque `NEXT_PUBLIC_*` littéralement, condition pour que Next.js les injecte dans le bundle. La validation est paresseuse : une variable manquante lève une erreur à l'appel, pas au démarrage.

Exception : `lib/supabase/server.ts` (client Supabase lié aux cookies) vit à côté de `browser.ts` et `update-session.ts`, mais commence lui aussi par `import "server-only"`.

### `components/` : UI pure

Composants de présentation : ils reçoivent des props et rendent du JSX. Ils ne font ni appel réseau, ni accès aux données, ni lecture de l'environnement, et ne connaissent aucun domaine métier. Exemple : `components/badge.tsx`.

### `types/`

Types TypeScript partagés entre plusieurs features. Un type utilisé par une seule feature reste dans cette feature.

## Qualité

Commandes à lancer depuis `apps/web` :

| Commande               | Rôle                                  |
| ---------------------- | ------------------------------------- |
| `npm run lint`         | ESLint, dont l'interdiction de `any`. |
| `npm run typecheck`    | `tsc --noEmit`, mode `strict`.        |
| `npm run format:check` | Vérifie le format Prettier.           |
| `npm run format`       | Applique Prettier.                    |
| `npm test`             | Vitest et Testing Library.            |

- `strict` est activé dans `tsconfig.json`.
- La règle `@typescript-eslint/no-explicit-any` est une erreur.
- Les tests sont placés à côté du code (`*.test.ts` / `*.test.tsx`). Vitest remplace `server-only` par un module vide pour pouvoir tester le code de `lib/server/`.

## Authentification

- `features/auth/` : schémas zod (`schemas.ts`), traduction des erreurs Supabase en français (`messages.ts`), actions serveur (`actions.ts` : `signIn`, `signUp`, `requestPasswordReset`, `signOut`) et formulaire partagé.
- Pages : `/inscription`, `/connexion` (paramètre `redirect`, limité aux chemins internes), `/mot-de-passe-oublie`. La route `/auth/callback` échange le code des e-mails contre une session.
- `proxy.ts` (via `lib/supabase/update-session.ts`) redirige vers `/connexion?redirect=…` toute requête anonyme sur `/app` ou `/app/*`. Ce contrôle est une première barrière : les données restent protégées par la RLS Supabase.
- Les actions sont testées avec des doubles de `@/lib/supabase/server`, `next/headers` et `next/navigation`.

## Facturation

La page `/app/compte/abonnement` affiche l'abonnement accessible via la RLS. Le bouton appelle `POST /api/stripe/portal` : la route authentifie l'utilisateur, retrouve son client Stripe en base et crée une session du portail avec une URL de retour fixe fondée sur `APP_URL`. La date affichée est la fin de période connue ; elle ne garantit pas un renouvellement. Le portail client doit être configuré dans Stripe et `APP_URL` doit correspondre à l'URL publique de l'application.

## Quotas

`features/quotas/service.ts` est réservé au serveur : l'appelant doit authentifier l'utilisateur et lui associer lui-même `userId`. `checkQuota` fournit un état indicatif ; seul `consumeQuota`, à appeler avant le travail coûteux, réserve atomiquement une unité. La fonction SQL est exécutable uniquement par le rôle service, utilise le plafond du plan associé et un mois calendaire UTC, sans report. Un plan absent ou une limite atteinte donne un refus explicite ; les erreurs techniques sont propagées.

La consommation de chaque action et le droit d'accès selon le statut de l'abonnement ne sont pas définis par les spécifications : ce service ne contrôle pas le statut et ne rembourse pas automatiquement une unité en cas d'échec ultérieur. Ces règles restent à définir avant son intégration aux actions métier.

## Compte et projets

`/app/compte` charge séparément le profil, l'abonnement, le quota, les projets et les analyses. Les lectures utilisateur et les mutations de projets utilisent le client Supabase associé à la session et la RLS ; l'identité est vérifiée à chaque mutation. La suppression d'un projet entraîne celle de ses analyses par cascade et nécessite une confirmation. Le quota affiché provient du service serveur et ne constitue pas une autorisation de lancer une analyse. Aucun historique de recherche distinct ni système de crédits n'est encore disponible ; la page d'analyse est pour l'instant un emplacement réservé.
