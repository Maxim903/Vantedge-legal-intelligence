# Déploiement de l'application web

L'[ADR-0007](../adr/0007-hebergement-web.md) propose Cloud Run à Paris ; elle
n'est pas encore acceptée. Ce guide prépare le déploiement, sans présumer
qu'un domaine, un service, une image web ou un workflow de publication existe.
La CI actuelle teste l'application mais ne la déploie pas ; l'image du pipeline
Python n'est pas une image web. Aucun changement de production ne doit précéder
la validation de l'ADR, des accès, des coûts et des contrôles de conformité.

## Préparation commune

1. Utiliser une branche dédiée et une pull request ; ne fusionner qu'après
   succès de la CI requise. Identifier le commit à publier et la version
   précédente connue comme fonctionnelle.
2. Isoler production et préproduction : projets et données Supabase, Stripe,
   BigQuery et Neo4j, secrets, domaines et permissions. Appliquer et vérifier
   les migrations, les politiques RLS et les données de référence requises.
   Prévoir la compatibilité des migrations avec la version précédente.
3. Vérifier les droits de déploiement, le budget, les certificats, les quotas,
   la connectivité vers Supabase, Stripe, BigQuery et Neo4j ainsi que les
   régions et contrats des fournisseurs. Ne jamais utiliser de données ou de
   clés Stripe réelles dans les tests de préproduction.
4. Construire depuis le dépôt complet : les requêtes Cypher sont dans
   [`graph/queries`](../../graph/queries/) et les requêtes SQL dans
   [`apps/web/src/features/analyse/sql`](../../apps/web/src/features/analyse/sql/).
   Depuis `apps/web`, les commandes du projet sont `npm ci`, `npm run build`
   et `npm run start`. Le build doit inclure les fichiers hors de ce dossier
   nécessaires aux imports ; un hébergement exclusivement statique ne convient
   pas. CI utilise Node.js 24.
5. Tester en préproduction les parcours ci-dessous avant toute bascule :
   HTTPS, connexion et retour d'authentification, pages protégées et RLS,
   ouverture d'analyse et quota, données BigQuery, notions liées Neo4j,
   Checkout, portail et réception d'un événement Stripe signé. Vérifier les
   journaux sans y afficher de secrets ni de données personnelles.

## Variables d'environnement

Configurer des valeurs distinctes par environnement. La liste de référence est
[`.env.example`](../../.env.example) ; ne jamais y enregistrer de valeurs
privées. Les variables publiques `NEXT_PUBLIC_*` sont incorporées au bundle
lors de `next build` : les fournir au build et reconstruire si elles changent.
Les variables privées ci-dessous sont réservées au serveur et doivent provenir
d'un gestionnaire de secrets ou de la configuration sécurisée de l'hébergeur.

| Variable | Usage et précautions |
|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | URL publique du projet Supabase de l'environnement. |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Clé publique anon ; la protection des données repose sur l'authentification et les politiques RLS. |
| `SUPABASE_SERVICE_ROLE_KEY` | Clé privilégiée utilisée côté serveur par le webhook Stripe ; secret strictement privé. |
| `GCP_PROJECT_ID` | Projet des requêtes BigQuery. |
| `BQ_LOCATION` | Région du dataset, normalement `europe-west9` ; défaut de l'application si absente. |
| `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` | Connexion et identité Neo4j en lecture seule ; protéger les identifiants. |
| `NEO4J_DATABASE` | Facultatif ; nom de la base si nécessaire. Une valeur vide est invalide. |
| `STRIPE_SECRET_KEY` | Clé API Stripe privée du bon environnement. |
| `STRIPE_WEBHOOK_SECRET` | Secret de signature propre à l'endpoint Stripe. |
| `STRIPE_PRICE_PRO` | Identifiant du prix du plan `pro`, issu du même environnement Stripe. |
| `APP_URL` | Origine HTTPS canonique sans chemin, utilisée pour les retours Checkout et portail. |

La bibliothèque BigQuery utilise les identifiants ADC de l'environnement,
pas une variable contenant une clé JSON. L'identité doit pouvoir créer des
jobs dans le projet et lire les tables `marts` ; les droits doivent rester
limités. `LLM_API_KEY`, les secrets DataForSEO et `GCS_BUCKET_RAW` concernent
les jobs de données et ne sont pas requis par le web. Voir le
[runbook des secrets](secrets.md).

## Domaine et intégrations

1. Choisir et vérifier la propriété du domaine ; configurer les DNS indiqués par
   l'hébergeur, le certificat TLS et le renouvellement. Attendre la propagation
   et la validité du certificat avant la bascule. Ne pas inventer d'adresse IP
   ni modifier les DNS du domaine existant sans plan de retour arrière.
2. Définir l'origine canonique dans `APP_URL`. Configurer l'URL du site et les
   URL de redirection autorisées dans Supabase, dont
   `https://<domaine>/auth/callback`, ainsi que les paramètres des fournisseurs
   d'authentification activés. Les domaines de préproduction doivent avoir leur
   propre configuration.
3. Configurer l'endpoint Stripe
   `https://<domaine>/api/stripe/webhook` avec son secret de signature et les
   événements `checkout.session.completed`, `customer.subscription.updated`
   et `customer.subscription.deleted`. Tester avec Stripe en mode test avant
   toute activation réelle ; vérifier la réception et les nouvelles tentatives.
4. Contrôler le domaine public, les redirections, les cookies, les en-têtes
   HTTPS et l'absence de cache partagé de pages ou réponses personnalisées.
   Documenter les valeurs effectives et les contacts d'exploitation sans
   consigner de secrets.

## Option proposée : Cloud Run

1. Créer et tester une **image web** Node.js séparée, non root, qui démarre le
   serveur Next.js sur `0.0.0.0` et le port `PORT` fourni par Cloud Run.
   Inclure les sources nécessaires au build et ne pas inclure de fichiers
   d'identifiants ou de secrets dans l'image. Le
   [`.dockerignore`](../../.dockerignore) actuel exclut l'application web :
   prévoir un contexte adapté sans exposer de secrets. Publier une image
   identifiée par digest dans Artifact Registry ; sa création et son workflow
   restent à implémenter et vérifier.
2. Créer le service dans `europe-west9` avec l'identité dédiée
   `sa-app-reader`. Lui accorder la lecture des `marts`, la création de jobs
   BigQuery et l'accès aux seuls secrets nécessaires. Utiliser Secret Manager
   pour injecter les secrets en variables serveur, avec versions épinglées ;
   vérifier que l'identité de déploiement peut utiliser le compte de service.
   Ne pas définir `GOOGLE_APPLICATION_CREDENTIALS` avec une clé privée.
3. Configurer instances, concurrence, timeout, logs et surveillance selon les
   résultats de charge ; vérifier le comportement du cache Next.js avec
   plusieurs instances et les éventuelles données sensibles. Déployer d'abord
   dans un service de préproduction, puis valider la révision de production
   avant d'y diriger le trafic.
4. Pour le domaine de production, utiliser le
   [load balancer HTTPS externe avec backend serverless](https://cloud.google.com/run/docs/mapping-custom-domains)
   et certificat, puis appliquer les DNS fournis. Le mapping direct Cloud Run
   est en préversion et ne couvre pas `europe-west9`. Examiner les restrictions
   d'ingress pour éviter un accès non souhaité qui contournerait les contrôles
   du load balancer. Le caractère global du load balancer doit être évalué
   séparément des contraintes de résidence.
5. Après la bascule, vérifier les parcours de préproduction sur le domaine de
   production avec des comptes autorisés, les logs et les alertes, puis noter le
   digest et la révision. Ne pas créer de paiement réel pour un simple test.

## Alternative : Vercel

Si l'ADR retient finalement Vercel, configurer un projet Next.js pointant vers
`apps/web`, Node.js 24 et l'accès aux fichiers du dépôt hors de ce répertoire ;
vérifier que le build inclut les requêtes Cypher. Paramétrer les variables par
environnement et les valeurs publiques au build. Dans **Settings → Functions**,
choisir `cdg1` (Paris), puis vérifier les éventuelles surcharges et régions de
repli ; les nouveaux projets utilisent `iad1` par défaut. CDN et middleware
restent à analyser séparément pour la localisation.

Avant production, mettre au point et tester une fédération d'identité Google
permettant au client BigQuery d'obtenir des ADC pour `sa-app-reader`, sans clé
longue durée ; aucune configuration de fédération Vercel n'est fournie ici.
Configurer le domaine et TLS dans Vercel puis effectuer les vérifications
communes. Prévoir une promotion seulement après les contrôles requis : une
intégration Git ne garantit pas à elle seule que la CI a terminé avant
publication.

## Retour arrière

1. Suspendre toute promotion et identifier la dernière révision ou le dernier
   déploiement sain. Vérifier sa compatibilité avec les migrations et données
   actuelles, l'état des secrets et l'accès aux services ; le retour du code ne
   restaure ni les données, ni les migrations, ni les événements Stripe.
2. **Cloud Run** : dans la région et le projet concernés, sélectionner dans
   l'historique une révision saine et lui attribuer 100 % du trafic. Par CLI,
   après avoir renseigné `SERVICE`, `PROJECT_ID` et `REVISION` :

   ```sh
   gcloud run revisions list --service="$SERVICE" \
     --project="$PROJECT_ID" --region=europe-west9
   gcloud run services update-traffic "$SERVICE" --to-revisions="$REVISION=100" \
     --project="$PROJECT_ID" --region=europe-west9
   ```

   Le changement n'est pas instantané pour les requêtes en cours et ne
   revalide pas les dépendances. Contrôler les versions de secrets utilisées
   par la révision et le routage des déploiements suivants.
3. **Vercel** : dans le projet, utiliser **Instant Rollback**, choisir un
   déploiement de production éligible et vérifier les domaines concernés.
   Les variables de l'ancien déploiement ne sont pas actualisées ; la
   réaffectation automatique des domaines de production est désactivée après
   rollback et doit être rétablie explicitement lorsque l'incident est résolu.
4. Retester HTTPS, connexion, analyse et webhook signé ; surveiller erreurs et
   retries Stripe. Si le domaine ou le certificat lui-même est en cause,
   restaurer séparément la configuration DNS/TLS précédente en tenant compte
   de sa propagation. Consigner l'incident et avertir les responsables.

Références : [rollback Cloud Run](https://cloud.google.com/run/docs/rollouts-rollbacks-traffic-migration),
[rollback Vercel](https://vercel.com/docs/instant-rollback),
[régions Vercel Functions](https://vercel.com/docs/functions/configuring-functions/region).
