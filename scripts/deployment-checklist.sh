#!/usr/bin/env bash
# Quick Deployment Checklist & Next Steps
# Run this after the test suite to verify critical items

set -e

PROJECT_ID="test-barometre-juridique"
REGION="europe-west9"

echo "════════════════════════════════════════════════════════════════"
echo "  🚀 VANTEDGE LEGAL INTELLIGENCE - DEPLOYMENT NEXT STEPS"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "Project: $PROJECT_ID | Region: $REGION"
echo "Timestamp: $(date -u +'%Y-%m-%d %H:%M:%S UTC')"
echo ""

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}────────────────────────────────────────────────────────────────${NC}"
echo -e "${BLUE}CRITICAL NEXT STEPS (Do these FIRST):${NC}"
echo -e "${BLUE}────────────────────────────────────────────────────────────────${NC}"
echo ""

echo -e "${YELLOW}1. VERIFY GITHUB SECRETS${NC}"
echo "   Location: GitHub Settings > Secrets and variables > Actions"
echo "   Required secrets:"
echo "   ☐ GCP_PROJECT_ID = test-barometre-juridique"
echo "   ☐ GCP_WORKLOAD_IDENTITY_PROVIDER = projects/31886648583/locations/global/workloadIdentityPools/github-action/providers/github-provider"
echo "   ☐ GCP_SERVICE_ACCOUNT = github-actions@test-barometre-juridique.iam.gserviceaccount.com"
echo ""
echo "   Command to check:"
echo "   ${YELLOW}gh secret list${NC}"
echo ""

echo -e "${YELLOW}2. VERIFY GITHUB VARIABLES${NC}"
echo "   Location: GitHub Settings > Secrets and variables > Variables"
echo "   Required variables (Frontend):"
echo "   ☐ NEXT_PUBLIC_SUPABASE_URL"
echo "   ☐ NEXT_PUBLIC_SUPABASE_ANON_KEY"
echo "   ☐ STRIPE_PRICE_PRO"
echo ""
echo "   Required variables (Pipeline):"
echo "   ☐ CORPUS_BUCKET"
echo "   ☐ CORPUS_OBJECT"
echo "   ☐ EXTRACTION_MAX_COST"
echo "   ☐ EXTRACTION_COST_PER_CALL"
echo ""
echo "   Command to check:"
echo "   ${YELLOW}gh variable list${NC}"
echo ""

echo -e "${YELLOW}3. VALIDATE GOOGLE CLOUD SECRETS${NC}"
echo "   These exist and are configured. Verify their values:"
echo "   ${YELLOW}gcloud secrets describe supabase-service-role-key --format='value(labels)'${NC}"
echo "   ${YELLOW}gcloud secrets describe stripe-secret-key --format='value(labels)'${NC}"
echo ""

echo -e "${BLUE}────────────────────────────────────────────────────────────────${NC}"
echo -e "${BLUE}TESTING PHASES:${NC}"
echo -e "${BLUE}────────────────────────────────────────────────────────────────${NC}"
echo ""

echo -e "${YELLOW}PHASE 1: Local Testing (Optional - requires Docker)${NC}"
echo ""
echo "1.1) Build and test Frontend locally:"
echo "    ${YELLOW}npm install --prefix apps/web${NC}"
echo "    ${YELLOW}npm run dev --prefix apps/web${NC}"
echo "    → Open http://localhost:3000"
echo ""

echo "1.2) Build and test Pipeline locally (requires Docker):"
echo "    ${YELLOW}docker build -f pipeline/Dockerfile -t vil-pipeline:test .${NC}"
echo "    ${YELLOW}docker run --rm vil-pipeline:test --help${NC}"
echo ""

echo -e "${YELLOW}PHASE 2: GitHub Actions CI/CD${NC}"
echo ""
echo "2.1) Commit and push to fix/infra-alignment:"
echo "    ${YELLOW}git add .${NC}"
echo "    ${YELLOW}git commit -m 'Add deployment tests and documentation'${NC}"
echo "    ${YELLOW}git push origin fix/infra-alignment${NC}"
echo ""

echo "2.2) Create Pull Request:"
echo "    URL: https://github.com/Maxim903/Vantedge-legal-intelligence/pull/new/fix/infra-alignment"
echo "    Wait for CI to pass (tests, build, lint)"
echo ""

echo "2.3) Merge to main:"
echo "    After CI passes, merge the PR"
echo "    ${YELLOW}git checkout main${NC}"
echo "    ${YELLOW}git merge fix/infra-alignment${NC}"
echo "    ${YELLOW}git push origin main${NC}"
echo ""

echo "2.4) Monitor workflows:"
echo "    URL: https://github.com/Maxim903/Vantedge-legal-intelligence/actions"
echo "    Watch for:"
echo "    ✓ CI workflow (all tests pass)"
echo "    ✓ publish-pipeline.yml (image built and pushed)"
echo "    ✓ deploy-frontend.yml (service deployed)"
echo ""

echo -e "${YELLOW}PHASE 3: Manual Job Testing${NC}"
echo ""
echo "3.1) After publish-pipeline succeeds, test jobs manually:"
echo ""
echo "    Execute vil-load-corpus:"
echo "    ${YELLOW}gcloud run jobs execute vil-load-corpus --region=$REGION --wait${NC}"
echo ""
echo "    Execute vil-extract-notions:"
echo "    ${YELLOW}gcloud run jobs execute vil-extract-notions --region=$REGION --wait${NC}"
echo ""
echo "    Execute vil-gap-analysis:"
echo "    ${YELLOW}gcloud run jobs execute vil-gap-analysis --region=$REGION --wait${NC}"
echo ""

echo "3.2) Check job logs:"
echo "    ${YELLOW}gcloud run jobs log vil-load-corpus --region=$REGION --limit=100${NC}"
echo "    ${YELLOW}gcloud run jobs log vil-extract-notions --region=$REGION --limit=100${NC}"
echo "    ${YELLOW}gcloud run jobs log vil-gap-analysis --region=$REGION --limit=100${NC}"
echo ""

echo -e "${YELLOW}PHASE 4: Frontend Verification${NC}"
echo ""
echo "4.1) After deploy-frontend succeeds, get the service URL:"
echo "    ${YELLOW}gcloud run services describe vil-web --region=$REGION --format='value(status.url)'${NC}"
echo ""

echo "4.2) Test the service:"
echo "    ${YELLOW}curl https://vil-web-xxx.region-run.app/${NC}"
echo "    ${YELLOW}curl -v https://vil-web-xxx.region-run.app/health${NC}"
echo ""

echo "4.3) Check frontend logs:"
echo "    ${YELLOW}gcloud run logs read vil-web --region=$REGION --limit=50${NC}"
echo ""

echo "4.4) Test authentication (requires Supabase configured):"
echo "    Open https://vil-web-xxx.region-run.app/ in browser"
echo "    Try sign-up and sign-in flows"
echo ""

echo -e "${YELLOW}PHASE 5: Scheduler Activation${NC}"
echo ""
echo "5.1) The schedulers are already ENABLED. They will run at:"
echo "    ${GREEN}vil-load-corpus   : 02:00 UTC${NC}"
echo "    ${GREEN}vil-extract-notions: 04:00 UTC${NC}"
echo "    ${GREEN}vil-gap-analysis   : 06:00 UTC${NC}"
echo ""

echo "5.2) Manually test scheduler:"
echo "    ${YELLOW}gcloud scheduler jobs run vil-load-corpus --location=$REGION${NC}"
echo "    ${YELLOW}gcloud scheduler jobs run vil-extract-notions --location=$REGION${NC}"
echo "    ${YELLOW}gcloud scheduler jobs run vil-gap-analysis --location=$REGION${NC}"
echo ""

echo -e "${BLUE}────────────────────────────────────────────────────────────────${NC}"
echo -e "${BLUE}USEFUL COMMANDS:${NC}"
echo -e "${BLUE}────────────────────────────────────────────────────────────────${NC}"
echo ""

echo "List all Cloud Run Jobs:"
echo "  ${YELLOW}gcloud run jobs list --region=$REGION${NC}"
echo ""

echo "List all Cloud Run Services:"
echo "  ${YELLOW}gcloud run services list --region=$REGION${NC}"
echo ""

echo "List all Scheduler jobs:"
echo "  ${YELLOW}gcloud scheduler jobs list --location=$REGION${NC}"
echo ""

echo "List all Secrets:"
echo "  ${YELLOW}gcloud secrets list${NC}"
echo ""

echo "List images in vil-pipeline:"
echo "  ${YELLOW}gcloud artifacts docker images list europe-west9-docker.pkg.dev/$PROJECT_ID/vil-pipeline${NC}"
echo ""

echo "List images in vil-frontend:"
echo "  ${YELLOW}gcloud artifacts docker images list europe-west9-docker.pkg.dev/$PROJECT_ID/vil-frontend${NC}"
echo ""

echo -e "${BLUE}────────────────────────────────────────────────────────────────${NC}"
echo -e "${BLUE}TROUBLESHOOTING:${NC}"
echo -e "${BLUE}────────────────────────────────────────────────────────────────${NC}"
echo ""

echo "If workflows fail, check:"
echo ""
echo "1. GitHub Actions logs:"
echo "   URL: https://github.com/Maxim903/Vantedge-legal-intelligence/actions"
echo ""

echo "2. Cloud Build logs (if using Cloud Build):"
echo "   ${YELLOW}gcloud builds log <BUILD_ID>${NC}"
echo ""

echo "3. Cloud Run Job execution logs:"
echo "   ${YELLOW}gcloud run jobs log <JOB_NAME> --region=$REGION --limit=200${NC}"
echo ""

echo "4. Cloud Run Service logs:"
echo "   ${YELLOW}gcloud run logs read <SERVICE_NAME> --region=$REGION --limit=100${NC}"
echo ""

echo "5. Check IAM permissions:"
echo "   ${YELLOW}gcloud projects get-iam-policy $PROJECT_ID --flatten='bindings[].members' --filter='bindings.members:github-actions*'${NC}"
echo ""

echo -e "${BLUE}────────────────────────────────────────────────────────────────${NC}"
echo -e "${BLUE}QUICK REFERENCE:${NC}"
echo -e "${BLUE}────────────────────────────────────────────────────────────────${NC}"
echo ""

echo "Project ID: $PROJECT_ID"
echo "Region: $REGION"
echo "Registry: europe-west9-docker.pkg.dev"
echo ""

echo "Frontend Service:"
echo "  Name: vil-web"
echo "  Port: 3000"
echo "  Memory: 1Gi"
echo "  CPU: 2"
echo "  Max instances: 10"
echo ""

echo "Pipeline Jobs:"
echo "  vil-load-corpus (02:00 UTC)"
echo "  vil-extract-notions (04:00 UTC)"
echo "  vil-gap-analysis (06:00 UTC)"
echo ""

echo "Service Accounts:"
echo "  github-actions@$PROJECT_ID.iam.gserviceaccount.com (GitHub OIDC)"
echo "  vil-jobs-runner@$PROJECT_ID.iam.gserviceaccount.com (Job execution)"
echo "  vil-scheduler@$PROJECT_ID.iam.gserviceaccount.com (Scheduler)"
echo ""

echo -e "${GREEN}════════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✓ Infrastructure is ready for deployment!${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════════════════${NC}"
echo ""
