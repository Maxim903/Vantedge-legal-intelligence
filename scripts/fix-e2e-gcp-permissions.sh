#!/usr/bin/env bash
# Script to fix E2E test BigQuery permissions on GCP
# 
# Usage: ./scripts/fix-e2e-gcp-permissions.sh
# 
# This script adds BigQuery IAM roles to the GitHub Actions Service Account
# to enable E2E tests to create and manage BigQuery datasets.

set -euo pipefail

# Configuration
GCP_PROJECT_ID="test-barometre-juridique"
SERVICE_ACCOUNT="vantedge-legal-intelligence-gha-runner"
SERVICE_ACCOUNT_EMAIL="${SERVICE_ACCOUNT}@${GCP_PROJECT_ID}.iam.gserviceaccount.com"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   E2E Test GCP BigQuery Permissions Fixer                 ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check prerequisites
echo -e "${YELLOW}📋 Checking prerequisites...${NC}"
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}❌ gcloud CLI not found. Install it:${NC}"
    echo "   https://cloud.google.com/sdk/docs/install"
    exit 1
fi

if ! command -v jq &> /dev/null; then
    echo -e "${RED}❌ jq not found. Install it:${NC}"
    echo "   - macOS: brew install jq"
    echo "   - Linux: sudo apt-get install jq"
    echo "   - Windows: https://github.com/jqlang/jq/releases"
    exit 1
fi

echo -e "${GREEN}✓ Prerequisites OK${NC}"
echo ""

# Check GCP authentication
echo -e "${YELLOW}🔐 Checking GCP authentication...${NC}"
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" &> /dev/null; then
    echo -e "${RED}❌ Not authenticated with gcloud${NC}"
    echo "   Run: gcloud auth login"
    exit 1
fi

CURRENT_ACCOUNT=$(gcloud auth list --filter=status:ACTIVE --format="value(account)")
echo -e "${GREEN}✓ Authenticated as: $CURRENT_ACCOUNT${NC}"
echo ""

# Confirm project
echo -e "${YELLOW}🔍 Verifying GCP project...${NC}"
CURRENT_PROJECT=$(gcloud config get-value project 2>/dev/null || echo "")
if [ "$CURRENT_PROJECT" != "$GCP_PROJECT_ID" ]; then
    echo -e "${YELLOW}⚠️  Current project is: $CURRENT_PROJECT${NC}"
    echo -e "${YELLOW}📌 Target project is: $GCP_PROJECT_ID${NC}"
    echo ""
    read -p "Switch to $GCP_PROJECT_ID? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        gcloud config set project "$GCP_PROJECT_ID"
        echo -e "${GREEN}✓ Project switched${NC}"
    else
        echo -e "${RED}❌ Project mismatch. Exiting.${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✓ Project is: $GCP_PROJECT_ID${NC}"
fi
echo ""

# Verify service account exists
echo -e "${YELLOW}🤖 Verifying service account exists...${NC}"
if ! gcloud iam service-accounts describe "$SERVICE_ACCOUNT_EMAIL" \
    --project="$GCP_PROJECT_ID" > /dev/null 2>&1; then
    echo -e "${RED}❌ Service account not found: $SERVICE_ACCOUNT_EMAIL${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Service account found: $SERVICE_ACCOUNT_EMAIL${NC}"
echo ""

# Check current permissions
echo -e "${YELLOW}📊 Checking current BigQuery roles...${NC}"
CURRENT_ROLES=$(gcloud iam service-accounts get-iam-policy "$SERVICE_ACCOUNT_EMAIL" \
    --project="$GCP_PROJECT_ID" \
    --format=json | jq -r '.bindings[]? | select(.role | contains("bigquery")) | .role' || echo "")

if [ -z "$CURRENT_ROLES" ]; then
    echo -e "${RED}⚠️  No BigQuery roles found${NC}"
else
    echo -e "${GREEN}Current roles:${NC}"
    echo "$CURRENT_ROLES" | while read -r role; do
        echo -e "  ${GREEN}✓${NC} $role"
    done
fi
echo ""

# Apply BigQuery roles
echo -e "${YELLOW}🔑 Applying BigQuery IAM roles...${NC}"
echo ""

ROLES=(
    "roles/bigquery.user"
    "roles/bigquery.dataEditor"
)

for role in "${ROLES[@]}"; do
    echo -n "  Adding $role... "
    
    # Check if role is already assigned
    if gcloud iam service-accounts get-iam-policy "$SERVICE_ACCOUNT_EMAIL" \
        --project="$GCP_PROJECT_ID" \
        --format=json | jq -e ".bindings[]? | select(.role == \"$role\")" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Already assigned${NC}"
    else
        if gcloud iam service-accounts add-iam-policy-binding "$SERVICE_ACCOUNT_EMAIL" \
            --project="$GCP_PROJECT_ID" \
            --role="$role" \
            --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
            --condition=None \
            --quiet > /dev/null 2>&1; then
            echo -e "${GREEN}✓ Added${NC}"
        else
            echo -e "${RED}✗ Failed to add${NC}"
            exit 1
        fi
    fi
done
echo ""

# Verify new permissions
echo -e "${YELLOW}✅ Verifying final permissions...${NC}"
FINAL_ROLES=$(gcloud iam service-accounts get-iam-policy "$SERVICE_ACCOUNT_EMAIL" \
    --project="$GCP_PROJECT_ID" \
    --format=json | jq -r '.bindings[]? | select(.role | contains("bigquery")) | .role' || echo "")

echo -e "${GREEN}Final BigQuery roles:${NC}"
echo "$FINAL_ROLES" | while read -r role; do
    echo -e "  ${GREEN}✓${NC} $role"
done
echo ""

# Success message
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                     ✅ PERMISSIONS FIXED!                  ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}📝 Next steps:${NC}"
echo "   1. Re-run PR #23 workflow on GitHub"
echo "   2. Watch E2E tests pass ✅"
echo ""
echo -e "${BLUE}🔗 Resources:${NC}"
echo "   • GCP IAM: https://console.cloud.google.com/iam-admin/iam"
echo "   • PR #23: https://github.com/Maxim903/Vantedge-legal-intelligence/pull/23"
echo "   • Workflow: https://github.com/Maxim903/Vantedge-legal-intelligence/actions"
echo ""
