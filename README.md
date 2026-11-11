# Vantedge-legal-intelligence

## Migrations BigQuery

Depuis `pipeline/`, exécuter `uv run python -m vil_pipeline.cli migrate` avec
`GCP_PROJECT_ID`, `BQ_LOCATION` et des identifiants Google Cloud Application
Default Credentials configurés. Les options `--project-id` et `--location`
permettent aussi de préciser le projet et la région. La commande crée les
datasets `raw` et `ops` si nécessaire, puis applique les migrations manquantes
dans l'ordre des noms de fichiers et les enregistre dans `ops.schema_migrations`.

Les extractions sont stockées dans `raw.entites_extraites` et les exécutions
dans `ops.pipeline_runs` ; `compteurs` contient un objet JSON et `cout_estime`
est un montant numérique dans la devise retenue par le pipeline. Les clés
`extraction_id` et `run_id` sont des identifiants logiques : BigQuery n'impose
pas leur unicité. Les scores de confiance (de 0 à 1) et les statuts de validation
(`AUTO`, `A_REVOIR`, `VALIDE`, `REJETE`) doivent être contrôlés avant insertion.

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