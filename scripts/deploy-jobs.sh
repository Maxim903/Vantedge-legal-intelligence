#!/bin/bash
# Script de déploiement des Cloud Run Jobs

set -e

PROJECT_ID="${GCP_PROJECT_ID:-test-barometre-juridique}"
REGION="${GCP_REGION:-europe-west9}"
SERVICE_ACCOUNT="vil-jobs-runner@${PROJECT_ID}.iam.gserviceaccount.com"
IMAGE_NAME="vil-pipeline"
REGISTRY="europe-west9-docker.pkg.dev"

# Déterminer la version de l'image
if [ -z "$IMAGE_TAG" ]; then
  IMAGE_TAG="latest"
fi

IMAGE="${REGISTRY}/${PROJECT_ID}/${IMAGE_NAME}/${IMAGE_NAME}:${IMAGE_TAG}"

echo "╔════════════════════════════════════════════════════════════╗"
echo "║           Déploiement des Cloud Run Jobs                  ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "Configuration:"
echo "  Projet: $PROJECT_ID"
echo "  Région: $REGION"
echo "  Image: $IMAGE"
echo "  Service Account: $SERVICE_ACCOUNT"
echo ""

# Vérifier que l'image existe
echo "Vérification de l'image Docker..."
if ! gcloud artifacts docker images describe "$IMAGE" --project="$PROJECT_ID" >/dev/null 2>&1; then
  echo "❌ Erreur: Image non trouvée: $IMAGE"
  echo "Veuillez d'abord builder et pousser l'image vers Artifact Registry"
  exit 1
fi
echo "✅ Image trouvée"
echo ""

# Définir les jobs
declare -A JOBS=(
  [vil-load-corpus]="Charge le corpus juridique"
  [vil-extract-notions]="Extrait les notions juridiques"
  [vil-gap-analysis]="Analyse l'écart de couverture"
)

# Créer ou mettre à jour chaque job
for JOB_NAME in "${!JOBS[@]}"; do
  JOB_DESC="${JOBS[$JOB_NAME]}"
  
  echo "Traitement du job: $JOB_NAME"
  echo "  Description: $JOB_DESC"
  
  # Vérifier si le job existe
  if gcloud run jobs describe "$JOB_NAME" \
    --region="$REGION" \
    --project="$PROJECT_ID" \
    >/dev/null 2>&1; then
    
    echo "  ➜ Mise à jour du job existant..."
    gcloud run jobs update "$JOB_NAME" \
      --image="$IMAGE" \
      --region="$REGION" \
      --project="$PROJECT_ID" \
      --service-account="$SERVICE_ACCOUNT" \
      --quiet 2>&1 | grep -E "Updated|ERROR" || echo "  ✅ Job mis à jour"
  else
    echo "  ➜ Création du job..."
    gcloud run jobs create "$JOB_NAME" \
      --image="$IMAGE" \
      --region="$REGION" \
      --project="$PROJECT_ID" \
      --service-account="$SERVICE_ACCOUNT" \
      --quiet 2>&1 | grep -E "Created|ERROR" || echo "  ✅ Job créé"
  fi
  
  echo ""
done

echo "╔════════════════════════════════════════════════════════════╗"
echo "║            ✅ Déploiement complété!                        ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "Jobs disponibles:"
gcloud run jobs list \
  --region="$REGION" \
  --project="$PROJECT_ID" \
  --format="table(name, state)"

echo ""
echo "Pour exécuter un job manuellement:"
echo "  gcloud run jobs execute <job-name> --region=$REGION --project=$PROJECT_ID"
echo ""
echo "Pour voir les logs:"
echo "  gcloud run jobs log <job-name> --region=$REGION --project=$PROJECT_ID --limit=50"
