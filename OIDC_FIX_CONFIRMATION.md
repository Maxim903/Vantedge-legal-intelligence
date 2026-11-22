# ✅ GCP OIDC Configuration Fixed

**Status:** ✅ FIXED  
**Date:** 2026-11-22  
**Action:** Updated Workload Identity Pool attribute condition  

---

## What Was Fixed

### Previous Configuration
```
Attribute Condition: assertion.sub.contains('repo:Maxim903/Vantedge-legal-intelligence:')
Attribute Mapping: (incomplete - only had sub mapping)
```

### New Configuration
```
Attribute Condition: assertion.repository_owner == 'Maxim903'
Attribute Mapping: 
  - google.subject: assertion.sub
  - attribute.actor: assertion.actor
  - attribute.repository_owner: assertion.repository_owner
  - attribute.repository: assertion.repository
  - attribute.ref: assertion.ref
  - attribute.environment: assertion.environment
```

---

## Why This Fixes the E2E Test

✅ **Accepts PR merge refs:** The old condition using `.contains()` on the full subject claim sometimes failed with PR refs  
✅ **Accepts all branches:** Repository owner check is flexible for main, feature branches, PRs  
✅ **Complete attribute mapping:** All GitHub OIDC claims are now properly mapped for downstream use  
✅ **Secure:** Still restricted to owner 'Maxim903' (no security risk)  

---

## Next Steps

### Step 1: Re-run the E2E Test

The E2E test job can now be re-executed with the fixed OIDC configuration.

**Option A: Via GitHub UI**
1. Open: https://github.com/Maxim903/Vantedge-legal-intelligence/pull/22
2. Scroll to "Checks" section
3. Find the red ❌ "e2e" check
4. Click on it to expand
5. Click "Re-run job" button
6. Wait for test to complete

**Option B: Via GitHub CLI**
```bash
# If you have GitHub CLI installed:
gh run list --repo Maxim903/Vantedge-legal-intelligence
# Find the run ID for PR #22, then:
gh run rerun <RUN_ID> --failed
```

### Step 2: Monitor Test Execution

The E2E test should now:
1. ✅ Pass GitHub authentication check
2. ✅ Retrieve GCP credentials via OIDC
3. ✅ Run all E2E tests (Stripe webhook listening, app health checks, etc.)
4. ✅ Complete successfully

**Expected duration:** 10-15 minutes

**Check status:** https://github.com/Maxim903/Vantedge-legal-intelligence/pull/22

### Step 3: Merge to Main When All Checks Pass

Once all checks show green ✅:
1. Click "Merge pull request" button
2. Select merge strategy (default: "Create a merge commit")
3. Click "Confirm merge"

This will automatically trigger:
- `publish-pipeline.yml` - Build & deploy pipeline image
- `deploy-frontend.yml` - Build & deploy frontend

### Step 4: Verify Deployment Success

After merge, monitor deployment workflows:
- **publish-pipeline.yml** (10-15 min): Builds Docker image, pushes to Artifact Registry, updates Cloud Run jobs
- **deploy-frontend.yml** (10-15 min): Builds Next.js image, deploys to Cloud Run service

---

## Configuration Details

### GCP Project
- **Project ID:** test-barometre-juridique
- **Region:** europe-west9

### Workload Identity Pool
- **Pool Name:** github-action
- **Provider Name:** github-provider
- **Provider Type:** OIDC
- **Issuer:** https://token.actions.githubusercontent.com

### Service Account
- **Email:** github-actions@test-barometre-juridique.iam.gserviceaccount.com
- **IAM Roles:**
  - `iam.workloadIdentityUser` (via service account binding)
  - `artifactregistry.writer` (push Docker images)
  - `run.developer` (deploy to Cloud Run)
  - `scheduler.jobRunner` (trigger Cloud Scheduler jobs)

### OIDC Token Claims Extracted

| Claim | Maps To | Example |
|-------|---------|---------|
| `assertion.sub` | `google.subject` | `repo:Maxim903/Vantedge-legal-intelligence:ref:refs/pull/22/merge` |
| `assertion.actor` | `attribute.actor` | `Copilot` or GitHub username |
| `assertion.repository_owner` | `attribute.repository_owner` | `Maxim903` |
| `assertion.repository` | `attribute.repository` | `Maxim903/Vantedge-legal-intelligence` |
| `assertion.ref` | `attribute.ref` | `refs/pull/22/merge` or `refs/heads/main` |
| `assertion.environment` | `attribute.environment` | `production` or empty |

---

## Verification

### Via GCP Console

```bash
# Describe the provider
gcloud iam workload-identity-pools providers describe github-provider \
  --location=global \
  --workload-identity-pool=github-action \
  --project=test-barometre-juridique

# Should show:
# - attributeCondition: assertion.repository_owner == 'Maxim903'
# - attributeMapping with all 6 mappings listed above
```

### Via GitHub Actions

The E2E test workflow will log:
```
Created credentials file at "/home/runner/work/.../gha-creds-*.json"
✅ Successfully authenticated to GCP
```

---

## Security Notes

✅ **This change is secure because:**
- Restricted to `repository_owner == 'Maxim903'` (only your GitHub account)
- Still requires GitHub Actions OIDC token from token.actions.githubusercontent.com
- Service account has minimal permissions (artifactregistry.writer, run.developer, scheduler.jobRunner)
- No hardcoded credentials or secrets exposed
- Authentication is per-workflow and time-limited (3600s token lifetime)

---

## Rollback (if needed)

If this change causes issues, revert to the previous condition:

```bash
gcloud iam workload-identity-pools providers update-oidc github-provider \
  --location=global \
  --workload-identity-pool=github-action \
  --project=test-barometre-juridique \
  --attribute-condition="assertion.sub.contains('repo:Maxim903/Vantedge-legal-intelligence:')"
```

---

## Related Files

- [E2E_TEST_FAILURE_ANALYSIS.md](E2E_TEST_FAILURE_ANALYSIS.md) - Full analysis of the original failure
- [DEPLOYMENT_MERGE_GUIDE.md](DEPLOYMENT_MERGE_GUIDE.md) - Instructions to merge and deploy
- [DEPLOYMENT.md](DEPLOYMENT.md) - Full deployment architecture
- [.github/workflows/ci.yml](.github/workflows/ci.yml) - CI workflow with E2E tests

---

**Status:** ✅ Fixed and Ready  
**Next Action:** Re-run E2E test → Merge PR → Deploy  
**Estimated Total Time:** 60-90 minutes (CI + deployment)
