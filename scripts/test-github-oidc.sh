#!/bin/bash
# Test script pour vérifier la configuration GitHub OIDC

set -e

PROJECT_ID="test-barometre-juridique"
REPO="Maxim903/Vantedge-legal-intelligence"

echo "🧪 Test Configuration GitHub OIDC"
echo "=================================="
echo ""

# 1. Vérifier le Workload Identity Pool
echo "1️⃣ Vérification du Workload Identity Pool..."
POOL=$(gcloud iam workload-identity-pools describe \
  "github-action" \
  --project="${PROJECT_ID}" \
  --location="global" \
  --format="value(name)" 2>&1)

if [ $? -eq 0 ]; then
  echo "   ✅ Pool trouvé: $POOL"
else
  echo "   ❌ Erreur: Pool non trouvé"
  exit 1
fi

# 2. Vérifier le Provider OIDC
echo ""
echo "2️⃣ Vérification du Provider OIDC..."
PROVIDER=$(gcloud iam workload-identity-pools providers describe \
  "github-provider" \
  --project="${PROJECT_ID}" \
  --location="global" \
  --workload-identity-pool="github-action" \
  --format="value(name)" 2>&1)

if [ $? -eq 0 ]; then
  echo "   ✅ Provider trouvé: $PROVIDER"
else
  echo "   ❌ Erreur: Provider non trouvé"
  exit 1
fi

# 3. Vérifier le Service Account
echo ""
echo "3️⃣ Vérification du Service Account..."
SA="github-actions@${PROJECT_ID}.iam.gserviceaccount.com"
SA_CHECK=$(gcloud iam service-accounts describe "$SA" \
  --project="${PROJECT_ID}" \
  --format="value(email)" 2>&1)

if [ $? -eq 0 ]; then
  echo "   ✅ Service Account trouvé: $SA_CHECK"
else
  echo "   ❌ Erreur: Service Account non trouvé"
  exit 1
fi

# 4. Vérifier les IAM bindings
echo ""
echo "4️⃣ Vérification des IAM Bindings..."
WORKLOAD_IDENTITY_BINDING=$(gcloud iam service-accounts get-iam-policy \
  "$SA" \
  --project="${PROJECT_ID}" \
  --format="value(bindings[].members)" 2>&1 | grep "principalSet" | wc -l)

if [ "$WORKLOAD_IDENTITY_BINDING" -gt 0 ]; then
  echo "   ✅ Workload Identity Binding configuré"
else
  echo "   ⚠️ Avertissement: Pas de Workload Identity Binding trouvé"
fi

# 5. Vérifier les rôles IAM
echo ""
echo "5️⃣ Vérification des rôles IAM..."
ROLES=$(gcloud projects get-iam-policy "${PROJECT_ID}" \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:$SA" \
  --format="value(bindings.role)" 2>&1)

ROLE_COUNT=$(echo "$ROLES" | wc -l)
if [ "$ROLE_COUNT" -ge 3 ]; then
  echo "   ✅ Au moins 3 rôles configurés:"
  echo "$ROLES" | sed 's/^/      /'
else
  echo "   ❌ Erreur: Pas assez de rôles configurés (trouvé: $ROLE_COUNT, attendu: 3+)"
  exit 1
fi

# 6. Résumé
echo ""
echo "=================================="
echo "✅ Configuration GitHub OIDC validée!"
echo ""
echo "📝 Résumé:"
echo "   - Workload Identity Pool: github-action"
echo "   - OIDC Provider: github-provider"
echo "   - Service Account: $SA"
echo "   - Rôles: $ROLE_COUNT configurés"
echo ""
echo "🎯 Prochaines étapes:"
echo "   1. Ajouter les secrets dans GitHub:"
echo "      https://github.com/$REPO/settings/secrets/actions"
echo "   2. Les secrets à ajouter:"
echo "      - GCP_PROJECT_ID: $PROJECT_ID"
echo "      - GCP_WORKLOAD_IDENTITY_PROVIDER: $PROVIDER"
echo "      - GCP_SERVICE_ACCOUNT: $SA"
echo ""
