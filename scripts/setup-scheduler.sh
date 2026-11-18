#!/bin/bash
# Configuration de Cloud Scheduler pour orchestrer les jobs

set -e

PROJECT_ID="${GCP_PROJECT_ID:-test-barometre-juridique}"
REGION="europe-west9"
SCHEDULER_LOCATION="europe-west9"
SCHEDULER_SA="vil-scheduler@${PROJECT_ID}.iam.gserviceaccount.com"
JOBS_SA="vil-jobs-runner@${PROJECT_ID}.iam.gserviceaccount.com"

echo "╔════════════════════════════════════════════════════════════╗"
echo "║      Configuration de Cloud Scheduler                      ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "Configuration:"
echo "  Projet: $PROJECT_ID"
echo "  Région: $SCHEDULER_LOCATION"
echo "  Scheduler SA: $SCHEDULER_SA"
echo "  Jobs SA: $JOBS_SA"
echo ""

# Vérifier que l'API Cloud Scheduler est activée
echo "Activation de l'API Cloud Scheduler..."
gcloud services enable cloudscheduler.googleapis.com --project="$PROJECT_ID" 2>&1 | grep -E "Enabling|Enabled|ERROR|already" | head -1

echo ""

# Définir les jobs et leurs schedules
declare -A JOB_SCHEDULES=(
  [vil-load-corpus]="0 2 * * *"      # Tous les jours à 2h du matin
  [vil-extract-notions]="0 4 * * *"  # Tous les jours à 4h du matin
  [vil-gap-analysis]="0 6 * * *"     # Tous les jours à 6h du matin
)

# Créer ou mettre à jour les horaires de scheduler
for JOB_NAME in "${!JOB_SCHEDULES[@]}"; do
  SCHEDULE="${JOB_SCHEDULES[$JOB_NAME]}"
  
  echo "Configuration du scheduler pour: $JOB_NAME"
  echo "  Schedule: $SCHEDULE (cron)"
  
  # Construire l'URI du job Cloud Run
  JOB_URI="https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/projects/${PROJECT_ID}/locations/${REGION}/jobs/${JOB_NAME}:run"
  
  # Vérifier si le scheduler existe
  if gcloud scheduler jobs describe "$JOB_NAME" \
    --location="$SCHEDULER_LOCATION" \
    --project="$PROJECT_ID" \
    >/dev/null 2>&1; then
    
    echo "  ➜ Mise à jour du scheduler..."
    gcloud scheduler jobs update http "$JOB_NAME" \
      --location="$SCHEDULER_LOCATION" \
      --project="$PROJECT_ID" \
      --schedule="$SCHEDULE" \
      --http-method=POST \
      --uri="$JOB_URI" \
      --oidc-service-account-email="$SCHEDULER_SA" \
      --oidc-token-audience="$JOB_URI" \
      --quiet 2>&1 | grep -E "Updated|ERROR|already" || echo "  ✅ Scheduler mis à jour"
  else
    echo "  ➜ Création du scheduler..."
    gcloud scheduler jobs create http "$JOB_NAME" \
      --location="$SCHEDULER_LOCATION" \
      --project="$PROJECT_ID" \
      --schedule="$SCHEDULE" \
      --http-method=POST \
      --uri="$JOB_URI" \
      --oidc-service-account-email="$SCHEDULER_SA" \
      --oidc-token-audience="$JOB_URI" \
      --quiet 2>&1 | grep -E "Created|ERROR" || echo "  ✅ Scheduler créé"
  fi
  
  echo ""
done

echo "╔════════════════════════════════════════════════════════════╗"
echo "║          ✅ Schedulers configurés!                         ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "Horaires de exécution:"
echo "  - vil-load-corpus: 02:00 UTC (tous les jours)"
echo "  - vil-extract-notions: 04:00 UTC (tous les jours)"
echo "  - vil-gap-analysis: 06:00 UTC (tous les jours)"
echo ""
echo "Pour voir les schedulers:"
gcloud scheduler jobs list \
  --location="$SCHEDULER_LOCATION" \
  --project="$PROJECT_ID" \
  --format="table(name, schedule, state)"

echo ""
echo "Pour exécuter un scheduler manuellement:"
echo "  gcloud scheduler jobs run <job-name> --location=$SCHEDULER_LOCATION --project=$PROJECT_ID"
