#!/usr/bin/env bash

set -euo pipefail

# Les comptes utilisent les identités IAM directement ; aucune clé JSON n'est créée ni exportée.
: "${PROJECT_ID:?Définissez PROJECT_ID avec le project ID GCP.}"
: "${RAW_DATASET:?Définissez RAW_DATASET avec le nom du dataset raw.}"
: "${STAGING_DATASET:?Définissez STAGING_DATASET avec le nom du dataset staging.}"
: "${OPS_DATASET:?Définissez OPS_DATASET avec le nom du dataset ops.}"
: "${MARTS_DATASET:?Définissez MARTS_DATASET avec le nom du dataset marts.}"
: "${BUCKET_NAME:?Définissez BUCKET_NAME avec le nom du bucket GCS, sans gs://.}"

command -v gcloud >/dev/null 2>&1 || {
  printf 'Erreur : gcloud doit être installé.\n' >&2
  exit 1
}

command -v bq >/dev/null 2>&1 || {
  printf 'Erreur : bq doit être installé.\n' >&2
  exit 1
}

service_accounts=(
  sa-ingestion
  sa-app-reader
  sa-neo4j-sync
)

ensure_service_account() {
  local account=$1
  local email="${account}@${PROJECT_ID}.iam.gserviceaccount.com"

  if ! gcloud iam service-accounts describe "$email" \
    --project="$PROJECT_ID" >/dev/null 2>&1; then
    gcloud iam service-accounts create "$account" \
      --display-name="$account" \
      --project="$PROJECT_ID"
  fi
}

for account in "${service_accounts[@]}"; do
  ensure_service_account "$account"
done

ingestion="serviceAccount:sa-ingestion@${PROJECT_ID}.iam.gserviceaccount.com"
app_reader="serviceAccount:sa-app-reader@${PROJECT_ID}.iam.gserviceaccount.com"
neo4j_sync="serviceAccount:sa-neo4j-sync@${PROJECT_ID}.iam.gserviceaccount.com"

# Data Editor est limité aux datasets raw, staging et ops pour écrire les données d'ingestion.
for dataset in "$RAW_DATASET" "$STAGING_DATASET" "$OPS_DATASET"; do
  bq add-iam-policy-binding "${PROJECT_ID}:${dataset}" \
    --member="$ingestion" \
    --role=roles/bigquery.dataEditor
done

# Object Creator autorise l'ajout d'objets dans le bucket sans leur donner accès en lecture.
gcloud storage buckets add-iam-policy-binding "gs://${BUCKET_NAME}" \
  --member="$ingestion" \
  --role=roles/storage.objectCreator

# Object Viewer autorise la lecture des objets du bucket pour les besoins d'ingestion.
gcloud storage buckets add-iam-policy-binding "gs://${BUCKET_NAME}" \
  --member="$ingestion" \
  --role=roles/storage.objectViewer

# Data Viewer limite la lecture BigQuery de ces comptes au dataset marts.
for member in "$app_reader" "$neo4j_sync"; do
  bq add-iam-policy-binding "${PROJECT_ID}:${MARTS_DATASET}" \
    --member="$member" \
    --role=roles/bigquery.dataViewer
done

# Job User autorise l'exécution de jobs BigQuery dans le projet pour ces deux comptes.
for member in "$app_reader" "$neo4j_sync"; do
  gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="$member" \
    --role=roles/bigquery.jobUser \
    --quiet
done
