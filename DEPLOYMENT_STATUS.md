# État du déploiement

**Vérifié le :** 2026-11-22
**Projet :** `test-barometre-juridique`
**Région :** `europe-west9`
**État global :** non déployé; les jobs Cloud Run et les schedulers existent, mais le frontend et l'image pipeline ne sont pas opérationnels.

## État GCP vérifié

| Ressource | État observé |
|---|---|
| Services Cloud Run | Aucun service; `vil-web` n'existe pas. |
| Jobs Cloud Run | `vil-load-corpus`, `vil-extract-notions` et `vil-gap-analysis` existent, mais utilisent `gcr.io/google.com/cloudsdktool/cloud-sdk:slim`, sans compte de service explicite, commande ni arguments. Aucune exécution récente n'a été trouvée. |
| Cloud Scheduler | Les trois schedulers existent et sont activés : 02:00, 04:00 et 06:00 UTC. Leur activation ne prouve pas le succès des jobs. |
| Artifact Registry | `vil-frontend` et `vil-pipeline` existent. Aucune image n'est publiée dans `vil-pipeline`; `vil-frontend` est vide. |
| BigQuery | `marts` existe en `europe-west9` avec 22 tables. `marts_e2e` n'existe pas encore; le workflow CI le créera lors de son exécution. |
| Secret Manager | Onze secrets ont une version active : `llm-api-key`, `dataforseo-login`, `dataforseo-password`, `neo4j-uri`, `neo4j-user`, `neo4j-password`, `supabase-url`, `supabase-key`, `supabase-service-role-key`, `stripe-secret-key`, `stripe-webhook-secret`. |
| Contenu des secrets | Les trois nouveaux noms ont une version active et des bindings Secret Accessor pour le compte frontend. Leur contenu n'a pas été lu ni validé contre Supabase/Stripe. La nature de `supabase-key` reste indéterminée; ne pas l'utiliser comme clé service-role. |
| Comptes d'exécution | `vil-jobs-runner` a BigQuery Data Editor, Storage Object User et Secret Manager Secret Accessor au niveau projet; le compte GitHub Actions peut maintenant agir comme ce compte. Le compte Compute par défaut a BigQuery Data Editor et un accès Secret Accessor par secret aux trois clés serveur du frontend. |

Les valeurs de secrets n'ont pas été affichées. L'état des variables/secrets GitHub n'a pas pu être vérifié : la CLI `gh` n'est pas disponible dans ce Codespace. Les connexions réelles à Supabase, Neo4j, DataForSEO et Stripe n'ont pas été testées.

## État du code

Les corrections sont sur la branche locale `fix/infra-alignment`; elles ne sont ni poussées ni fusionnées.

- E2E BigQuery : la fixture cible `marts_e2e`; le workflow crée le dataset en `europe-west9` ou vérifie sa localisation s'il existe déjà.
- Pipeline : `publish-pipeline.yml` est le workflow unique. Il construit et teste l'image, la publie avec le SHA du commit, puis configure les trois jobs avec `vil-jobs-runner`, leurs commandes et leurs variables. `vil-gap-analysis` lance `dbt build --select +fait_gap_score`. Le test local `dbt ls` n'a pas pu démarrer : `dbt-core-experimental-parser` ne fournit pas de wheel pour l'environnement courant.
- Frontend : les variables publiques Supabase sont transmises comme build-args. Le déploiement sélectionne explicitement le compte Compute par défaut, référence les secrets serveur Supabase/Stripe et exige `STRIPE_PRICE_PRO`.
- Docker : le Docker-in-Docker est déjà déclaré dans `.devcontainer/devcontainer.json`; reconstruire le Codespace devrait l'activer. Le binaire Docker n'était pas disponible pendant la vérification, donc les images n'ont pas été construites.

## Blocages à lever

1. Configurer les variables et secrets GitHub attendus par les workflows; leur présence reste à confirmer.
2. Valider que les valeurs des trois nouveaux secrets correspondent aux clés Supabase service-role et Stripe attendues, puis vérifier les connexions depuis le service.
3. Reconstruire le Codespace, puis construire et tester les deux images Docker.
4. Configurer les variables GitHub pipeline listées ci-dessous. Le workflow configure les trois jobs existants; le script manuel `scripts/deploy_jobs.sh` cible encore six autres noms et ne doit pas servir de référence avant alignement. La sélection dbt n'est pas validée localement à cause de la dépendance indisponible sur cette plateforme.
5. Publier la branche par Pull Request et attendre la CI. Le workflow de publication du pipeline ne déploie les jobs que sur `main`.
6. Exécuter chaque job manuellement et vérifier ses logs avant de laisser les schedulers actifs.
7. Déployer `vil-web`, tester l'URL, l'authentification Supabase et le parcours Stripe en mode test.

## Variables et secrets GitHub attendus

La présence des noms ci-dessous n'a pas été vérifiée (`gh` indisponible).

**Secrets du workflow pipeline et du frontend :**

- `GCP_PROJECT_ID`
- `GCP_WORKLOAD_IDENTITY_PROVIDER`
- `GCP_SERVICE_ACCOUNT`
- `STRIPE_TEST_SECRET_KEY` (CI E2E)

**Variables du frontend :**

- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- `STRIPE_PRICE_PRO`

**Variables du pipeline (nécessaires au déploiement des jobs sur `main`) :**

- `CORPUS_BUCKET`
- `CORPUS_OBJECT`
- `EXTRACTION_MAX_COST`
- `EXTRACTION_COST_PER_CALL`

**Variables et secrets du job E2E :**

- Variables : `E2E_GCP_PROJECT_ID`, `E2E_GCP_WORKLOAD_IDENTITY_PROVIDER`, `E2E_GCP_SERVICE_ACCOUNT`, `E2E_STRIPE_PRICE_PRO`
- Secret : `STRIPE_TEST_SECRET_KEY`

## Vérifications après configuration

1. CI complète, dont tests E2E sur `marts_e2e`.
2. Exécution manuelle de `vil-load-corpus`, `vil-extract-notions` et `vil-gap-analysis`, puis contrôle des états et logs.
3. Vérification de l'URL publique de `vil-web` et des pages principales.
4. Parcours connexion/inscription et session Supabase.
5. Checkout, webhook et portail Stripe avec des identifiants de test.