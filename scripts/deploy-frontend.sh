#!/bin/bash
# Script: Deploy Frontend to Cloud Run
# This script builds and deploys the Next.js frontend to Google Cloud Run

set -euo pipefail

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:-test-barometre-juridique}"
REGION="${GCP_REGION:-europe-west9}"
REGISTRY="${REGION}-docker.pkg.dev"
SERVICE_NAME="vil-web"
IMAGE_NAME="vil-frontend"
IMAGE_TAG="${1:-latest}"

: "${NEXT_PUBLIC_SUPABASE_URL:?NEXT_PUBLIC_SUPABASE_URL must be set for the production build}"
: "${NEXT_PUBLIC_SUPABASE_ANON_KEY:?NEXT_PUBLIC_SUPABASE_ANON_KEY must be set for the production build}"
: "${STRIPE_PRICE_PRO:?STRIPE_PRICE_PRO must be set for the production service}"

echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║          🚀 Déploiement du Frontend sur Cloud Run                 ║"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo ""

echo "📦 Configuration:"
echo "   Project ID: $PROJECT_ID"
echo "   Région: $REGION"
echo "   Service: $SERVICE_NAME"
echo "   Image Tag: $IMAGE_TAG"
echo ""

# Ensure the frontend image repository exists.
if ! gcloud artifacts repositories describe "$IMAGE_NAME" \
  --location="$REGION" \
  --project="$PROJECT_ID" >/dev/null 2>&1; then
  gcloud artifacts repositories create "$IMAGE_NAME" \
    --repository-format=docker \
    --location="$REGION" \
    --project="$PROJECT_ID"
fi

# Build the Docker image
echo "📦 Build de l'image Docker..."
docker build \
  -f apps/web/Dockerfile \
  --build-arg "NEXT_PUBLIC_SUPABASE_URL=$NEXT_PUBLIC_SUPABASE_URL" \
  --build-arg "NEXT_PUBLIC_SUPABASE_ANON_KEY=$NEXT_PUBLIC_SUPABASE_ANON_KEY" \
  -t "$REGISTRY/$PROJECT_ID/$IMAGE_NAME/$SERVICE_NAME:$IMAGE_TAG" \
  -t "$REGISTRY/$PROJECT_ID/$IMAGE_NAME/$SERVICE_NAME:latest" \
  .

echo "✅ Build réussi!"
echo ""

# Push to Artifact Registry
echo "📤 Push vers Artifact Registry..."
docker push "$REGISTRY/$PROJECT_ID/$IMAGE_NAME/$SERVICE_NAME:$IMAGE_TAG"
docker push "$REGISTRY/$PROJECT_ID/$IMAGE_NAME/$SERVICE_NAME:latest"

echo "✅ Images pushées!"
echo ""

# Deploy to Cloud Run
echo "🚀 Déploiement sur Cloud Run..."
gcloud run deploy "$SERVICE_NAME" \
  --image="$REGISTRY/$PROJECT_ID/$IMAGE_NAME/$SERVICE_NAME:$IMAGE_TAG" \
  --region="$REGION" \
  --project="$PROJECT_ID" \
  --platform=managed \
  --service-account="31886648583-compute@developer.gserviceaccount.com" \
  --allow-unauthenticated \
  --port=3000 \
  --memory=1Gi \
  --cpu=2 \
  --timeout=3600 \
  --max-instances=10 \
  --min-instances=1 \
  --set-env-vars="NODE_ENV=production,GCP_PROJECT_ID=$PROJECT_ID,BQ_LOCATION=$REGION,BQ_DATASET=marts,STRIPE_PRICE_PRO=$STRIPE_PRICE_PRO" \
  --set-secrets="SUPABASE_SERVICE_ROLE_KEY=supabase-service-role-key:latest,STRIPE_SECRET_KEY=stripe-secret-key:latest,STRIPE_WEBHOOK_SECRET=stripe-webhook-secret:latest" \
  --no-gen2 \
  --quiet

echo "✅ Déploiement réussi!"
echo ""

# Get the service URL
SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" \
  --region="$REGION" \
  --project="$PROJECT_ID" \
  --format="value(status.url)" 2>/dev/null)

gcloud run services update "$SERVICE_NAME" \
  --region="$REGION" \
  --project="$PROJECT_ID" \
  --update-env-vars="APP_URL=$SERVICE_URL" \
  --quiet

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🎉 Déploiement complété!"
echo ""
echo "Service URL: $SERVICE_URL"
echo "Region: $REGION"
echo "Image: $REGISTRY/$PROJECT_ID/$IMAGE_NAME/$SERVICE_NAME:$IMAGE_TAG"
echo ""
echo "Pour voir les logs:"
echo "  gcloud run logs read $SERVICE_NAME --region=$REGION --limit=50"
echo ""
echo "Pour mettre à jour le service:"
echo "  gcloud run deploy $SERVICE_NAME --image=... --region=$REGION"
