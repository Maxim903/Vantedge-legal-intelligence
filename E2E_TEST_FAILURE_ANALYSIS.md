# 🔴 E2E Test Failure Analysis

**Date:** 2026-11-22  
**PR:** #22  
**Branch:** fix/infra-alignment  
**Failure:** Google OIDC Authentication Error

---

## Problem Summary

The E2E test workflow failed during GitHub Actions CI/CD pipeline execution due to **GCP Workload Identity OIDC authentication failure**.

### Error Details

```
Error: google-github-actions/auth failed with: 
  failed to generate Google Cloud federated token for 
  //iam.googleapis.com/projects/31886648583/locations/global/workloadIdentityPools/github-action/providers/github-provider: 
  {
    "error":"unauthorized_client",
    "error_description":"The given credential is rejected by the attribute condition."
  }
```

**Root Cause:** The Workload Identity Pool **attribute condition** does not match the GitHub Actions OIDC token being presented.

---

## Technical Analysis

### What Happened

1. **E2E test job started** in GitHub Actions workflow
2. **GCP authentication step executed** using `google-github-actions/auth@v2`
3. **OIDC flow initiated:**
   - GitHub Actions generated an OIDC token with claims like:
     - `iss` (issuer): https://token.actions.githubusercontent.com
     - `sub` (subject): repo:Maxim903/Vantedge-legal-intelligence:ref:refs/pull/22/merge
     - `repository`: Maxim903/Vantedge-legal-intelligence
     - `environment`: (env variable)
   - Token sent to GCP's Workload Identity Provider
4. **WIP checked attribute conditions** configured in `github-action` pool
5. **Attribute mismatch detected** → Token rejected → Authentication failed

### Likely Causes

The Workload Identity Pool's attribute condition likely uses one of these patterns:

```python
# Pattern 1: Too restrictive (requires specific branch)
attribute.ref == "refs/heads/main"  # ← WRONG for PR refs!

# Pattern 2: Repository mismatch
attribute.repository == "wrong/repo"  # ← WRONG if set incorrectly

# Pattern 3: Environment restriction
attribute.environment == "production"  # ← WRONG if no env set

# Pattern 4: Incompatible claim format
attribute.actor == "specific_user"  # ← WRONG if checking GitHub Actions actor
```

The error suggests the **attribute condition is checking for `refs/heads/main`** (or similar), but the E2E test runs on **`refs/pull/22/merge`** (PR merge ref), which doesn't match.

---

## Solution

### Step 1: Check Current Workload Identity Pool Configuration

```bash
# Get the attribute condition currently set
gcloud iam workload-identity-pools providers describe github-provider \
  --location=global \
  --workload-identity-pool=github-action \
  --project=test-barometre-juridique \
  --format="value(attributeCondition)"
```

Expected output: Shows the current condition (e.g., `"attribute.ref == \"refs/heads/main\""`)

### Step 2: Update Attribute Condition to Accept All PRs & Main

Update the condition to accept:
- Push to `main` branch
- Pull requests (all branches)
- Pull request merge refs

```bash
# Update the attribute condition
gcloud iam workload-identity-pools providers update github-provider \
  --location=global \
  --workload-identity-pool=github-action \
  --project=test-barometre-juridique \
  --attribute-condition="assertion.repository_owner == 'Maxim903'"
```

**OR for more restrictive access (main + PRs only):**

```bash
gcloud iam workload-identity-pools providers update github-provider \
  --location=global \
  --workload-identity-pool=github-action \
  --project=test-barometre-juridique \
  --attribute-condition="assertion.repository_owner == 'Maxim903' && (assertion.ref == 'refs/heads/main' || assertion.ref_type == 'pull')"
```

**OR for maximum flexibility (any branch, any PR):**

```bash
gcloud iam workload-identity-pools providers update github-provider \
  --location=global \
  --workload-identity-pool=github-action \
  --project=test-barometre-juridique \
  --attribute-condition="assertion.repository_owner == 'Maxim903'"
```

### Step 3: Verify the Update

```bash
# Confirm the new condition was applied
gcloud iam workload-identity-pools providers describe github-provider \
  --location=global \
  --workload-identity-pool=github-action \
  --project=test-barometre-juridique \
  --format="value(attributeCondition)"
```

### Step 4: Re-run the E2E Test

Go to GitHub Actions and re-run the failed E2E test job:

1. Open: https://github.com/Maxim903/Vantedge-legal-intelligence/pull/22
2. Scroll to "Checks" section
3. Find the failed "e2e" check
4. Click "Re-run job" button
5. Wait for the test to complete (should now succeed ✅)

---

## Recommended Attribute Conditions

### Option A: Repository Owner Only (Most Flexible)

```
assertion.repository_owner == 'Maxim903'
```

**Pros:**
- Allows all workflows in your repository
- Simplest to maintain
- No branch restrictions

**Cons:**
- Any branch can authenticate (may be security risk in multi-team setting)

### Option B: Main + PRs Only (Recommended)

```
assertion.repository_owner == 'Maxim903' && 
(assertion.ref == 'refs/heads/main' || assertion.ref_type == 'pull')
```

**Pros:**
- Restricts to main branch + all PRs
- Good balance of security and flexibility
- Allows CI/CD and testing workflows

**Cons:**
- Feature branches cannot authenticate
- Slightly more complex condition

### Option C: Main Only (Most Restrictive)

```
assertion.repository_owner == 'Maxim903' && assertion.ref == 'refs/heads/main'
```

**Pros:**
- Only production deployments can authenticate
- Highest security level

**Cons:**
- Breaks all PR testing workflows
- Not suitable for CI/CD testing

---

## Available GitHub OIDC Token Attributes

When a GitHub Actions workflow runs, the OIDC token includes these attributes:

| Attribute | Example Value | Used For |
|-----------|---------------|----------|
| `assertion.repository_owner` | `Maxim903` | Identify repository owner |
| `assertion.repository` | `Maxim903/Vantedge-legal-intelligence` | Identify specific repository |
| `assertion.ref` | `refs/heads/main` or `refs/pull/22/merge` | Identify branch or PR |
| `assertion.ref_type` | `branch` or `pull` | Branch vs PR distinction |
| `assertion.environment` | `production` | Identify environment |
| `assertion.actor` | `Copilot` or `username` | Identify who triggered the workflow |
| `assertion.workflow` | `ci.yml` | Identify which workflow |
| `assertion.event_name` | `push`, `pull_request`, etc. | Identify trigger event |

---

## GitHub Actions OIDC Token Reference

**GitHub Actions OIDC Provider:** `token.actions.githubusercontent.com`

**Token Claims Include:**
- `iss`: https://token.actions.githubusercontent.com
- `aud`: (Repository URL)
- `sub`: repo:Maxim903/Vantedge-legal-intelligence:ref:refs/pull/22/merge
- `repository`: Maxim903/Vantedge-legal-intelligence
- `repository_owner`: Maxim903
- `repository_owner_id`: (GitHub user ID)
- `run_id`: (Workflow run ID)
- `run_number`: (Workflow run number)
- `environment`: (Job environment if set)
- `actor`: (GitHub username or bot name)
- `actor_id`: (GitHub user ID)
- `workflow`: (Workflow filename)
- `head_ref`: (PR source branch)
- `base_ref`: (PR target branch)
- `event_name`: (Event that triggered workflow)
- `ref`: (Full ref path)
- `ref_type`: (branch or tag)

---

## Verification After Fix

Once you apply the fix, verify by:

### 1. Check Configuration Applied

```bash
gcloud iam workload-identity-pools providers describe github-provider \
  --location=global \
  --workload-identity-pool=github-action \
  --project=test-barometre-juridique
```

Should show your updated `attributeCondition`

### 2. Re-run E2E Test

```bash
# Via GitHub UI:
# 1. Open PR #22
# 2. Go to Checks
# 3. Click red "e2e" check
# 4. Click "Re-run job"
```

### 3. Monitor Test Completion

Expect:
- GCP auth step succeeds ✅
- Remaining E2E tests proceed ✅
- Test completes with success ✅

### 4. Verify All CI Checks Pass

```bash
# When all checks green:
# 1. Click "Merge pull request"
# 2. Confirm merge
# 3. Deployment workflows will trigger automatically
```

---

## Impact of This Fix

| Component | Impact | Status |
|-----------|--------|--------|
| E2E Tests | Will pass in CI/CD | Fixed ✅ |
| PR Merging | Unblocked | Ready |
| Deployment | Will proceed after merge | Ready |
| Security | No change (still restricted to Maxim903) | Maintained |
| Other Workflows | python, web, accessibility, etc. | Unaffected |

---

## Commands Summary

**Quick Fix (Repository Owner Only):**
```bash
gcloud iam workload-identity-pools providers update github-provider \
  --location=global \
  --workload-identity-pool=github-action \
  --project=test-barometre-juridique \
  --attribute-condition="assertion.repository_owner == 'Maxim903'"
```

**Verify:**
```bash
gcloud iam workload-identity-pools providers describe github-provider \
  --location=global \
  --workload-identity-pool=github-action \
  --project=test-barometre-juridique \
  --format="value(attributeCondition)"
```

**Re-run E2E Test:**
1. Open PR #22: https://github.com/Maxim903/Vantedge-legal-intelligence/pull/22
2. Find "e2e" check → Click "Re-run job"
3. Wait for completion

---

## References

- [Google Cloud Workload Identity Federation](https://cloud.google.com/iam/docs/workload-identity-federation)
- [GitHub Actions OIDC with GCP](https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/about-security-hardening-with-openid-connect)
- [Google Cloud Attribute Conditions](https://cloud.google.com/iam/docs/conditions-overview)

---

**Status:** Ready for Implementation  
**Estimated Fix Time:** 2 minutes (1 gcloud command)  
**Re-test Time:** 5-10 minutes (E2E test execution)  
**Deployment Impact:** None (fix only affects authentication)
