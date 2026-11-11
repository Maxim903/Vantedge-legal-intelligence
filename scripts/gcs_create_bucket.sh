#!/usr/bin/env bash

set -euo pipefail

: "${PROJECT_ID:?Définissez PROJECT_ID avec le project ID GCP.}"
: "${BUCKET_NAME:?Définissez BUCKET_NAME avec le nom du bucket GCS, sans gs://.}"

command -v gcloud >/dev/null 2>&1 || {
  printf 'Erreur : gcloud doit être installé.\n' >&2
  exit 1
}

command -v python3 >/dev/null 2>&1 || {
  printf 'Erreur : python3 doit être installé.\n' >&2
  exit 1
}

bucket_uri="gs://${BUCKET_NAME}"
tmpdir=$(mktemp -d)
trap 'rm -rf "$tmpdir"' EXIT

bucket_info="$tmpdir/bucket.json"
describe_error="$tmpdir/describe.err"

if ! gcloud storage buckets describe "$bucket_uri" \
  --project="$PROJECT_ID" \
  --format=json >"$bucket_info" 2>"$describe_error"; then
  if ! gcloud storage buckets create "$bucket_uri" \
    --project="$PROJECT_ID" \
    --location=europe-west9 \
    --uniform-bucket-level-access \
    --public-access-prevention \
    --quiet; then
    cat "$describe_error" >&2
    exit 1
  fi

  gcloud storage buckets describe "$bucket_uri" \
    --project="$PROJECT_ID" \
    --format=json >"$bucket_info"
fi

location=$(python3 -c 'import json, sys; print(json.load(open(sys.argv[1])).get("location", ""))' "$bucket_info")
if [[ "${location,,}" != "europe-west9" ]]; then
  printf 'Erreur : le bucket %s est en %s ; sa région doit être europe-west9 et ne peut pas être modifiée.\n' \
    "$bucket_uri" "${location:-inconnue}" >&2
  exit 1
fi

gcloud storage buckets update "$bucket_uri" \
  --project="$PROJECT_ID" \
  --uniform-bucket-level-access \
  --public-access-prevention \
  --versioning

lifecycle_file="$tmpdir/lifecycle.json"
python3 - "$bucket_info" "$lifecycle_file" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as bucket_file:
    bucket = json.load(bucket_file)

lifecycle = bucket.get("lifecycle") or {}
rules = lifecycle.get("rule") or []
nearline_after_90_days = {
    "action": {"type": "SetStorageClass", "storageClass": "NEARLINE"},
    "condition": {"age": 90},
}

if not any(
    rule.get("action", {}).get("type") == "SetStorageClass"
    and rule.get("action", {}).get("storageClass") == "NEARLINE"
    and rule.get("condition") == {"age": 90}
    for rule in rules
):
    rules.append(nearline_after_90_days)

with open(sys.argv[2], "w", encoding="utf-8") as lifecycle_file:
    json.dump({"rule": rules}, lifecycle_file)
PY

gcloud storage buckets update "$bucket_uri" \
  --project="$PROJECT_ID" \
  --lifecycle-file="$lifecycle_file"
