#!/usr/bin/env bash

set -euo pipefail

: "${PROJECT_ID:?Définissez PROJECT_ID avec le project ID GCP.}"

command -v bq >/dev/null 2>&1 || {
  printf 'Erreur : bq doit être installé.\n' >&2
  exit 1
}

raw_dataset=${RAW_DATASET:-raw}
staging_dataset=${STAGING_DATASET:-staging}
marts_dataset=${MARTS_DATASET:-marts}
ops_dataset=${OPS_DATASET:-ops}

# raw conserve les payloads sources et le corpus juridique brut versionné.
bq mk --dataset --force \
  --location=europe-west9 \
  --description="Corpus juridique brut versionné et payloads sources." \
  --label=layer:raw \
  --label=managed_by:script \
  "${PROJECT_ID}:${raw_dataset}"

# staging contient les données nettoyées, typées et dédupliquées, reconstructibles depuis raw.
bq mk --dataset --force \
  --location=europe-west9 \
  --description="Données nettoyées, typées et dédupliquées, reconstructibles depuis raw." \
  --label=layer:staging \
  --label=managed_by:script \
  "${PROJECT_ID}:${staging_dataset}"

# marts contient le modèle analytique destiné à l'application et à Neo4j.
bq mk --dataset --force \
  --location=europe-west9 \
  --description="Modèle analytique en étoile destiné à l'application et à Neo4j." \
  --label=layer:marts \
  --label=managed_by:script \
  "${PROJECT_ID}:${marts_dataset}"

# ops conserve le suivi d'exécution, les coûts et les évaluations de qualité.
bq mk --dataset --force \
  --location=europe-west9 \
  --description="Journal du pipeline, coûts et évaluations de qualité." \
  --label=layer:ops \
  --label=managed_by:script \
  "${PROJECT_ID}:${ops_dataset}"
