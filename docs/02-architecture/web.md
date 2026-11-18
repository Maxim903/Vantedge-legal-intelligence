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

| Commande               | Rôle                                                             |
| ---------------------- | ---------------------------------------------------------------- |
| `npm run lint`         | ESLint, dont l'interdiction de `any`.                            |
| `npm run typecheck`    | `tsc --noEmit`, mode `strict`.                                   |
| `npm run format:check` | Vérifie le format Prettier.                                      |
| `npm run format`       | Applique Prettier.                                               |
| `npm test`             | Vitest et Testing Library.                                       |
| `npm run test:e2e`     | Parcours Playwright avec services de test configurés.            |
| `npm run test:a11y`    | Axe et navigation clavier des pages publiques (build préalable). |

- `strict` est activé dans `tsconfig.json`.
- La règle `@typescript-eslint/no-explicit-any` est une erreur.
- Les tests sont placés à côté du code (`*.test.ts` / `*.test.tsx`). Vitest remplace `server-only` par un module vide pour pouvoir tester le code de `lib/server/`.

Les tests Playwright d'accessibilité vérifient les règles axe WCAG A/AA et les
contrastes des pages publiques en clair et en sombre, ainsi que l'ordre de
tabulation et un contraste d'au moins 3:1 pour le focus et la bordure du champ
de connexion. Le job
CI `accessibility` ne nécessite aucun service externe ; le parcours E2E avec
services de test analyse aussi les pages authentifiées et le lien d'évitement.
Les contrôles automatisés ne remplacent pas une revue manuelle complète, notamment
avec un lecteur d'écran.

Pour les lancer localement depuis `apps/web`, installer Chromium avec
`npx playwright install chromium`, définir `NEXT_PUBLIC_SUPABASE_URL` sur
`http://127.0.0.1:54321` et `NEXT_PUBLIC_SUPABASE_ANON_KEY` sur `local-test`,
puis exécuter `npm run build` et `npm run test:a11y`. Les pages publiques de
ce test n'établissent aucune session Supabase.

## Authentification

- `features/auth/` : schémas zod (`schemas.ts`), traduction des erreurs Supabase en français (`messages.ts`), actions serveur (`actions.ts` : `signIn`, `signUp`, `requestPasswordReset`, `signOut`) et formulaire partagé.
- Pages : `/inscription`, `/connexion` (paramètre `redirect`, limité aux chemins internes), `/mot-de-passe-oublie`. La route `/auth/callback` échange le code des e-mails contre une session.
- `proxy.ts` (via `lib/supabase/update-session.ts`) redirige vers `/connexion?redirect=…` toute requête anonyme sur `/app` ou `/app/*`. Ce contrôle est une première barrière : les données restent protégées par la RLS Supabase.
- Les actions sont testées avec des doubles de `@/lib/supabase/server`, `next/headers` et `next/navigation`.

## Facturation

La page `/app/compte/abonnement` affiche l'abonnement accessible via la RLS. Sans abonnement actif, le bouton de souscription ouvre le checkout du plan `pro` via `POST /api/stripe/checkout`. Le bouton de gestion appelle `POST /api/stripe/portal` : la route authentifie l'utilisateur, retrouve son client Stripe en base et crée une session du portail avec une URL de retour fixe fondée sur `APP_URL`. La date affichée est la fin de période connue ; elle ne garantit pas un renouvellement. Le portail client doit être configuré dans Stripe et `APP_URL` doit correspondre à l'URL publique de l'application.

### Test de bout en bout

Le job CI `e2e` utilise Supabase local, Stripe en mode test et un projet BigQuery
**exclusivement dédié aux tests**, dans `europe-west9`. Il crée ou complète les
tables synthétiques du dataset `marts` ; ne jamais le configurer sur un projet
contenant des données réelles. Le jeu reste dans ce projet et les exécutions sont
sérialisées. Le test crée un utilisateur et un projet locaux, paie avec la carte
Stripe de test, attend le webhook puis vérifie l'ouverture et la réouverture
depuis l'historique. Il supprime le client Stripe de test créé ; Supabase local
est éphémère. Une interruption peut laisser le client de test dans Stripe ;
vérifier le compte dédié si le nettoyage échoue. Aucun enregistrement vidéo,
capture ou trace navigateur n'est conservé.

Configurer l'environnement GitHub `e2e` avec les variables
`E2E_GCP_PROJECT_ID`, `E2E_GCP_WORKLOAD_IDENTITY_PROVIDER`,
`E2E_GCP_SERVICE_ACCOUNT` et `E2E_STRIPE_PRICE_PRO`, et le secret
`STRIPE_TEST_SECRET_KEY` (`sk_test_…`). Le prix Stripe doit être récurrent et
appartenir au compte de test dédié. L'identité Google doit pouvoir créer le
dataset, les tables et les jobs BigQuery dans ce projet de test uniquement.
Configurer une approbation obligatoire pour l'environnement et une restriction
Workload Identity sur ce dépôt et cet environnement ; examiner les modifications
du workflow et des tests avant d'autoriser l'accès aux secrets. Le job est
ignoré sur les pull requests provenant de forks, qui n'ont pas accès aux secrets.
Les variables manquantes font échouer le job, elles ne désactivent pas le test.

Pour l'exécuter localement, démarrer une instance Supabase locale avec les
migrations et un plan `pro` de quota 5, provisionner le jeu
`apps/web/e2e/fixtures/marts.sql` dans le projet BigQuery dédié, et transférer
les webhooks Stripe CLI vers `http://127.0.0.1:3000/api/stripe/webhook`.
Configurer les variables Supabase, BigQuery, Stripe et `APP_URL`, notamment
`STRIPE_WEBHOOK_SECRET` fourni par Stripe CLI. Depuis `apps/web`, lancer
`npm ci`, `npx playwright install chromium`, `npm run build`, puis
`npm run test:e2e`. Ne pas utiliser des identifiants de production.

## Quotas

`features/quotas/service.ts` est réservé au serveur : l'appelant doit authentifier l'utilisateur et lui associer lui-même `userId`. `checkQuota` fournit un état indicatif ; seul `consumeQuota`, à appeler avant le travail coûteux, réserve atomiquement une unité. La fonction SQL est exécutable uniquement par le rôle service, utilise le plafond du plan associé et un mois calendaire UTC, sans report. Un plan absent ou une limite atteinte donne un refus explicite ; les erreurs techniques sont propagées.

L'ouverture d'une notion dans un projet utilise `checkQuota`, puis `consumeQuota` ; la consommation et l'enregistrement de l'analyse sont atomiques. Le service ne contrôle pas le statut de l'abonnement. Les autres règles de consommation restent à définir.

## Compte et projets

`/app/compte` charge séparément le profil, l'abonnement, le quota, les projets et les analyses. Les lectures utilisateur et les mutations de projets utilisent le client Supabase associé à la session et la RLS ; l'identité est vérifiée à chaque mutation. La suppression d'un projet entraîne celle de ses analyses par cascade et nécessite une confirmation. Le quota affiché provient du service serveur et ne constitue pas une autorisation de lancer une analyse. Aucun historique de recherche distinct ni système de crédits n'est encore disponible.

## Analyse loi vs marché

`/app/analyse` vérifie la session avant de lire BigQuery. La page affiche les
scores calculés du Code du travail pour la France et le français, filtre par
situation de vie et trie les résultats avant pagination. Chaque ligne représente
un score distinct et affiche sa date et sa version. Le modèle actuel calcule les
scores pour le code entier, pas pour le Livre I : la page l'indique explicitement
et ne présente pas ces résultats comme propres au livre. La consultation du
tableau ne déclenche aucun recalcul ni consommation de quota.

La page `/app/analyse/[notionId]` vérifie également la session et le périmètre,
puis charge indépendamment les articles, requêtes, volumes, intentions et SERP.
Les articles sont limités au Code du travail ; la version en vigueur est
privilégiée, sinon la dernière version est signalée comme non actuellement en
vigueur. Les données de marché sont limitées à France/fr. La courbe représente,
pour chaque mois disponible, la moyenne des volumes pondérée par les scores de
rattachement ; les mois sans données ne sont pas interpolés. Le top SERP
correspond aux positions 1 à 10 de la dernière date disponible par requête.
Les blocs en erreur conservent les autres résultats visibles ; réessayer recharge
la page. Aucun recalcul ni appel DataForSEO n'est déclenché.

Le bloc « Notions liées » présente les notions partageant des articles dans le
graphe, tous codes confondus. La liste et le nombre d'articles communs sont
toujours rendus côté serveur ; le graphique facultatif montre les 12 premières
notions. Si son chargement échoue ou si JavaScript est désactivé, la liste reste
disponible. Le chargement initial de cette page attend la lecture du graphe
(délai maximal de 15 secondes) afin de garantir ce repli sans JavaScript ; une
erreur de lecture est signalée dans le bloc sans masquer les autres données.

L'ouverture d'une notion nécessite le choix d'un projet appartenant à l'utilisateur.
La première ouverture vérifie puis consomme une unité ; l'enregistrement dans
`analyses` et la consommation sont effectués dans la même transaction, avec un
verrou empêchant les ouvertures concurrentes en double. Les réouvertures, y compris
après épuisement du quota, sont gratuites tant que l'analyse et son projet existent.
Les créations et modifications directes d'analyses par les clients sont interdites.
Les lignes antérieures, créées avant cette protection, ne valent pas autorisation
de consultation gratuite ; une nouvelle ouverture les soumet au quota.
Une limite atteinte propose de gérer l'abonnement pour passer à un plan supérieur.

## Repository d'analyse

`features/analyse/repository.ts` lit les tables `marts` du projet BigQuery configuré.
Ses requêtes SQL sont importées au build et leurs valeurs sont passées en
paramètres. `listNotions` accepte `tri` (`asc` ou `desc`), un `filtre` texte et
une `page` à partir de 1 ; il retourne jusqu'à 20 notions par page.
`getNotionDetail` retourne les champs de `dim_notion`, ou `null` si elle est
absente. `getGapScores` retourne tous les scores disponibles pour les notions
demandées, avec leurs dates et périmètres, sans choisir un score unique.
Les entrées et les lignes retournées sont validées avec Zod. La limite du client
BigQuery de 1 000 lignes s'applique aussi aux scores : un dépassement est une
erreur, jamais une liste tronquée. L'authentification et l'autorisation des
appelants restent à la charge de la couche appelante.

## Repository graphe

`features/graphe/repository.ts` expose `getNotionsVoisines(notionId)`,
`getNotionsConnectees(limite)`, `getCheminsNotionArticles(notionId)` et
`getClustersSituations()`. Les requêtes Cypher de `graph/queries/` sont intégrées
au build ; les paramètres et les résultats sont validés, et les chemins et
entiers Neo4j sont convertis en données JavaScript sérialisables. Un entier hors
plage sûre est rejeté. L'authentification et l'autorisation restent à la charge
de l'appelant ; aucun écran ne consomme encore ce repository.

Le client serveur partage le pilote et ouvre une session de lecture par requête.
Configurer `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` et, si nécessaire,
`NEO4J_DATABASE`. Utiliser un compte Neo4j disposant uniquement des droits de
lecture : le mode de routage `READ` ne remplace pas ces permissions. Le délai
maximal est de 15 secondes, fermeture de session comprise ; les erreurs de
requête, de validation et de fermeture sont remontées.
