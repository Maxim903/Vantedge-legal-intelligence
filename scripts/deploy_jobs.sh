#!/usr/bin/env bash
set -euo pipefail

: "${PROJECT_ID:?Définissez PROJECT_ID.}"
: "${IMAGE:?Définissez IMAGE avec une image Artifact Registry à déployer.}"
: "${JOB_SERVICE_ACCOUNT:?Définissez JOB_SERVICE_ACCOUNT.}"
: "${SCHEDULER_SERVICE_ACCOUNT:?Définissez SCHEDULER_SERVICE_ACCOUNT.}"
: "${GCS_BUCKET_RAW:?Définissez GCS_BUCKET_RAW.}"
: "${CORPUS_BUCKET:?Définissez CORPUS_BUCKET.}"
: "${CORPUS_OBJECT:?Définissez CORPUS_OBJECT, chemin dans le bucket.}"
: "${EXTRACTION_MAX_COST:?Définissez EXTRACTION_MAX_COST.}"
: "${EXTRACTION_COST_PER_CALL:?Définissez EXTRACTION_COST_PER_CALL.}"
: "${VOLUMES_MAX_COST:?Définissez VOLUMES_MAX_COST.}"
: "${VOLUMES_COST_PER_CALL:?Définissez VOLUMES_COST_PER_CALL.}"
: "${LLM_SECRET:?Définissez LLM_SECRET.}"
: "${DATAFORSEO_LOGIN_SECRET:?Définissez DATAFORSEO_LOGIN_SECRET.}"
: "${DATAFORSEO_PASSWORD_SECRET:?Définissez DATAFORSEO_PASSWORD_SECRET.}"
: "${NEO4J_URI_SECRET:?Définissez NEO4J_URI_SECRET.}"
: "${NEO4J_USER_SECRET:?Définissez NEO4J_USER_SECRET.}"
: "${NEO4J_PASSWORD_SECRET:?Définissez NEO4J_PASSWORD_SECRET.}"

command -v gcloud >/dev/null 2>&1 || {
  echo "Erreur : gcloud doit être installé." >&2
  exit 1
}

region=europe-west9
secret_version=${SECRET_VERSION:-latest}
for value in "$LLM_SECRET" "$DATAFORSEO_LOGIN_SECRET" "$DATAFORSEO_PASSWORD_SECRET" \
  "$NEO4J_URI_SECRET" "$NEO4J_USER_SECRET" "$NEO4J_PASSWORD_SECRET"; do
  [[ "$value" =~ ^[A-Za-z0-9_-]+$ ]] || { echo "Identifiant de secret invalide." >&2; exit 1; }
done
[[ "$secret_version" =~ ^(latest|[1-9][0-9]*)$ ]] || {
  echo "SECRET_VERSION doit être latest ou un numéro de version." >&2; exit 1;
}
for value in "$EXTRACTION_MAX_COST" "$EXTRACTION_COST_PER_CALL" \
  "$VOLUMES_MAX_COST" "$VOLUMES_COST_PER_CALL"; do
  [[ "$value" =~ ^[0-9]+([.][0-9]{1,9})?$ ]] || {
    echo "Les budgets doivent être des montants décimaux non négatifs." >&2; exit 1;
  }
done
for value in "$EXTRACTION_COST_PER_CALL" "$VOLUMES_COST_PER_CALL"; do
  [[ "$value" =~ [1-9] ]] || { echo "Le coût par appel doit être positif." >&2; exit 1; }
done
[[ "$PROJECT_ID" =~ ^[a-z][a-z0-9-]{4,28}[a-z0-9]$ ]] || {
  echo "PROJECT_ID invalide." >&2; exit 1;
}
for value in "$GCS_BUCKET_RAW" "$CORPUS_BUCKET"; do
  [[ "$value" =~ ^[a-z0-9][a-z0-9._-]*[a-z0-9]$ ]] || {
    echo "Nom de bucket invalide." >&2; exit 1;
  }
done
[[ "$CORPUS_OBJECT" =~ ^[A-Za-z0-9_./-]+$ && "$CORPUS_OBJECT" != /* ]] || {
  echo "CORPUS_OBJECT doit être un chemin relatif sans virgule." >&2; exit 1;
}
case "/$CORPUS_OBJECT/" in */../*|*/./*) echo "Chemin de corpus invalide." >&2; exit 1 ;; esac

common=(
  "--project=$PROJECT_ID" "--region=$region" "--image=$IMAGE"
  "--service-account=$JOB_SERVICE_ACCOUNT" "--tasks=1" "--max-retries=1"
  "--task-timeout=3600s" "--command=/bin/sh"
  "--set-env-vars=GCP_PROJECT_ID=$PROJECT_ID,BQ_LOCATION=$region,GCS_BUCKET_RAW=$GCS_BUCKET_RAW"
  --quiet
)
entry=/app/pipeline/job-entrypoint.sh

gcloud run jobs deploy vil-load-corpus "${common[@]}" \
  "--args=$entry,load-corpus,--archive,/mnt/corpus/$CORPUS_OBJECT" \
  "--add-volume=name=corpus,type=cloud-storage,bucket=$CORPUS_BUCKET,readonly=true" \
  "--add-volume-mount=volume=corpus,mount-path=/mnt/corpus" --clear-secrets
gcloud run jobs deploy vil-extract-entities "${common[@]}" \
  "--args=$entry,extract-entities,--max-cost,$EXTRACTION_MAX_COST,--cost-per-call,$EXTRACTION_COST_PER_CALL" \
  "--set-secrets=/secrets/llm/key=$LLM_SECRET:$secret_version"
gcloud run jobs deploy vil-collect-volumes "${common[@]}" \
  "--args=$entry,collect-volumes,--max-cost,$VOLUMES_MAX_COST,--cost-per-call,$VOLUMES_COST_PER_CALL" \
  "--set-secrets=/secrets/dataforseo/login=$DATAFORSEO_LOGIN_SECRET:$secret_version,/secrets/dataforseo/password=$DATAFORSEO_PASSWORD_SECRET:$secret_version"
gcloud run jobs deploy vil-load-raw-market "${common[@]}" \
  "--args=$entry,load-raw-market" --clear-secrets
gcloud run jobs deploy vil-dbt "${common[@]}" \
  "--args=$entry,dbt" --clear-secrets
gcloud run jobs deploy vil-sync-graph "${common[@]}" \
  "--args=$entry,sync-graph" \
  "--set-secrets=/secrets/neo4j/uri=$NEO4J_URI_SECRET:$secret_version,/secrets/neo4j/user=$NEO4J_USER_SECRET:$secret_version,/secrets/neo4j/password=$NEO4J_PASSWORD_SECRET:$secret_version"

for job in vil-collect-volumes vil-sync-graph; do
  gcloud run jobs add-iam-policy-binding "$job" \
    "--project=$PROJECT_ID" "--region=$region" \
    "--member=serviceAccount:$SCHEDULER_SERVICE_ACCOUNT" \
    --role=roles/run.invoker --quiet
done

existing=$(gcloud scheduler jobs list "--project=$PROJECT_ID" "--location=$region" \
  --format='value(name)')
schedule_job() {
  local name=$1 target=$2 schedule=$3 operation=create line
  while IFS= read -r line; do
    if [[ "$line" == "$name" || "$line" == */"$name" ]]; then
      operation=update
      break
    fi
  done <<< "$existing"
  gcloud scheduler jobs "$operation" http "$name" \
    "--project=$PROJECT_ID" "--location=$region" "--schedule=$schedule" \
    --time-zone=Etc/UTC --http-method=POST \
    "--uri=https://run.googleapis.com/v2/projects/$PROJECT_ID/locations/$region/jobs/$target:run" \
    "--oauth-service-account-email=$SCHEDULER_SERVICE_ACCOUNT" \
    --oauth-token-scope=https://www.googleapis.com/auth/cloud-platform \
    --max-retry-attempts=0 --quiet
}

schedule_job vil-collect-volumes-monthly vil-collect-volumes "0 3 1 * *"
schedule_job vil-sync-graph-weekly vil-sync-graph "0 4 * * 1"
