# Environnements et promotion

Ce guide définit la configuration attendue pour le développement local, la CI,
la préproduction et la production. L'isolement et les contrôles ci-dessous
doivent être vérifiés avant utilisation ; ils ne sont pas tous automatisés.
La préproduction et l'hébergement web restent à mettre en place et à valider :
voir l'[ADR-0007](../adr/0007-hebergement-web.md) et le
[déploiement web](deploiement-web.md). Ici, « préproduction » désigne un
environnement de recette, pas le dataset BigQuery nommé `staging`.

## Règle : jamais de clé live en préproduction

La préproduction, le développement et la CI ne doivent recevoir **aucune clé
live Stripe**, ni aucun secret, compte de service ou accès permettant d'agir
sur les ressources de production. Utiliser uniquement des identités et
ressources de test distinctes, avec des droits minimaux et des données
synthétiques. Ne pas copier des secrets ou données de production pour faciliter
une recette. En cas de doute sur le mode ou la destination d'un identifiant,
arrêter le déploiement jusqu'à vérification.

Pour Stripe, utiliser une clé `sk_test_…`, un prix et un endpoint webhook du
même compte et mode de test. Vérifier le mode du prix et de l'endpoint dans
Stripe : `price_…` et `whsec_…` ne distinguent pas à eux seuls test et live.
La CI E2E vérifie le préfixe de la clé et que le prix est récurrent et en mode
test ; cela ne vérifie pas l'isolement de toutes les autres ressources.
L'activation de paiements réels en production nécessite une décision et une
recette séparées ; le MVP actuel utilise Stripe en mode test.

Pour les autres fournisseurs, utiliser un environnement de test isolé si
disponible et approprié. S'il n'existe pas d'identifiant ou de service de test
adapté, utiliser un double et ne pas raccorder la préproduction au service
live. Désactiver les déclencheurs et les appels payants non nécessaires.

## Variables par environnement

Les cellules décrivent l'origine ou la destination attendue, **pas des valeurs
à copier**. Les variables publiques `NEXT_PUBLIC_*` sont intégrées au build ;
seules des informations publiques peuvent y figurer. Les autres identifiants
sensibles sont réservés au serveur. Consulter
[`.env.example`](../../.env.example) et le [runbook des secrets](secrets.md).

| Variable | Local | CI / E2E | Préproduction | Production |
|---|---|---|---|---|
| `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Instance locale ou projet de test dédié. | Supabase local pour l'E2E ; valeurs locales fictives pour le build d'accessibilité. | Projet de recette distinct. | Projet de production. |
| `SUPABASE_SERVICE_ROLE_KEY` | Clé serveur du projet de test local ou dédié. | Clé du Supabase local, obtenue au démarrage E2E. | Secret serveur du projet de recette. | Secret serveur du projet de production. |
| `GCP_PROJECT_ID` | Projet de développement isolé. | Projet BigQuery dédié aux fixtures, via `E2E_GCP_PROJECT_ID`. | Projet de recette distinct. | Projet de production. |
| `BQ_LOCATION` | Région du dataset de développement ; `europe-west9` visée. | `europe-west9` pour l'E2E. | Région réelle du dataset de recette, `europe-west9` visée. | Région réelle du dataset de production, `europe-west9` visée. |
| `GCS_BUCKET_RAW` | Bucket de développement isolé pour les jobs qui en ont besoin. | Non requis par l'E2E web ; utiliser un bucket de test dédié pour les tests de jobs. | Bucket de recette distinct. | Bucket de production. |
| `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` | Instance et identité de test ; lecture seule pour le web. | Non configurés dans le job E2E web actuel ; doubles ou instance de test pour les tests concernés. | Instance et identité de recette distinctes ; lecture seule pour le web. | Instance et identité de production ; lecture seule pour le web. |
| `NEO4J_DATABASE` | Facultatif ; base de test si nécessaire. | Facultatif pour les tests concernés. | Facultatif ; base de recette si nécessaire. | Facultatif ; base de production si nécessaire. |
| `STRIPE_SECRET_KEY` | Clé `sk_test_…` du compte de test dédié. | Secret GitHub `STRIPE_TEST_SECRET_KEY` en mode test. | Secret du compte de test dédié, jamais une clé live. | Secret propre à l'environnement Stripe autorisé ; live seulement après validation explicite. |
| `STRIPE_PRICE_PRO` | Prix récurrent du compte de test. | `E2E_STRIPE_PRICE_PRO` : prix récurrent de test. | Prix du compte de test associé à la clé. | Prix correspondant au compte et au mode autorisés. |
| `STRIPE_WEBHOOK_SECRET` | Secret de l'endpoint test ou de Stripe CLI. | Secret du transfert Stripe CLI créé pour l'E2E. | Secret de l'endpoint de recette en mode test. | Secret de l'endpoint de production, adapté au mode autorisé. |
| `APP_URL` | Origine locale, par exemple `http://127.0.0.1:3000`. | `http://127.0.0.1:3000` pour l'E2E. | Origine HTTPS canonique de recette. | Origine HTTPS canonique de production. |
| `LLM_API_KEY` | Double ou identifiant de test isolé si disponible. | Double pour les tests unitaires. | Double ou identifiant de test isolé si disponible ; aucun accès live. | Secret de production pour le job d'extraction autorisé. |
| `DATAFORSEO_LOGIN`, `DATAFORSEO_PASSWORD` | Double ou identifiants de test isolés si disponibles. | Doubles pour les tests unitaires. | Doubles ou identifiants de test isolés si disponibles ; aucun accès live. | Secrets de production pour les jobs autorisés. |

`NEO4J_DATABASE` doit être omis plutôt que vide. L'application BigQuery
utilise les identifiants ADC et non une clé JSON embarquée ; affecter une
identité différente à chaque environnement et restreindre ses droits au projet
concerné. Le web n'a pas besoin des secrets LLM ou DataForSEO. Les budgets,
buckets, identités et noms de secrets du script de déploiement des jobs sont
documentés dans la section « Jobs Cloud Run et planification » du
[README](../../README.md#jobs-cloud-run-et-planification) ; les configurer
séparément pour chaque environnement, sans partager les secrets de production.

Pour l'E2E, l'environnement GitHub `e2e` fournit aussi
`E2E_GCP_WORKLOAD_IDENTITY_PROVIDER` et `E2E_GCP_SERVICE_ACCOUNT`. Les droits
de cette identité doivent porter uniquement sur le projet BigQuery de test :
le workflow crée ou modifie ses tables de fixtures. Vérifier le projet avant
approbation ; le contrôle actuel exige une valeur non vide mais ne prouve pas
qu'il s'agit d'un projet isolé. Le détail figure dans
[l'architecture web](../02-architecture/web.md#test-de-bout-en-bout).

## Procédure de promotion

1. **Préparer** : ouvrir une branche dédiée et une pull request. Identifier le
   commit, les migrations, les dépendances externes, les configurations et la
   dernière version de production saine. Vérifier la compatibilité ascendante
   et la possibilité de retour arrière des changements de données.
2. **Contrôler la CI** : examiner et attendre le succès des contrôles requis
   avant fusion ; si une protection de branche manque, appliquer cette règle
   manuellement. Un test E2E ignoré, notamment pour une PR issue d'un fork,
   n'est pas un test réussi : l'exécuter dans un contexte de confiance avant
   toute promotion nécessitant ce contrôle.
3. **Déployer en recette** : construire à partir du commit candidat, configurer
   les variables de préproduction et contrôler l'isolement des projets,
   domaines, prix, webhooks, identités et secrets. Vérifier la règle sans clé
   live, les RLS, les migrations et le parcours web et données décrit dans le
   [guide web](deploiement-web.md#préparation-commune). Noter la version et les
   résultats sans enregistrer de secrets.
4. **Autoriser la production** : après validation de la recette, du responsable
   de mise en production et du plan de retour arrière, publier le même commit
   approuvé avec les paramètres propres à la production. Ne jamais promouvoir
   les secrets ou les données de recette. Les valeurs `NEXT_PUBLIC_*` sont
   figées au build : si elles diffèrent, reconstruire pour la production à
   partir du même commit et identifier le nouvel artefact ; ne pas prétendre
   que le bundle de recette est identique. Pour les autres artefacts, privilégier
   un digest immuable déjà vérifié.
5. **Vérifier après bascule** : contrôler le domaine, la connexion, les
   permissions, les analyses, les journaux et la réception des webhooks du mode
   autorisé, sans paiement réel de test. Surveiller les erreurs ; en cas
   d'échec, suspendre les promotions et appliquer le
   [retour arrière web](deploiement-web.md#retour-arrière). Un rollback
   applicatif n'annule ni les migrations, ni les données, ni les événements.

Le workflow de publication de l'image du pipeline est déclenché par un push
sur `main` et n'attend pas explicitement la CI dans sa définition. Une image
publiée n'est donc pas automatiquement une version approuvée ; ne la déployer
qu'après vérification du commit, de la CI et de la recette. Le workflow de
déploiement web et les validations automatiques de promotion restent à créer.
