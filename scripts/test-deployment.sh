#!/bin/bash
# Vantedge Legal Intelligence - Deployment Test Suite
# Tests comprehensive deployment infrastructure on GCP

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:-test-barometre-juridique}"
REGION="europe-west9"
SERVICE_NAME="vil-web"
REGISTRY="europe-west9-docker.pkg.dev"

# Test results
PASSED=0
FAILED=0
SKIPPED=0

# Helper functions
print_header() {
    echo -e "\n${BLUE}=================================================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}=================================================================================${NC}\n"
}

print_test() {
    echo -e "${YELLOW}→${NC} $1"
}

print_pass() {
    echo -e "${GREEN}✓${NC} $1"
    ((PASSED++))
}

print_fail() {
    echo -e "${RED}✗${NC} $1"
    ((FAILED++))
}

print_skip() {
    echo -e "${YELLOW}⊘${NC} $1"
    ((SKIPPED++))
}

# Test 1: GCP Authentication
test_gcp_auth() {
    print_header "TEST 1: GCP Authentication & Configuration"
    
    print_test "Checking GCP authentication..."
    if gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q "@"; then
        print_pass "GCP authentication active"
    else
        print_fail "GCP authentication not configured"
        return 1
    fi
    
    print_test "Checking project configuration..."
    if [[ $(gcloud config get-value project) == "$PROJECT_ID" ]]; then
        print_pass "Project set to $PROJECT_ID"
    else
        print_fail "Project not set correctly"
        return 1
    fi
}

# Test 2: Artifact Registry
test_artifact_registry() {
    print_header "TEST 2: Artifact Registry Configuration"
    
    for repo in vil-frontend vil-pipeline; do
        print_test "Checking $repo repository..."
        if gcloud artifacts repositories describe "$repo" \
            --location="$REGION" \
            --project="$PROJECT_ID" >/dev/null 2>&1; then
            print_pass "$repo repository exists"
            
            # List images in repo
            image_count=$(gcloud artifacts docker images list \
                "${REGISTRY}/${PROJECT_ID}/${repo}" \
                --format="value(image)" 2>/dev/null | wc -l)
            
            if [ "$image_count" -gt 0 ]; then
                print_pass "$repo has $image_count image(s)"
            else
                print_skip "$repo has no images published yet"
            fi
        else
            print_fail "$repo repository not found"
            return 1
        fi
    done
}

# Test 3: Cloud Run Jobs
test_cloud_run_jobs() {
    print_header "TEST 3: Cloud Run Jobs"
    
    expected_jobs=("vil-load-corpus" "vil-extract-notions" "vil-gap-analysis")
    
    for job in "${expected_jobs[@]}"; do
        print_test "Checking $job..."
        if gcloud run jobs describe "$job" \
            --region="$REGION" \
            --project="$PROJECT_ID" >/dev/null 2>&1; then
            print_pass "$job exists"
            
            # Get job details
            status=$(gcloud run jobs describe "$job" \
                --region="$REGION" \
                --project="$PROJECT_ID" \
                --format="value(status.state)" 2>/dev/null || echo "UNKNOWN")
            
            echo "  └─ Status: ${status:-READY}"
        else
            print_fail "$job not found"
            return 1
        fi
    done
}

# Test 4: Cloud Scheduler
test_cloud_scheduler() {
    print_header "TEST 4: Cloud Scheduler Jobs"
    
    expected_schedules=("vil-load-corpus" "vil-extract-notions" "vil-gap-analysis")
    
    for job in "${expected_schedules[@]}"; do
        print_test "Checking scheduler for $job..."
        if gcloud scheduler jobs describe "$job" \
            --location="$REGION" \
            --project="$PROJECT_ID" >/dev/null 2>&1; then
            
            state=$(gcloud scheduler jobs describe "$job" \
                --location="$REGION" \
                --project="$PROJECT_ID" \
                --format="value(state)")
            
            if [[ "$state" == "ENABLED" ]]; then
                print_pass "Scheduler for $job is ENABLED"
            else
                print_pass "Scheduler for $job exists (State: $state)"
            fi
        else
            print_fail "Scheduler for $job not found"
            return 1
        fi
    done
}

# Test 5: Secret Manager
test_secret_manager() {
    print_header "TEST 5: Google Cloud Secret Manager"
    
    expected_secrets=(
        "llm-api-key"
        "dataforseo-login"
        "dataforseo-password"
        "neo4j-uri"
        "neo4j-user"
        "neo4j-password"
        "supabase-url"
        "supabase-key"
        "supabase-service-role-key"
        "stripe-secret-key"
        "stripe-webhook-secret"
    )
    
    secret_count=$(gcloud secrets list --project="$PROJECT_ID" --format="value(name)" | wc -l)
    echo "Found $secret_count secrets in Secret Manager"
    
    for secret in "${expected_secrets[@]}"; do
        print_test "Checking $secret..."
        if gcloud secrets describe "$secret" --project="$PROJECT_ID" >/dev/null 2>&1; then
            version=$(gcloud secrets describe "$secret" \
                --project="$PROJECT_ID" \
                --format="value(labels.version)" 2>/dev/null || echo "unknown")
            print_pass "$secret configured"
        else
            print_fail "$secret not found (expected)"
        fi
    done
}

# Test 6: Cloud Run Services
test_cloud_run_services() {
    print_header "TEST 6: Cloud Run Services"
    
    print_test "Checking for existing Cloud Run services..."
    services=$(gcloud run services list --region="$REGION" --project="$PROJECT_ID" --format="value(SERVICE)")
    
    if [[ -z "$services" ]]; then
        print_skip "No services deployed yet (expected before frontend deployment)"
    else
        while IFS= read -r service; do
            print_pass "Service found: $service"
            url=$(gcloud run services describe "$service" \
                --region="$REGION" \
                --project="$PROJECT_ID" \
                --format="value(status.url)")
            echo "  └─ URL: $url"
        done <<< "$services"
    fi
}

# Test 7: IAM & Service Accounts
test_iam_service_accounts() {
    print_header "TEST 7: IAM Service Accounts"
    
    expected_accounts=(
        "github-actions@${PROJECT_ID}.iam.gserviceaccount.com"
        "vil-jobs-runner@${PROJECT_ID}.iam.gserviceaccount.com"
        "vil-scheduler@${PROJECT_ID}.iam.gserviceaccount.com"
    )
    
    for account in "${expected_accounts[@]}"; do
        print_test "Checking $account..."
        if gcloud iam service-accounts describe "$account" \
            --project="$PROJECT_ID" >/dev/null 2>&1; then
            print_pass "$account exists"
        else
            print_fail "$account not found"
        fi
    done
}

# Test 8: GitHub Configuration
test_github_config() {
    print_header "TEST 8: GitHub Configuration Check"
    
    print_test "Checking for GitHub CLI..."
    if command -v gh &> /dev/null; then
        print_pass "GitHub CLI installed"
        
        print_test "Checking GitHub repository..."
        repo=$(gh repo view --json nameWithOwner --jq '.nameWithOwner' 2>/dev/null || echo "")
        if [[ -n "$repo" ]]; then
            print_pass "Repository: $repo"
            
            # List GitHub secrets (names only, not values)
            print_test "Checking GitHub secrets..."
            secrets=$(gh secret list --repo="$repo" 2>/dev/null || echo "")
            if [[ -n "$secrets" ]]; then
                echo "$secrets" | while IFS= read -r line; do
                    secret_name=$(echo "$line" | awk '{print $1}')
                    echo "  └─ Secret: $secret_name"
                done
            fi
        else
            print_skip "GitHub CLI not fully configured"
        fi
    else
        print_skip "GitHub CLI not installed (gh command not found)"
    fi
}

# Test 9: Workflow Files
test_workflow_files() {
    print_header "TEST 9: GitHub Actions Workflows"
    
    workflows=(
        ".github/workflows/deploy-frontend.yml"
        ".github/workflows/publish-pipeline.yml"
        ".github/workflows/ci.yml"
    )
    
    for workflow in "${workflows[@]}"; do
        print_test "Checking $workflow..."
        if [[ -f "$workflow" ]]; then
            print_pass "$workflow exists"
            
            # Basic validation
            if grep -q "on:" "$workflow"; then
                triggers=$(grep -A 5 "^on:" "$workflow" | head -6)
                echo "  └─ Triggers: $(echo "$triggers" | tr '\n' ' ')"
            fi
        else
            print_fail "$workflow not found"
        fi
    done
}

# Test 10: Docker Configuration
test_docker() {
    print_header "TEST 10: Docker Configuration"
    
    print_test "Checking Docker availability..."
    if command -v docker &> /dev/null; then
        docker_version=$(docker --version)
        print_pass "Docker installed: $docker_version"
    else
        print_skip "Docker not available in this environment (expected in Codespace)"
        print_skip "Rebuild Codespace with Docker-in-Docker support to build images locally"
    fi
}

# Test 11: Local Project Structure
test_project_structure() {
    print_header "TEST 11: Project Structure Validation"
    
    directories=(
        "apps/web"
        "pipeline"
        "dbt"
        "graph"
        "scripts"
    )
    
    for dir in "${directories[@]}"; do
        print_test "Checking $dir..."
        if [[ -d "$dir" ]]; then
            print_pass "$dir found"
        else
            print_fail "$dir missing"
        fi
    done
    
    files=(
        "apps/web/Dockerfile"
        "apps/web/next.config.ts"
        "apps/web/package.json"
        "pipeline/Dockerfile"
        "dbt/dbt_project.yml"
    )
    
    for file in "${files[@]}"; do
        print_test "Checking $file..."
        if [[ -f "$file" ]]; then
            print_pass "$file found"
        else
            print_fail "$file missing"
        fi
    done
}

# Test 12: Environment Variables
test_env_vars() {
    print_header "TEST 12: Environment Variables Check"
    
    if [[ -f ".env" ]]; then
        print_pass ".env file exists"
        
        required_vars=(
            "GCP_PROJECT_ID"
            "NEO4J_URI"
            "NEO4J_USER"
            "NEO4J_PASSWORD"
            "DATAFORSEO_LOGIN"
            "DATAFORSEO_PASSWORD"
        )
        
        for var in "${required_vars[@]}"; do
            if grep -q "$var" .env 2>/dev/null; then
                print_pass "$var configured in .env"
            else
                print_fail "$var not found in .env"
            fi
        done
    else
        print_skip ".env file not found (may be needed for local testing)"
    fi
}

# Test 13: Git Status
test_git_status() {
    print_header "TEST 13: Git Repository Status"
    
    print_test "Checking git branch..."
    current_branch=$(git rev-parse --abbrev-ref HEAD)
    print_pass "Current branch: $current_branch"
    
    print_test "Checking for uncommitted changes..."
    if [[ -z $(git status --porcelain) ]]; then
        print_pass "No uncommitted changes"
    else
        changes=$(git status --porcelain | wc -l)
        print_skip "$changes files have uncommitted changes"
    fi
    
    print_test "Checking git remote..."
    remote_url=$(git config --get remote.origin.url)
    print_pass "Remote: $remote_url"
}

# Main test execution
main() {
    echo -e "${BLUE}"
    cat << "EOF"
 ╭─────────────────────────────────────────────────────╮
 │  Vantedge Legal Intelligence - Deployment Tests     │
 │  Complete Infrastructure Validation Suite           │
 ╰─────────────────────────────────────────────────────╯
EOF
    echo -e "${NC}"
    
    echo "Project: $PROJECT_ID"
    echo "Region: $REGION"
    echo "Timestamp: $(date -u +'%Y-%m-%d %H:%M:%S UTC')"
    
    # Run all tests
    test_gcp_auth || true
    test_artifact_registry || true
    test_cloud_run_jobs || true
    test_cloud_scheduler || true
    test_secret_manager || true
    test_cloud_run_services || true
    test_iam_service_accounts || true
    test_github_config || true
    test_workflow_files || true
    test_docker || true
    test_project_structure || true
    test_env_vars || true
    test_git_status || true
    
    # Print summary
    print_header "TEST SUMMARY"
    
    total=$((PASSED + FAILED + SKIPPED))
    echo -e "Total Tests: $total"
    echo -e "${GREEN}Passed: $PASSED${NC}"
    echo -e "${RED}Failed: $FAILED${NC}"
    echo -e "${YELLOW}Skipped: $SKIPPED${NC}"
    
    if [ "$FAILED" -eq 0 ]; then
        echo -e "\n${GREEN}✓ All critical tests passed!${NC}"
        return 0
    else
        echo -e "\n${RED}✗ Some tests failed. Please review the output above.${NC}"
        return 1
    fi
}

# Run tests
main
