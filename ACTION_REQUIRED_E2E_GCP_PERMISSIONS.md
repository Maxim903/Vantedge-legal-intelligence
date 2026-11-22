# ⚠️ ACTION REQUIRED: Fix E2E Test GCP Permissions

**Status**: 🔴 BLOCKING - E2E tests cannot run  
**Timeline**: ~5 minutes to fix  
**Owner**: @Maxim903

---

## 🎯 What Happened

The E2E test workflow on PR #23 failed with:

```
BigQuery error: Access Denied - User does not have bigquery.datasets.create permission
```

**Why**: The GitHub Actions service account lacks BigQuery permissions needed to run E2E tests.

---

## ✅ Fix (Choose One)

### Option A: Automated Script (FASTEST - 2 min) ⭐

```bash
cd /workspaces/Vantedge-legal-intelligence
./scripts/fix-e2e-gcp-permissions.sh
```

**What it does**:
- ✅ Verifies you're authenticated to GCP
- ✅ Checks the service account exists
- ✅ Adds `BigQuery User` role
- ✅ Adds `BigQuery Data Editor` role
- ✅ Verifies permissions are applied

**Time**: ~2 minutes

---

### Option B: GCP Console (VISUAL - 3 min)

1. Open: https://console.cloud.google.com/iam-admin/iam?project=test-barometre-juridique
2. Find this row: `vantedge-legal-intelligence-gha-runner@test-barometre-juridique.iam.gserviceaccount.com`
3. Click the **pencil icon** (Edit principal)
4. Click **+ Add another role**
5. Search for: `BigQuery User` → Add it
6. Click **+ Add another role** again
7. Search for: `BigQuery Data Editor` → Add it
8. Click **Save**

**Time**: ~3 minutes

---

### Option C: gcloud CLI (FAST - 2 min)

```bash
# Authenticate to GCP first
gcloud auth login

# Set the correct project
gcloud config set project test-barometre-juridique

# Add BigQuery User role
gcloud iam service-accounts add-iam-policy-binding \
  vantedge-legal-intelligence-gha-runner@test-barometre-juridique.iam.gserviceaccount.com \
  --project=test-barometre-juridique \
  --role=roles/bigquery.user

# Add BigQuery Data Editor role
gcloud iam service-accounts add-iam-policy-binding \
  vantedge-legal-intelligence-gha-runner@test-barometre-juridique.iam.gserviceaccount.com \
  --project=test-barometre-juridique \
  --role=roles/bigquery.dataEditor
```

**Time**: ~2 minutes

---

## ✔️ Verify It Worked

After applying the fix, verify:

```bash
gcloud iam service-accounts get-iam-policy \
  vantedge-legal-intelligence-gha-runner@test-barometre-juridique.iam.gserviceaccount.com \
  --project=test-barometre-juridique
```

**Expected output should show**:
- ✅ `roles/bigquery.user`
- ✅ `roles/bigquery.dataEditor`

---

## 🚀 Re-run Tests

After permissions are fixed, re-run the E2E tests:

### Method 1: GitHub UI (Easiest)
1. Go to: https://github.com/Maxim903/Vantedge-legal-intelligence/pull/23
2. Click **"Re-run all jobs"** button
3. Wait for workflow to complete (~10-15 min)

### Method 2: Push New Commit
```bash
git commit --allow-empty -m "test: re-run E2E tests after GCP permissions fix"
git push origin test/e2e-verification
```

### Method 3: GitHub CLI
```bash
gh workflow run ci.yml -r test/e2e-verification
```

---

## 📊 Expected Result

After re-running tests, you should see:

| Job | Status |
|-----|--------|
| detect-web | ✅ PASS |
| python | ✅ PASS |
| web | ✅ PASS |
| accessibility | ✅ PASS |
| e2e | ✅ PASS |
| CodeQL | ✅ PASS |

**PR Status**: ✅ All checks passing → Ready to merge

---

## 📚 Documentation

- **Failure Details**: [E2E_TEST_WORKFLOW_FAILURE_REPORT.md](./E2E_TEST_WORKFLOW_FAILURE_REPORT.md)
- **Fix Guide**: [E2E_TEST_GCP_PERMISSIONS_FIX.md](./E2E_TEST_GCP_PERMISSIONS_FIX.md)
- **E2E Tests Guide**: [E2E_TEST_LAUNCH_GUIDE.md](./E2E_TEST_LAUNCH_GUIDE.md)
- **GCP Setup**: [GITHUB_OIDC_SETUP.md](./GITHUB_OIDC_SETUP.md)

---

## 🆘 Troubleshooting

**Q: Permission denied when running script?**
```bash
chmod +x ./scripts/fix-e2e-gcp-permissions.sh
```

**Q: gcloud not found?**
```bash
# Install Google Cloud SDK
# macOS: brew install google-cloud-sdk
# Linux: https://cloud.google.com/sdk/docs/install
# Windows: https://cloud.google.com/sdk/docs/install-cloud-sdk
```

**Q: Not authenticated?**
```bash
gcloud auth login
# Or for Application Default Credentials:
gcloud auth application-default login
```

**Q: Script still fails?**
- Run Option B (GCP Console) instead
- Or manually run the gcloud commands in Option C

---

## ⏱️ Time Estimate

| Step | Time |
|------|------|
| Fix permissions (pick one option) | 2-3 min |
| Re-run tests via GitHub UI | 10-15 min |
| Total time to completion | **12-18 min** |

---

## 🎯 Success Criteria

✅ All items checked = Ready to merge PR #23

- [ ] Permissions added to service account
- [ ] Permission fix verified
- [ ] Workflow re-run triggered
- [ ] All jobs pass in workflow
- [ ] PR shows ✅ All checks passing
- [ ] Ready to merge!

---

## 📞 Questions?

- Check: [E2E_TEST_GCP_PERMISSIONS_FIX.md](./E2E_TEST_GCP_PERMISSIONS_FIX.md)
- Read: [E2E_TEST_LAUNCH_GUIDE.md](./E2E_TEST_LAUNCH_GUIDE.md)
- Look at: Workflow logs on GitHub Actions
- File an issue on GitHub

---

**Next Step**: Choose Option A, B, or C above and apply the fix! ⚡

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>
