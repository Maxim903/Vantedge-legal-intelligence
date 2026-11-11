#!/usr/bin/env bash

set -euo pipefail

: "${PROJECT_ID:?Définissez PROJECT_ID dans l'environnement avec l'identifiant du projet GCP.}"

command -v gcloud >/dev/null 2>&1 || {
  printf 'Erreur : gcloud doit être installé.\n' >&2
  exit 1
}

apis=(
  bigquery.googleapis.com
  storage.googleapis.com
  secretmanager.googleapis.com
  run.googleapis.com
  cloudscheduler.googleapis.com
  artifactregistry.googleapis.com
  iam.googleapis.com
  monitoring.googleapis.com
  logging.googleapis.com
)

gcloud services enable "${apis[@]}" --project="$PROJECT_ID"
