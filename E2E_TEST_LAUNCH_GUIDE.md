# 🚀 E2E Test Launch Guide

**Last Updated:** 2026-11-22  
**Purpose:** Complete guide to run E2E tests via GitHub Actions CI/CD  
**Expected Duration:** 10-15 minutes  
**Success Rate:** ✅ Fully automated

---

## Why GitHub Actions is the Best Option

The local Codespace environment lacks Docker, which prevents starting the required infrastructure (Supabase, PostgreSQL, Redis). However, the GitHub Actions CI/CD pipeline **automatically handles everything**:

| Aspect | Local | GitHub Actions |
|--------|-------|-----------------|
| Docker | ❌ Not available | ✅ Full Docker support |
| Supabase | ❌ Manual setup | ✅ Auto-started |
| PostgreSQL | ❌ Manual setup | ✅ Service container |
| Test Isolation | ❌ Requires cleanup | ✅ Fresh environment |
| Environment Vars | ⚠️ Manual export | ✅ Auto-loaded from secrets |
| Reporting | ⚠️ Local only | ✅ Artifacts + summary |

---

## Quick Start (5 minutes)

### Step 1: Create a Test Branch
```bash
git checkout -b test/e2e-verification
```

### Step 2: Commit Your Changes
```bash
git add -A
git commit -m "test: re-run E2E tests to verify infrastructure

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

### Step 3: Push to GitHub
```bash
git push origin test/e2e-verification
```

### Step 4: Create Pull Request
```bash
# Navigate to: https://github.com/Maxim903/Vantedge-legal-intelligence/pulls
# Click: "Compare & pull request"
# Set:
#   - Base: main
#   - Compare: test/e2e-verification
# Click: "Create pull request"
```

### Step 5: Monitor Test Execution
```
On the PR page, scroll down to "Checks" section
You will see:
├─ ci (Python + TypeScript linting, unit tests)
├─ e2e (Playwright tests with Stripe flow)
└─ deploy-frontend (Frontend deployment)

Wait 10-15 minutes for all checks to complete
```

### Step 6: Review Results
```
When all checks pass ✅:
1. Click "Merge pull request"
2. Deployment workflow triggers automatically
3. Frontend deploys to Cloud Run
4. Access at: https://vil-web-xxxxx.run.app
```

---

## Detailed GitHub Actions Workflow

### What Happens Automatically

```
1. Push to Branch
   ↓
2. GitHub Detects Changes
   ↓
3. CI Workflow Triggers (.github/workflows/ci.yml)
   ├─ Python tests (pytest)
   ├─ TypeScript lint (eslint)
   └─ Next.js build
   ↓
4. E2E Test Job Starts
   ├─ Authentication: GitHub OIDC → GCP
   ├─ Infrastructure: Docker Compose with services
   │  ├─ PostgreSQL 15
   │  ├─ Redis
   │  ├─ Supabase Emulator
   │  └─ Local Stripe Mock (optional)
   ├─ Build: Next.js application
   ├─ Deploy: To temporary Cloud Run instance
   └─ Test: Playwright E2E suite
   ↓
5. Results Collection
   ├─ Test output: GitHub Actions console
   ├─ Artifacts: Screenshots, videos, traces
   ├─ Summary: Check status badge
   └─ Report: Detailed failure logs (if any)
   ↓
6. Merge Decision
   ├─ All checks pass ✅ → Ready to merge
   └─ Any check fails ❌ → Review logs and fix
```

### GitHub Actions Workflow Files

**Primary Workflow:**
- `.github/workflows/ci.yml` - Runs on every push/PR

**Key Jobs:**
1. `python-tests` - Run Python tests with pytest
2. `web-tests` - Run TypeScript/JS tests with Vitest
3. `e2e` - Run Playwright E2E tests
4. `accessibility` - Run accessibility tests

---

## Manual Workflow Triggers (Alternative)

If you want to trigger tests without creating a branch:

### Option A: Trigger from GitHub UI

```
1. Go to: https://github.com/Maxim903/Vantedge-legal-intelligence
2. Click: "Actions" tab
3. Find workflow: "CI"
4. Click: "Run workflow"
5. Select: Branch to test
6. Click: "Run workflow"
```

### Option B: Trigger via GitHub CLI

```bash
# List available workflows
gh workflow list

# Run CI workflow on current branch
gh workflow run ci.yml --ref $(git rev-parse --abbrev-ref HEAD)

# Monitor execution
gh run list --workflow=ci.yml --limit=1

# View detailed logs
gh run view <run-id> --log
```

### Option C: Trigger via API (Advanced)

```bash
curl -X POST \
  -H "Authorization: token YOUR_GITHUB_TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  "https://api.github.com/repos/Maxim903/Vantedge-legal-intelligence/actions/workflows/ci.yml/dispatches" \
  -d '{"ref":"test/e2e-verification"}'
```

---

## Monitoring Test Execution

### On GitHub UI

1. **During Execution:**
   ```
   PR Page > Checks > e2e (orange dot - running)
   
   Details visible:
   - Current job
   - Elapsed time
   - Log output
   ```

2. **After Completion:**
   ```
   PR Page > Checks > e2e (green ✅ or red ❌)
   
   Click the check to see:
   - Full test output
   - Failure details
   - Screenshot artifacts
   ```

### Via Terminal

```bash
# Watch the workflow in real-time
gh run watch <run-id>

# View specific job logs
gh run view <run-id> --log --jq '.jobs.[].steps[]'

# Download artifacts
gh run download <run-id> --dir ./test-artifacts
```

---

## Expected Test Output

### Successful E2E Run ✅

```
Running 2 test using 1 worker

  ✓ 1 e2e/analyse.spec.ts:38:1 › inscription, abonnement, ouverture et historique (45.2s)
  ✓ 2 e2e/accessibilite.spec.ts:12:1 › vérification des critères WCAG (38.7s)

  2 passed (84s)
```

### Failed E2E Run ❌

```
Running 2 tests using 1 worker

  ✘ 1 e2e/analyse.spec.ts:38:1 › inscription, abonnement, ouverture et historique (45.2s)
  ✓ 2 e2e/accessibilite.spec.ts:12:1 › vérification des critères WCAG (38.7s)

  1 passed, 1 failed (84s)

Error Details:
- Test failed at: await page.getByRole("button", { name: "Souscrire au plan pro" }).click()
- Reason: Element not found on page
- Screenshot: test-results/[test-name]/screenshot.png
```

---

## Understanding Test Flow

### Test: "inscription, abonnement, ouverture et historique"

This test validates the complete user journey:

```
1. PRE-TEST SETUP (beforeAll)
   ├─ Check Stripe credentials exist
   ├─ Verify Supabase local instance running
   ├─ Validate Stripe price configuration
   └─ Initialize Stripe SDK

2. REGISTRATION PHASE
   ├─ Generate unique test email
   ├─ Navigate to /inscription
   ├─ Fill registration form
   ├─ Submit form
   └─ Verify "Espace connecté" page shown

3. SUBSCRIPTION PHASE
   ├─ Navigate to /app/compte/abonnement
   ├─ Click "Souscrire au plan pro"
   ├─ Complete Stripe checkout
   ├─ Verify subscription confirmed
   └─ Check user role upgraded to "pro"

4. ANALYSIS PHASE (Optional - if implemented)
   ├─ Create new project
   ├─ Create analysis
   ├─ Verify results
   └─ Check analysis history

5. POST-TEST CLEANUP (afterAll)
   └─ Delete test customer from Stripe
```

---

## Troubleshooting Failed E2E Tests

### Common Failures & Fixes

#### 1. OIDC Authentication Error
```
Error: google-github-actions/auth failed with:
  failed to generate Google Cloud federated token
  ...attribute_condition rejected
```

**Cause:** Workload Identity Pool condition doesn't match PR ref  
**Fix:** Update attribute condition in GCP  
```bash
gcloud iam workload-identity-pools providers update github-provider \
  --location=global \
  --workload-identity-pool=github-action \
  --project=test-barometre-juridique \
  --attribute-condition="assertion.repository_owner == 'Maxim903'"
```

#### 2. Stripe Credentials Missing
```
Error: Une clé Stripe sk_test_ et un prix de test sont requis
```

**Cause:** GitHub Secrets not configured  
**Fix:** Verify in GitHub Settings:
1. Settings > Secrets and variables > Actions
2. Check STRIPE_SECRET_KEY exists and starts with `sk_test_`
3. Check STRIPE_PRICE_PRO exists and starts with `price_`

#### 3. Supabase Connection Failed
```
Error: Le test E2E exige une instance Supabase locale dédiée
```

**Cause:** Service container failed to start  
**Fix:** Check Docker images in workflow:
```yaml
services:
  postgres:
    image: postgres:15
    # or rebuild Supabase container
```

#### 4. Element Not Found
```
Error: Locator.click: Timeout 30000ms exceeded
```

**Cause:** UI element not rendered in time  
**Fix:** 
- Check application logs in workflow
- Review screenshots in artifacts
- Increase timeout in playwright.config.ts
- Verify CSS selectors in test

#### 5. Network/API Errors
```
Error: Failed to connect to Stripe API
```

**Cause:** Stripe API key invalid or rate-limited  
**Fix:**
- Verify key is for test environment
- Check Stripe rate limits
- Review API error response in logs

---

## Accessing Test Artifacts

### In GitHub Actions UI

1. Go to: PR > Checks > e2e > "View full details"
2. Scroll to: "Artifacts"
3. Available artifacts:
   - `test-results` - Playwright test results
   - `screenshots` - Page screenshots
   - `videos` - Test recordings
   - `traces` - Playwright traces for debugging

### Via Terminal

```bash
# Download all artifacts
gh run download <run-id> --dir ./test-artifacts

# List artifacts
ls -la test-artifacts/

# View screenshots
open test-artifacts/screenshots/

# View test results
cat test-artifacts/test-results/index.html
```

---

## Integrating with Deployment

### Automatic Deployment After E2E Pass

When E2E tests pass ✅ in CI/CD:

```
1. E2E Tests Pass ✅
   ↓
2. All CI Checks Pass ✅
   ↓
3. PR Merged to Main
   ↓
4. GitHub Actions Triggers Deployment
   ├─ build-docker-image.yml
   ├─ push-to-artifact-registry.yml
   └─ deploy-to-cloud-run.yml
   ↓
5. Infrastructure Updated
   ├─ Cloud Run image updated
   ├─ Environment variables synced
   ├─ Database migrations run
   └─ Health checks executed
   ↓
6. Live Service Updated
   └─ Users see new version automatically
```

---

## Security & Best Practices

### Secrets Management

**Never commit secrets to repository:**
```bash
# ❌ BAD - commits secret to git
echo "sk_test_xyz123" >> .env

# ✅ GOOD - use GitHub Secrets
# Settings > Secrets and variables > Actions > New secret
```

**Available Secrets (verify they exist):**
- STRIPE_SECRET_KEY
- STRIPE_WEBHOOK_SECRET
- GCP_SERVICE_ACCOUNT
- SUPABASE_SERVICE_ROLE_KEY

### Test Isolation

The E2E test creates a unique test user for each run:

```typescript
// Each run gets unique credentials
const email = `e2e-${randomUUID()}@example.test`;
const password = `E2e-${randomUUID()}!`;
```

Cleanup removes the test Stripe customer:

```typescript
// After test completes
const customers = await stripe.customers.list({ email });
if (customers.data[0]) await stripe.customers.del(customers.data[0].id);
```

---

## Performance Optimization

### Test Parallelization

Currently tests run sequentially:
```
test.beforeAll: 2s
analyse.spec.ts: 45s
accessibilite.spec.ts: 38s
test.afterAll: 2s
---
Total: ~87s
```

To run in parallel (if independent):
```bash
# Update playwright.config.ts
fullyParallel: true,  // was: false
```

### Artifact Storage

Large artifacts (videos, traces) increase workflow time:

**Current Settings:**
```typescript
trace: "off"       // Playwright trace disabled
screenshot: "off"  // Screenshots disabled
video: "off"       // Video recording disabled
```

**To enable (for debugging):**
```typescript
trace: "on-first-retry"    // Only on failure
screenshot: "only-on-failure"
video: "retain-on-failure"
```

---

## Workflow Diagram

```
┌─────────────────────────────────────────┐
│  Developer Push / Create PR             │
│  git push origin test/e2e-verification  │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  GitHub Detects Changes                 │
│  - Triggers .github/workflows/ci.yml    │
└──────────────┬──────────────────────────┘
               │
        ┌──────┴──────────────┬────────────────┐
        ▼                     ▼                ▼
    ┌────────┐          ┌────────┐       ┌────────┐
    │ Python │          │TypeScp │       │   E2E  │
    │ Tests  │          │  Tests │       │ Tests  │
    │        │          │        │       │        │
    │  ...   │          │  ...   │       │  Auth  │
    │  OK ✅ │          │  OK ✅ │       │Docker  │
    └────────┘          └────────┘       │Supabase│
        │                   │            │Test    │
        └───────────┬───────┘            │  OK ✅ │
                    │                    └────────┘
                    └─────────┬────────────┘
                              │
                    ┌─────────▼──────────┐
                    │  All Checks Pass ✅│
                    └─────────┬──────────┘
                              │
                    ┌─────────▼──────────┐
                    │  Merge PR to Main  │
                    └─────────┬──────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
        ┌──────────┐    ┌──────────┐   ┌──────────┐
        │  Build   │    │  Build   │   │   Push   │
        │ Pipeline │    │ Frontend │   │  Registry│
        │  Image   │    │  Image   │   │          │
        └────┬─────┘    └────┬─────┘   └────┬─────┘
             │               │              │
        ┌────▼───────────────▼──────────────▼──┐
        │   Deploy to Cloud Run (Production)   │
        │   - Frontend service updated         │
        │   - Automatic health checks          │
        │   - Gradual rollout (if configured) │
        └─────────────────┬────────────────────┘
                          │
                ┌─────────▼─────────┐
                │  Live in Production
                │  Users see updates │
                └───────────────────┘
```

---

## Post-Deployment Verification

After deployment, verify E2E tests are still passing:

```bash
# 1. Access deployed frontend
open https://vil-web-xxxxx.run.app

# 2. Manual smoke test
# - Register new account
# - Try subscription
# - Create analysis

# 3. Run E2E tests again
# - Push to test branch
# - GitHub Actions runs automated tests
# - Verify results

# 4. Monitor production
gcloud run logs read vil-web --region=europe-west9 --limit=50
```

---

## Command Reference

### Create Test Branch & Run E2E Tests

```bash
# 1. Create branch
git checkout -b test/e2e-verification

# 2. Commit changes
git add -A
git commit -m "test: re-run E2E tests"

# 3. Push to GitHub
git push origin test/e2e-verification

# 4. Create PR (via GitHub UI or CLI)
gh pr create --title "test: E2E verification" --body "Re-running E2E tests" --base main

# 5. Monitor tests
gh run list --workflow=ci.yml --limit=1

# 6. View detailed logs
gh run view <run-id> --log

# 7. Download artifacts (if needed)
gh run download <run-id> --dir ./test-artifacts
```

### Advanced: Re-run Failed Jobs

```bash
# Re-run failed checks
gh run rerun <run-id>

# Re-run specific job
gh run rerun <run-id> --failed
```

---

## FAQ

**Q: Why not run tests locally?**  
A: Docker is not available in the Codespace. GitHub Actions provides full Docker support.

**Q: How long do tests take?**  
A: Total pipeline: 10-15 minutes (including build, deploy, and E2E tests)

**Q: Can I skip E2E tests?**  
A: Not recommended. Tests catch regressions. If needed, use `[skip ci]` in commit message (not recommended for production).

**Q: What if a test fails?**  
A: 
1. GitHub Actions shows failure in PR checks
2. Click on failed check to see detailed logs
3. Download test artifacts (screenshots, videos)
4. Fix the issue locally
5. Push fix to same branch
6. GitHub Actions automatically re-runs

**Q: Where are test results stored?**  
A: 
- GitHub Actions UI: PR > Checks > e2e > Details
- Artifacts: PR > Checks > e2e > Artifacts
- Locally: gh run download to retrieve artifacts

**Q: Can I run tests in parallel?**  
A: Yes, change `fullyParallel: true` in playwright.config.ts

**Q: How do I add more E2E tests?**  
A: Create new .spec.ts files in apps/web/e2e/

---

## Summary

| Step | Action | Time | Status |
|------|--------|------|--------|
| 1 | Create test branch | 1 min | Manual |
| 2 | Commit and push | 2 min | Manual |
| 3 | Create PR | 1 min | Manual |
| 4 | GitHub Actions runs CI | 5 min | Automatic |
| 5 | E2E tests execute | 3 min | Automatic |
| 6 | Review results | 2 min | Manual |
| **Total** | **Full E2E cycle** | **~15 min** | **✅ Complete** |

---

**Next Step:** Push to GitHub and monitor the workflow!

```bash
git push origin test/e2e-verification
# 🚀 E2E tests running automatically
```

