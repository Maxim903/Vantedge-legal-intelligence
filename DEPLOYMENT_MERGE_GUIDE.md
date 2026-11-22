# 🚀 Deployment Guide - From PR Merge to Live Deployment

## Current Status

✅ **Phase 1: Pull Request Created**
- PR #22 created: "Add comprehensive deployment test suite and infrastructure validation"
- URL: https://github.com/Maxim903/Vantedge-legal-intelligence/pull/22
- CI Workflows started and running

⏳ **Phase 2: Waiting for CI to Pass**
- Estimated duration: 15-20 minutes
- Current status: Multiple checks in progress (Python, Web, E2E, Pipeline, CodeQL)

🔜 **Phase 3-5: Merge & Deploy** (Pending CI completion)

---

## Instructions to Complete Deployment

### Step 1: Monitor CI Progress (15-20 minutes)

**Option A: Real-time Monitoring**
1. Open PR #22: https://github.com/Maxim903/Vantedge-legal-intelligence/pull/22
2. Scroll to "Checks" section to see all CI jobs
3. Click on individual jobs to see detailed logs
4. Wait for all checks to show green ✅

**Option B: GitHub Actions Dashboard**
1. Open: https://github.com/Maxim903/Vantedge-legal-intelligence/actions
2. Find the most recent workflow run
3. Monitor progress of each job
4. Wait for all to complete successfully

**What we're testing:**
- Python code quality & unit tests
- Frontend build & component tests
- Accessibility validation
- End-to-end (E2E) tests
- Pipeline Docker image build
- Security scanning (CodeQL)

---

### Step 2: Merge to Main (When CI Passes ✅)

**Once all checks show green:**

1. **Go to PR #22**
   - URL: https://github.com/Maxim903/Vantedge-legal-intelligence/pull/22

2. **Look for "Merge pull request" button**
   - It will be enabled when CI passes
   - Shows all checks have passed ✅

3. **Click "Merge pull request"**
   - Choose merge strategy (default: "Create a merge commit")
   - Add commit message if desired (optional)
   - Click "Confirm merge"

4. **Confirm the merge**
   - GitHub shows "Pull request successfully merged and closed"
   - Option to delete branch (recommended: yes)

**What happens automatically after merge:**
- Deployment workflows trigger on the `main` branch
- `publish-pipeline.yml` starts building the pipeline Docker image
- `deploy-frontend.yml` starts building and deploying the frontend

---

### Step 3: Monitor Deployment Workflows (10-30 minutes)

After merging, **two deployment workflows will start automatically:**

#### A. publish-pipeline.yml (Pipeline Image Deployment)

**Timeline:** 10-15 minutes

**What it does:**
1. ✅ Authenticates to GCP using OIDC
2. 🔨 Builds Docker image with:
   - Python 3.11
   - dbt (data transformation)
   - LLM extraction tools
   - Graph processing
3. 🧪 Runs smoke tests on the image
4. 📤 Pushes to Artifact Registry: `vil-pipeline:COMMIT_SHA`
5. 🔄 Updates Cloud Run Jobs:
   - `vil-load-corpus` (02:00 UTC)
   - `vil-extract-notions` (04:00 UTC)
   - `vil-gap-analysis` (06:00 UTC)

**Monitoring:**
- Open: https://github.com/Maxim903/Vantedge-legal-intelligence/actions
- Look for: "Build, test and deploy pipeline" workflow
- Check job logs if any failures occur

#### B. deploy-frontend.yml (Frontend Deployment)

**Timeline:** 10-15 minutes

**What it does:**
1. ✅ Authenticates to GCP using OIDC
2. 🔍 Verifies GitHub variables are set
3. 🔨 Builds Next.js Docker image with:
   - Node.js 20-alpine
   - Next.js 16
   - Supabase client
   - Stripe integration
4. 📤 Pushes to Artifact Registry: `vil-web:COMMIT_SHA`
5. 🚀 Deploys to Cloud Run:
   - Service: `vil-web`
   - Port: 3000
   - Memory: 1 Gi
   - CPU: 2 cores
   - Min instances: 1
   - Max instances: 10
6. 🏥 Performs health check
7. ✅ Verifies service is responding

**Monitoring:**
- Open: https://github.com/Maxim903/Vantedge-legal-intelligence/actions
- Look for: "Deploy Frontend to Cloud Run" workflow
- Check job logs if any failures occur

---

### Step 4: Verify Deployment Success

#### Check Images in Artifact Registry

```bash
# Check pipeline image
gcloud artifacts docker images list \
  europe-west9-docker.pkg.dev/test-barometre-juridique/vil-pipeline

# Check frontend image
gcloud artifacts docker images list \
  europe-west9-docker.pkg.dev/test-barometre-juridique/vil-frontend
```

Expected output: Images with COMMIT_SHA and latest tags

#### Verify Cloud Run Service

```bash
# Get service URL
gcloud run services describe vil-web \
  --region=europe-west9 \
  --project=test-barometre-juridique \
  --format="value(status.url)"
```

Should return something like: `https://vil-web-xxx.region-run.app`

#### Test Frontend Service

```bash
# Get the URL from above and test it
curl https://vil-web-xxx.region-run.app/
curl -v https://vil-web-xxx.region-run.app/health
```

Should return HTTP 200 response

#### Verify Cloud Run Jobs Updated

```bash
# Check if jobs have new image
gcloud run jobs describe vil-load-corpus \
  --region=europe-west9 \
  --project=test-barometre-juridique \
  --format="value(template.containers[0].image)"

gcloud run jobs describe vil-extract-notions \
  --region=europe-west9 \
  --project=test-barometre-juridique \
  --format="value(template.containers[0].image)"

gcloud run jobs describe vil-gap-analysis \
  --region=europe-west9 \
  --project=test-barometre-juridique \
  --format="value(template.containers[0].image)"
```

Should show images with new COMMIT_SHA

---

### Step 5: Manual Testing (Optional but Recommended)

#### Test Pipeline Job Execution

```bash
# Execute vil-load-corpus
gcloud run jobs execute vil-load-corpus \
  --region=europe-west9 \
  --project=test-barometre-juridique \
  --wait

# Check logs
gcloud run jobs log vil-load-corpus \
  --region=europe-west9 \
  --project=test-barometre-juridique \
  --limit=100
```

Expected: Job completes successfully, loads corpus data

```bash
# Execute vil-extract-notions
gcloud run jobs execute vil-extract-notions \
  --region=europe-west9 \
  --project=test-barometre-juridique \
  --wait

# Check logs
gcloud run jobs log vil-extract-notions \
  --region=europe-west9 \
  --project=test-barometre-juridique \
  --limit=100
```

Expected: Job completes successfully, extracts notions

```bash
# Execute vil-gap-analysis
gcloud run jobs execute vil-gap-analysis \
  --region=europe-west9 \
  --project=test-barometre-juridique \
  --wait

# Check logs
gcloud run jobs log vil-gap-analysis \
  --region=europe-west9 \
  --project=test-barometre-juridique \
  --limit=100
```

Expected: Job completes successfully, analyzes gaps

#### Test Frontend Service

1. Open the service URL in browser
2. Test sign-up/login (if Supabase configured)
3. Test payment flow (if Stripe configured)
4. Check browser console for errors

#### Verify Schedulers

```bash
# Check scheduler status
gcloud scheduler jobs list --location=europe-west9

# Manually trigger a scheduler (optional)
gcloud scheduler jobs run vil-load-corpus --location=europe-west9
```

Expected: Scheduler executes job successfully

---

## Timeline Summary

| Phase | Activity | Duration | Status |
|-------|----------|----------|--------|
| 1 | PR Created & CI Started | Done | ✅ COMPLETE |
| 2 | Wait for CI to Pass | 15-20 min | ⏳ IN PROGRESS |
| 3 | Merge to Main | ~1 min | 🔜 READY |
| 4 | Deploy Workflows Run | 20-30 min | 🔜 PENDING |
| 5 | Verification & Testing | 10-15 min | 🔜 PENDING |
| **TOTAL** | **Full Deployment** | **~1 hour** | |

---

## Troubleshooting

### If CI Fails

1. **Check the failing job logs**
   - Click on the red ❌ check in PR #22
   - Review the error message
   - Common issues:
     - Python test failures
     - E2E test timeouts
     - Build issues

2. **Fix the issue**
   - Create a new commit on `fix/infra-alignment`
   - Push to GitHub
   - CI will re-run automatically

3. **Merge when CI passes**
   - Once all checks are green ✅
   - Click "Merge pull request"

### If Deploy Fails

1. **Check GitHub Actions logs**
   - Open: https://github.com/Maxim903/Vantedge-legal-intelligence/actions
   - Click failing workflow
   - Review job logs

2. **Common issues:**
   - GitHub secrets not set → Set missing secrets
   - GitHub variables not set → Set missing variables
   - GCP permissions issue → Check service account roles
   - Supabase/Stripe misconfigured → Verify credentials

3. **Re-run failed workflow**
   - In GitHub Actions, click "Re-run failed jobs"
   - Or push a new commit to `main`

### If Frontend Service Not Responding

1. **Check service status**
   ```bash
   gcloud run services describe vil-web \
     --region=europe-west9 \
     --format="value(status.conditions)"
   ```

2. **View logs**
   ```bash
   gcloud run logs read vil-web \
     --region=europe-west9 \
     --limit=100 \
     --follow
   ```

3. **Common issues:**
   - Startup timeout → Increase timeout
   - Memory insufficient → Increase memory
   - Supabase/Stripe missing → Check environment variables
   - Health check failing → Check application health endpoint

---

## Success Criteria

✅ **Deployment is complete when:**
1. All CI checks pass in PR #22
2. PR is merged to main
3. `publish-pipeline.yml` workflow succeeds
4. `deploy-frontend.yml` workflow succeeds
5. Cloud Run jobs have new image
6. Cloud Run service responds to HTTP requests
7. Manual job execution succeeds
8. No critical errors in logs

---

## Resources

**Documentation:**
- [TESTING.md](TESTING.md) - Testing guide
- [DEPLOYMENT.md](DEPLOYMENT.md) - Full deployment guide
- [FRONTEND_DEPLOYMENT.md](FRONTEND_DEPLOYMENT.md) - Frontend guide
- [DEPLOYMENT_STATUS.md](DEPLOYMENT_STATUS.md) - Current status

**GitHub:**
- PR: https://github.com/Maxim903/Vantedge-legal-intelligence/pull/22
- Actions: https://github.com/Maxim903/Vantedge-legal-intelligence/actions
- Workflows: `.github/workflows/`

**GCP Console:**
- Cloud Run: https://console.cloud.google.com/run?project=test-barometre-juridique
- Artifact Registry: https://console.cloud.google.com/artifacts?project=test-barometre-juridique
- Cloud Scheduler: https://console.cloud.google.com/cloudscheduler?project=test-barometre-juridique
- Logs: https://console.cloud.google.com/logs?project=test-barometre-juridique

---

## Commands Reference

**Check PR Status**
```bash
gh pr view 22  # Requires GitHub CLI
```

**Check CI Workflows**
```bash
gh workflow list  # Requires GitHub CLI
```

**Monitor Deployment**
```bash
# Watch Cloud Run services
gcloud run services list --region=europe-west9

# Watch Cloud Run jobs
gcloud run jobs list --region=europe-west9

# Check recent logs
gcloud logging read --limit=50 --format=json
```

**Manual Job Testing**
```bash
# Execute all jobs in sequence
gcloud run jobs execute vil-load-corpus --region=europe-west9 --wait && \
gcloud run jobs execute vil-extract-notions --region=europe-west9 --wait && \
gcloud run jobs execute vil-gap-analysis --region=europe-west9 --wait

# View job logs
gcloud run jobs log vil-load-corpus --region=europe-west9 --limit=200
gcloud run jobs log vil-extract-notions --region=europe-west9 --limit=200
gcloud run jobs log vil-gap-analysis --region=europe-west9 --limit=200
```

**Get Service URL**
```bash
gcloud run services describe vil-web --region=europe-west9 \
  --format="value(status.url)"
```

---

**Generated:** 2026-11-22  
**Status:** Ready for Merge & Deployment  
**Next Action:** Monitor CI and merge when all checks pass ✅
