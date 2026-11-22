# 🔧 E2E Test GCP Permissions Fix

**Last Updated**: 2026-11-22  
**Status**: 🔴 ACTION REQUIRED  
**Severity**: Critical - Blocking E2E Tests

---

## 📋 Problem Summary

The E2E test workflow failed with:

```
BigQuery error in mk operation: Access Denied: Project test-barometre-juridique:
User does not have bigquery.datasets.create permission in project test-barometre-juridique.
```

**Root Cause**: The GitHub OIDC Service Account (`Vantedge-legal-intelligence-gha-runner`) lacks BigQuery IAM permissions required to:
- Create BigQuery datasets (`bigquery.datasets.create`)
- Run BigQuery queries (`bigquery.jobs.create`)
- Read/write BigQuery tables (`bigquery.dataEditor`)

---

## 🎯 Solution

### Option 1: Add IAM Roles to Service Account (RECOMMENDED ⭐)

**Location**: GCP Console → IAM & Admin → Service Accounts

**Steps**:

1. **Identify the Service Account**
   ```
   Service Account Email: vantedge-legal-intelligence-gha-runner@test-barometre-juridique.iam.gserviceaccount.com
   ```

2. **Add Required Roles** via GCP Console:
   - Open: https://console.cloud.google.com/iam-admin/iam?project=test-barometre-juridique
   - Click on the service account row to expand
   - Click "Edit" (pencil icon)
   - Add these roles:
     - ✅ **BigQuery Data Editor** (`roles/bigquery.dataEditor`)
     - ✅ **BigQuery User** (`roles/bigquery.user`)
     - ✅ **BigQuery Admin** (`roles/bigquery.admin`) [if needed for dataset creation]

   OR use the CLI:

   ```bash
   gcloud iam service-accounts add-iam-policy-binding \
     vantedge-legal-intelligence-gha-runner@test-barometre-juridique.iam.gserviceaccount.com \
     --project=test-barometre-juridique \
     --role=roles/bigquery.dataEditor

   gcloud iam service-accounts add-iam-policy-binding \
     vantedge-legal-intelligence-gha-runner@test-barometre-juridique.iam.gserviceaccount.com \
     --project=test-barometre-juridique \
     --role=roles/bigquery.user
   ```

3. **Verify Permissions**
   ```bash
   gcloud iam service-accounts get-iam-policy \
     vantedge-legal-intelligence-gha-runner@test-barometre-juridique.iam.gserviceaccount.com \
     --project=test-barometre-juridique
   ```

4. **Re-run E2E Tests**
   - Push a new commit or re-run PR #23 workflow
   - Verify all permissions are now available

---

### Option 2: Use Custom IAM Role (ADVANCED)

If you need fine-grained permissions:

```bash
gcloud iam roles create bigQueryE2ERunner \
  --project=test-barometre-juridique \
  --title="BigQuery E2E Test Runner" \
  --description="Minimal permissions for E2E test BigQuery operations" \
  --permissions=bigquery.datasets.create,bigquery.datasets.get,bigquery.datasets.update,bigquery.jobs.create,bigquery.jobs.get,bigquery.jobs.list,bigquery.tables.create,bigquery.tables.delete,bigquery.tables.get,bigquery.tables.list,bigquery.tables.update,bigquery.tables.getData,bigquery.tables.updateData
```

Then bind this role to the service account.

---

## 📊 Current IAM Status

| Role | Permission | Status |
|------|-----------|--------|
| BigQuery Data Editor | Write & read BigQuery tables | ❌ Missing |
| BigQuery User | Submit BigQuery jobs | ❌ Missing |
| BigQuery Admin | Manage datasets & tables | ❌ Missing |
| Project Editor | Full project access | ⚠️ Check if assigned |

---

## 🔄 Workflow After Fix

1. ✅ GitHub Actions triggers workflow
2. ✅ Authenticates via OIDC → Service Account
3. ✅ Service Account has BigQuery permissions
4. ✅ Workflow creates BigQuery dataset `marts_e2e`
5. ✅ Loads test fixtures (marts.sql)
6. ✅ Starts Supabase, Stripe, Next.js
7. ✅ Runs E2E tests
8. ✅ Reports results ✅ or ❌

---

## 🧪 Verification Steps

After applying permissions:

```bash
# 1. Check service account permissions
gcloud iam service-accounts get-iam-policy \
  vantedge-legal-intelligence-gha-runner@test-barometre-juridique.iam.gserviceaccount.com \
  --project=test-barometre-juridique \
  --format=json | jq '.bindings[] | select(.role | contains("bigquery")) | .role'

# 2. Test BigQuery access
gcloud auth activate-service-account \
  --key-file=/path/to/service-account-key.json

bq ls --project_id=test-barometre-juridique
bq mk --dataset --location=europe-west9 test-barometre-juridique:test_permissions_check
bq rm test-barometre-juridique:test_permissions_check

# 3. Re-run workflow
gh workflow run ci.yml -f test/e2e-verification
```

---

## 🚀 Next Steps

1. **Apply Permissions** (5 min)
   - Use Option 1 above via GCP Console or CLI
   - Verify permissions with the check command

2. **Verify Fix** (2 min)
   - Re-run PR #23 workflow
   - Check logs: GitHub Actions → PR → Checks → E2E job

3. **Document Results** (1 min)
   - If successful: Update this file and merge PR
   - If failed: Check logs for new error messages

---

## 📝 Notes

- **GCP Project**: `test-barometre-juridique`
- **Service Account**: `vantedge-legal-intelligence-gha-runner`
- **Region**: `europe-west9`
- **BigQuery Dataset**: `marts_e2e` (created by workflow)
- **OIDC Provider**: GitHub Actions (configured in Terraform/CDM)

---

## 🔗 Related

- [E2E Test Documentation](./E2E_TEST_LAUNCH_GUIDE.md)
- [GCP Deployment Info](./DEPLOYMENT.md)
- [GitHub OIDC Setup](./GITHUB_OIDC_SETUP.md)

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>
