# Vantedge-legal-intelligence

## Dépendances et analyse de sécurité

Dependabot vérifie chaque semaine pip, uv, npm et les GitHub Actions. L'entrée
uv maintient aussi `pipeline/uv.lock` ; les entrées pip et uv peuvent proposer
des mises à jour similaires et doivent être revues ensemble.

Le workflow CodeQL analyse Python et JavaScript/TypeScript sur les push vers
`main`, les pull requests et chaque semaine. Il nécessite l'activation de
GitHub Code Scanning et les droits correspondants ; vérifier la compatibilité
avec une éventuelle configuration CodeQL par défaut déjà activée sur le dépôt.

## Image du pipeline

Construire depuis la racine du dépôt, qui est le contexte Docker :

```sh
docker build -f pipeline/Dockerfile -t vil-pipeline:local .
docker run --rm vil-pipeline:local --help
```

L'image utilise Python 3.12, les dépendances verrouillées avec `uv sync
--frozen` et un utilisateur non root (UID 10001). Elle contient les migrations
SQL, les prompts, les contraintes Neo4j et les jeux de référence utilisés par
les commandes du pipeline. Les fichiers d'entrée et de sortie doivent être
montés avec des permissions compatibles ; les rapports écrits uniquement dans
le conteneur sont perdus à sa suppression. Fournir les variables, identifiants
et droits nécessaires au runtime sans inclure de secrets dans l'image.

Sur chaque push vers `main`, le workflow de publication construit et teste
l'image avant de la pousser sous le tag du SHA du commit vers
`europe-west9-docker.pkg.dev/<projet>/<dépôt>/vil-pipeline`. Créer d'abord le
dépôt Docker Artifact Registry en `europe-west9`, puis configurer les variables
GitHub Actions `GCP_PROJECT_ID`, `ARTIFACT_REGISTRY_REPOSITORY`,
`GCP_WORKLOAD_IDENTITY_PROVIDER` et `GCP_ARTIFACT_REGISTRY_SERVICE_ACCOUNT`.
Le fournisseur Workload Identity doit autoriser ce dépôt et limiter l'accès à
la branche `main` ; le compte de service doit pouvoir publier dans le dépôt
Artifact Registry. Aucun compte de service JSON n'est nécessaire.

## Jobs Cloud Run et planification

`scripts/deploy_jobs.sh` crée ou actualise six jobs en `europe-west9` :
`vil-load-corpus`, `vil-extract-entities`, `vil-collect-volumes`,
`vil-load-raw-market`, `vil-dbt` (`dbt build`) et `vil-sync-graph`. L'image
contient le projet dbt, ses dépendances et le module graphe. Le job corpus lit
une archive LEGI dans un bucket GCS monté en lecture seule ; le chargement
utilise par défaut le livre I. Les répertoires dbt et les fichiers temporaires
sont éphémères. Le profil dbt `oauth` utilise les identifiants ADC du compte
Cloud Run, sans clé JSON.

Avant le déploiement :

- Activer Cloud Run, Cloud Scheduler, Secret Manager, BigQuery et Cloud Storage ;
  créer les datasets, tables et contraintes Neo4j requis et publier l'image.
- Créer un compte de service **dédié aux jobs** et un compte distinct dédié à
  Scheduler. Accorder au premier les droits BigQuery nécessaires pour lire les
  sources, exécuter des requêtes, écrire dans `raw`, `staging`, `marts` et
  `ops.pipeline_runs`, lire le corpus, lire/écrire les archives marché et
  accéder aux versions de secrets utilisées. Le profil dbt doit pouvoir créer
  et remplacer ses modèles et exécuter ses tests. Accorder à ce compte l'accès
  Neo4j requis ; limiter les droits aux ressources concernées.
- Le déployeur doit pouvoir déployer les jobs, modifier leurs politiques IAM,
  créer et modifier les déclencheurs Scheduler, lister ces déclencheurs et
  utiliser les deux comptes de service (`iam.serviceAccounts.actAs`). L'agent
  de service Cloud Scheduler doit être correctement provisionné. Le script
  attribue `roles/run.invoker` au compte Scheduler sur les deux jobs planifiés.
  Le compte des jobs ayant accès à tous les secrets listés, isoler davantage les
  identités si cette portée dépasse la politique de sécurité.
- Créer les secrets dans le projet de déploiement. Ils sont montés en fichiers
  et lus seulement par le job concerné ; leurs valeurs ne doivent pas être
  fournies au script ni inscrites dans l'image ou la ligne de commande.

Configurer les variables suivantes dans l'environnement du déployeur, puis
exécuter `bash scripts/deploy_jobs.sh` :

| Variable | Contenu |
|---|---|
| `PROJECT_ID`, `IMAGE` | Projet et image Artifact Registry publiée (préférer un digest immuable). |
| `JOB_SERVICE_ACCOUNT`, `SCHEDULER_SERVICE_ACCOUNT` | Adresses des deux comptes dédiés. |
| `CORPUS_BUCKET`, `CORPUS_OBJECT` | Nom du bucket et chemin relatif de l'archive LEGI. |
| `GCS_BUCKET_RAW` | Bucket des archives DataForSEO. |
| `EXTRACTION_MAX_COST`, `EXTRACTION_COST_PER_CALL` | Budget et coût estimé par appel LLM. |
| `VOLUMES_MAX_COST`, `VOLUMES_COST_PER_CALL` | Budget et coût estimé par mot-clé DataForSEO. |
| `LLM_SECRET` | Identifiant du secret de clé API LLM. |
| `DATAFORSEO_LOGIN_SECRET`, `DATAFORSEO_PASSWORD_SECRET` | Identifiants des secrets DataForSEO. |
| `NEO4J_URI_SECRET`, `NEO4J_USER_SECRET`, `NEO4J_PASSWORD_SECRET` | Identifiants des secrets de connexion Neo4j. |
| `SECRET_VERSION` | Facultatif : `latest` par défaut, ou numéro de version commun aux secrets. |

Les limites de coût sont **par tentative**, non un plafond global : un nouvel
essai peut entraîner des coûts supplémentaires. Cloud Run autorise une nouvelle
tentative par tâche, avec un délai maximal d'une heure par tentative. Scheduler
appelle l'API Cloud Run avec OAuth, sans nouvelle tentative Scheduler : collecte
le 1er du mois à 03:00 UTC, graphe chaque lundi à 04:00 UTC. Les autres jobs
sont lancés explicitement après vérification de leurs prérequis.

**Exploitation :** Scheduler ne verrouille pas le job jusqu'à sa fin. Avant
une synchronisation manuelle ou une reconstruction dbt des marts, suspendre
le déclencheur graphe, vérifier qu'aucune synchronisation ni reconstruction
des marts n'est active, puis maintenir l'exclusion jusqu'à la fin avant de
réactiver le déclencheur. Réserver les lancements manuels aux opérateurs qui
appliquent cette procédure ; coordonner aussi toute autre écriture des marts.
Pour le premier déploiement, choisir une fenêtre hors déclenchement et vérifier
qu'aucun job concurrent n'est actif. Cette procédure ne constitue pas un
verrou technique : deux lancements simultanés non coordonnés restent possibles.
Un échec de déploiement peut laisser des ressources partiellement mises à jour ;
corriger la cause et relancer, puis contrôler les configurations et les horaires.

## Tests d'intégration Neo4j

Avec Docker et Docker Compose disponibles :

```sh
make neo4j-test-up
NEO4J_TEST_URI=bolt://127.0.0.1:17687 uv run --project pipeline --extra dev pytest -o addopts= pipeline/tests/integration
docker compose -p vantedge-neo4j-test -f docker-compose.test.yml down
```

Le service Community est éphémère, sans authentification et accessible
uniquement sur la boucle locale : il est réservé aux tests et ses données sont
perdues à l'arrêt du conteneur. `make neo4j-test-up` attend que Neo4j réponde.
Les tests sont ignorés si `NEO4J_TEST_URI` n'est pas défini ; une URI vide ou
inaccessible provoque une erreur. Ne jamais diriger ces tests vers une base de
production : ils créent et suppriment leurs propres nœuds de test.

## Contraintes Neo4j

Depuis la racine du dépôt, après avoir configuré `NEO4J_URI`, `NEO4J_USER` et
`NEO4J_PASSWORD` pour une identité autorisée à créer et consulter les contraintes :

```sh
uv run --project pipeline python -m vil_pipeline.graph.apply_constraints
```

Le module lit `graph/constraints.cypher` dans l'arborescence du dépôt et applique
les cinq contraintes explicites de l'ontologie. Il vérifie ensuite leur présence,
y compris si un nom déjà utilisé a empêché leur création. Une erreur est
propagée ; les contraintes déjà créées restent en place et une nouvelle
exécution est possible. L'unicité ne rend pas les propriétés obligatoires.

## Export des données du graphe

Depuis la racine du dépôt, avec les identifiants Google Cloud ADC et les droits
de lecture sur le dataset marts, utiliser les fonctions de `graph.export` :

```python
from google.cloud import bigquery
from graph.export import iter_batches, iter_table_batches

client = bigquery.Client(project="mon-projet")
dataset = bigquery.DatasetReference("mon-projet", "marts")
for lot in iter_batches(client, dataset, batch_size=1000):
    print(lot.table, len(lot.rows))

# Reprise à la frontière d'un lot dim_article préalablement traité :
# iter_table_batches(client, dataset, "dim_article", page_token=curseur_dim_article)
```

Chaque lot et chaque ligne sont des modèles Pydantic ; `next_page_token` vaut
`None` en fin de table. Les lots vides ne sont pas émis. L'export lit seulement
les colonnes nécessaires et conserve les versions, les identifiants de contexte
et les clés de relation ; il ne crée pas les nœuds ni les relations Neo4j.
Les chapitres relient les titres aux articles, les extractions relient les
notions aux versions puis aux articles et les contextes fournissent le pays
et la langue des requêtes. Le consommateur doit résoudre ces liens, choisir
la version d'article à projeter et vérifier les clés de métriques et de SERP :
leurs grains marts incluent le contexte pays/langue, contrairement aux clés de
l'ontologie. Une requête sans intention, un article sans chapitre et les
dimensions sans relation sont conservés.

La lecture utilise les pages de `tabledata.list`, sans garantir un instantané
cohérent entre pages ou entre tables : ne pas reconstruire les marts pendant
l'export et ne reprendre un curseur que sur la même table inchangée. Les erreurs
BigQuery, les colonnes manquantes et les données invalides interrompent la
lecture ; les lots déjà livrés ne sont pas annulés.

## Synchronisation du graphe

Après application des contraintes Neo4j et validation des tests dbt (unicité et
intégrité référentielle), depuis la racine du dépôt :

```python
from google.cloud import bigquery
from neo4j import GraphDatabase
from graph.sync import sync_graph

client = bigquery.Client(project="mon-projet")
dataset = bigquery.DatasetReference("mon-projet", "marts")
with GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "mot-de-passe")) as driver:
    stats = sync_graph(driver, client, dataset, batch_size=1000)
    print(stats)
```

Le compte BigQuery doit pouvoir lire les marts, exécuter des requêtes et écrire
dans `ops.pipeline_runs` ; `ops_dataset` permet de choisir un autre dataset
d'exploitation. Les nœuds sont écrits avant les relations avec `UNWIND` et
`MERGE`, dans une transaction Neo4j par lot. Les compteurs du journal indiquent
les lignes traitées et non les créations effectives. Les erreurs sont propagées,
y compris si l'écriture du journal échoue ; si la synchronisation et le journal
échouent tous deux, les deux erreurs sont conservées.

La version d'article en vigueur est préférée ; sinon, la plus récente est
retenue, avec l'identifiant de version comme départage. Les métriques et SERP
dont le contexte ne correspond pas à leur requête échouent au lieu de fusionner
des contextes différents. Les références manquantes ou les correspondances
multiples interrompent le lot. Il n'y a pas d'instantané commun ni de transaction
entre BigQuery et Neo4j : ne pas reconstruire les marts durant une exécution ;
après un échec, les lots déjà validés restent en place et peuvent être rejoués.

La synchronisation ajoute et met à jour, mais **ne supprime pas** les éléments
absents des marts. Une ancienne relation, notamment une intention remplacée, peut
donc subsister. Exécuter un seul synchroniseur à la fois : l'ontologie n'impose
pas de contraintes d'unicité sur tous les types de nœuds.

## Contrôle de cohérence du graphe

Avec les identifiants ADC BigQuery et `NEO4J_URI`, `NEO4J_USER` et
`NEO4J_PASSWORD` configurés :

```sh
uv run --project pipeline vil-pipeline check-graph-consistency \
  --project-id mon-projet --dataset marts
```

Le contrôle compare les nombres de notions, articles et requêtes, ainsi que
chaque type de relation et les trois niveaux `CONTIENT`. Les relations attendues
sont dédupliquées selon leurs clés de graphe : plusieurs extractions d'une même
notion vers des versions d'un même article comptent pour une seule relation.
Les types ou extrémités de relations inattendus et certains liens ou contextes
marts invalides sont signalés. Les écarts, erreurs de lecture et données
invalides donnent un code de sortie non nul.

Exécuter le contrôle hors synchronisation et reconstruction des marts : il n'y
a pas d'instantané commun entre BigQuery et Neo4j. Une égalité des comptes ne
garantit pas l'égalité des identifiants, propriétés ou relations individuels.
Comme la synchronisation ne supprime pas les données anciennes, elle peut
laisser des écarts qui nécessitent une intervention.

## Requêtes de graphe

Les requêtes Cypher de [`graph/queries/`](graph/queries/) sont en lecture seule
et utilisables avec le pilote Neo4j, en transmettant leurs paramètres séparément :

| Fichier | Paramètres | Résultat |
|---|---|---|
| [`notions_voisines.cypher`](graph/queries/notions_voisines.cypher) | `notion_id` | Notions partageant au moins un article, classées par nombre d'articles communs décroissant ; chaque article est compté une fois. |
| [`notions_connectees.cypher`](graph/queries/notions_connectees.cypher) | `limite` (entier ≥ 0) | Notions classées par degré décroissant. Le degré compte toutes les relations incidentes distinctes, entrantes ou sortantes ; une boucle compte une fois. |
| [`chemins_notion_articles.cypher`](graph/queries/chemins_notion_articles.cypher) | `notion_id` | Tous les chemins simples vers les articles directs et ceux atteints par 1 à 3 liens `RENVOIE_A`, `MODIFIE` ou `ABROGE` orientés. Le champ `chemin` est un objet chemin Neo4j. |
| [`clusters_situations.cypher`](graph/queries/clusters_situations.cypher) | Aucun | Une liste dédupliquée de notions par situation de vie non vide ; une notion peut figurer dans plusieurs groupes. |

Pour les requêtes paramétrées par `notion_id`, une notion inconnue ou sans
correspondance ne produit aucune ligne. Les chemins ne répètent pas de nœud,
mais un article peut apparaître plusieurs fois s'il est atteint par des chemins
différents. La recherche de tous les chemins peut être coûteuse dans un graphe
dense, malgré la limite de trois liens normatifs.

## Migrations BigQuery

Depuis `pipeline/`, exécuter `uv run python -m vil_pipeline.cli migrate` avec
`GCP_PROJECT_ID`, `BQ_LOCATION` et des identifiants Google Cloud Application
Default Credentials configurés. Les options `--project-id` et `--location`
permettent aussi de préciser le projet et la région. La commande crée les
datasets `raw` et `ops` si nécessaire, puis applique les migrations manquantes
dans l'ordre des noms de fichiers et les enregistre dans `ops.schema_migrations`.

Le client serveur de l'application web
(`apps/web/src/lib/server/bigquery.ts`) utilise les identifiants ADC du runtime :
déployer l'application sous l'identité
`sa-app-reader@<GCP_PROJECT_ID>.iam.gserviceaccount.com`, sans clé JSON. Chaque
requête utilise des paramètres BigQuery, valide les lignes avec Zod et est
limitée à 15 secondes et 1 000 lignes.

Les extractions sont stockées dans `raw.entites_extraites` et les exécutions
dans `ops.pipeline_runs` ; `compteurs` contient un objet JSON et `cout_estime`
est un montant numérique dans la devise retenue par le pipeline. Les clés
`extraction_id` et `run_id` sont des identifiants logiques : BigQuery n'impose
pas leur unicité. Les scores de confiance (de 0 à 1) et les statuts de validation
(`AUTO`, `A_REVOIR`, `VALIDE`, `REJETE`) doivent être contrôlés avant insertion.

Les jobs de `vil_pipeline.jobs` et la synchronisation graphe utilisent
`tracked_run` : une ligne `RUNNING` est créée avant leur exécution, puis mise à
jour avec la date de fin, le statut, les compteurs, le coût estimé et l'erreur
éventuelle. Un arrêt brutal peut laisser une ligne `RUNNING` ; aucune clôture
automatique n'est garantie. Si le démarrage du journal échoue, le job ne
démarre pas ; si sa finalisation échoue, l'erreur est propagée, ainsi que celle
du job s'il a également échoué. Pour les exceptions, le journal conserve leurs
types, y compris dans les groupes, mais pas leurs messages. Les exceptions
propagées et les anciennes lignes peuvent toutefois contenir des données
sensibles : protéger les logs et restreindre l'accès au dataset `ops`.

Les dry-runs sont également journalisés : même `load-corpus --dry-run` exige
`GCP_PROJECT_ID`, les identifiants ADC et le droit d'écrire dans
`ops.pipeline_runs`, mais ne modifie pas les tables métier. Exécuter d'abord les
migrations et accorder au compte du job les droits BigQuery nécessaires pour
créer les jobs et insérer puis modifier le journal. La commande de migration et
l'application des contraintes Neo4j sont des opérations de configuration, pas
des jobs journalisés ; la migration doit notamment pouvoir créer le journal.

## Qualité et fraîcheur dbt

Avec les identifiants ADC et `GCP_PROJECT_ID` configurés, depuis la racine :

```sh
uv run --project pipeline --extra dbt dbt deps --project-dir dbt --profiles-dir dbt
uv run --project pipeline --extra dbt dbt build --select +ops_qualite --project-dir dbt --profiles-dir dbt
uv run --project pipeline --extra dbt dbt source freshness --project-dir dbt --profiles-dir dbt
```

Les contrôles de fraîcheur avertissent après 30 jours et échouent après 60 jours,
en excluant les dates futures. Ils couvrent `raw.articles`, `raw.article_versions`,
`raw.entites_extraites`, `raw.requetes_intentions`, `raw.dataforseo_volumes`,
`raw.dataforseo_serp` et `ops.extraction_results`. Les dates de chargement des
articles et versions reflètent les insertions ou modifications : une source
inchangée peut être signalée ancienne malgré un pipeline fonctionnel.
`raw.requetes_candidates` ne dispose pas d'horodatage ; `raw.dataforseo_intent`
n'est pas utilisée par les modèles actuels et n'est pas contrôlée.

La vue `ops.ops_qualite` contient trois types de lignes : une par notion sans
requête, une par requête et contexte pays/langue sans collecte de volume
strictement positif depuis 60 jours, et une ligne de taux de quarantaine IA.
Le volume est recherché dans les archives brutes : zéro et `NULL` ne sont pas
des volumes positifs, et une collecte positive antérieure reste valable jusqu'à
son 60e jour même si une collecte plus récente vaut zéro. Les dates futures sont
ignorées. Le taux rapporte les résultats `QUARANTINE` à tous les résultats
d'extraction des 60 derniers jours glissants, bornes incluses ; il vaut `NULL`
si aucun résultat n'existe. La vue n'impose pas de seuil d'alerte sur ce taux.

## Extraction des entités

Appliquer d'abord les migrations, notamment `0005_ops_extraction_results`,
puis depuis `pipeline/` :

```sh
uv run python -m vil_pipeline.cli extract-entities \
  --max-cost 10 --cost-per-call 0.01 --batch-size 100 --dry-run
```

Remplacer les montants d'exemple par des estimations adaptées, dans la même
devise. Sans `--dry-run`, définir aussi `LLM_API_KEY` dans l'environnement.
Le modèle est configurable avec `--model`. Le dry-run lit les articles et
écrit une ligne dans `ops.pipeline_runs`, mais n'appelle pas le LLM et n'écrit
aucune extraction. Son estimation suppose un appel par article, sans relance.

Le budget est vérifié avant chaque appel au client LLM, y compris les relances
de validation. Le coût est une estimation fixe par appel, **pas une garantie
de facturation** : le nombre de tokens, les tarifs réels et les tentatives
HTTP internes au fournisseur peuvent modifier le coût effectif. Un arrêt pour
budget est enregistré avec le statut `BUDGET_EXHAUSTED` et les articles non
terminés restent disponibles pour une prochaine exécution.

Le registre `ops.extraction_results` conserve le JSON et le statut pour chaque
triplet article/version du prompt/modèle, même pour une liste de notions vide.
Les résultats invalides après relance sont conservés en `QUARANTINE` et ne sont
pas retraités automatiquement ; ils nécessitent une revue. Les sorties déjà
présentes dans `raw.entites_extraites` sont également considérées traitées.
Chaque résultat et ses entités sont enregistrés dans une même transaction.
Lancer une seule exécution à la fois pour un même triplet : les clés BigQuery
ne constituent pas des contraintes d'unicité garanties.

## Revue des entités extraites

Depuis `pipeline/`, avec le projet et les identifiants BigQuery configurés :

```sh
uv run python -m vil_pipeline.cli export-review --threshold 0.8 --output revue.csv
uv run python -m vil_pipeline.cli import-review --input revue.csv
```

Le seuil est configurable et strict : l'export inclut les entités dont le statut
est `A_REVOIR` **ou** dont le score est inférieur au seuil, y compris celles
éventuellement déjà validées ou rejetées. Le fichier ne doit pas déjà exister.
Pour chaque décision, renseigner `nouveau_statut` (`A_REVOIR`, `VALIDE` ou
`REJETE`) et `nouveau_valide_par`. Laisser les deux cellules vides pour ignorer
une ligne. Ne pas modifier les colonnes d'origine, notamment le statut et le
validateur initial encodé en JSON.

L'import valide le fichier entier avant toute écriture ; toutes les décisions
sont appliquées dans une transaction. Il échoue si un identifiant est absent ou
dupliqué dans BigQuery, ou si le statut ou le validateur a changé depuis
l'export. Dans ce cas, exporter à nouveau et refaire la revue avant de réimporter.
Le CSV peut contenir des textes non fiables : attention aux formules lors de son
ouverture dans un tableur. Les résultats bruts en quarantaine sont conservés
séparément dans `ops.extraction_results` et ne sont pas inclus dans cet export.
