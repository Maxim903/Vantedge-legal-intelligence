# 📊 Statut du Déploiement - Vantedge Legal Intelligence

**Date** : 2026-11-18  
**Projet GCP** : `test-barometre-juridique`  
**Région** : `europe-west9`

---

## ✅ Phases Complétées

### PHASE 0️⃣ : GitHub OIDC - ✅ Complétée
- [x] Workload Identity Pool créé : `github-action`
- [x] OIDC Provider créé : `github-provider`
- [x] Service Account créé : `github-actions@test-barometre-juridique.iam.gserviceaccount.com`
- [x] IAM Roles configurés (artifactregistry.writer, run.developer, secretmanager.secretAccessor)
- [x] Workflow GitHub Actions prêt : `.github/workflows/deploy-pipeline.yml`
- [ ] ⏳ **ACTION** : Ajouter 3 secrets dans GitHub Settings > Secrets and variables > Actions
  - `GCP_PROJECT_ID`
  - `GCP_WORKLOAD_IDENTITY_PROVIDER`
  - `GCP_SERVICE_ACCOUNT`

### PHASE 1️⃣ : Setup Infra Google Cloud - ✅ Complétée
- [x] APIs activées (Cloud Run, Scheduler, Secret Manager, BigQuery, etc.)
- [x] Artifact Registry créé : `vil-pipeline` (docker, europe-west9)
- [x] Docker authentification configurée
- [x] Repo URL : `europe-west9-docker.pkg.dev/test-barometre-juridique/vil-pipeline`

### PHASE 2️⃣ : Comptes de Service - ✅ Complétée
- [x] Service Account créé : `vil-jobs-runner@test-barometre-juridique.iam.gserviceaccount.com`
  - Rôles : BigQuery Data Editor, Storage Object User, Secret Manager Secret Accessor
- [x] Service Account créé : `vil-scheduler@test-barometre-juridique.iam.gserviceaccount.com`
  - Rôles : Cloud Run Admin, Service Account User (sur vil-jobs-runner)
- [x] IAM Bindings configurés

### PHASE 3️⃣ : Secrets - ✅ Complétée
- [x] Secret Manager API activée
- [x] 8 secrets créés (avec placeholder "PLACEHOLDER")
  - [x] llm-api-key
  - [x] dataforseo-login
  - [x] dataforseo-password
  - [x] neo4j-uri
  - [x] neo4j-user
  - [x] neo4j-password
  - [x] supabase-url
  - [x] supabase-key
- [x] Accès IAM configuré pour vil-jobs-runner
- [ ] ⏳ **ACTION** : Mettre à jour les secrets avec les vraies valeurs

### PHASE 4️⃣ : Cloud Run Jobs - ⏳ En attente d'image Docker
- [ ] Image Docker disponible dans Artifact Registry
- [ ] Cloud Run Jobs créés (vil-load-corpus, vil-extract-notions, vil-gap-analysis)
- [ ] Service Account configuré pour les jobs
- **Prochaines étapes** :
  1. Ajouter les 3 secrets GitHub (PHASE 0)
  2. Faire un push sur `main` → GitHub Actions build et push l'image
  3. Exécuter `bash scripts/deploy-jobs.sh`

### PHASE 5️⃣ : Cloud Scheduler - ⏳ En attente des Cloud Run Jobs
- [ ] Cloud Scheduler API activée
- [ ] Jobs Schedulers créés avec horaires cron
  - 02:00 UTC : vil-load-corpus
  - 04:00 UTC : vil-extract-notions
  - 06:00 UTC : vil-gap-analysis
- **Action** : Exécuter `bash scripts/setup-scheduler.sh`

### PHASE 6️⃣ : Frontend - ⏳ Pas encore démarrée
- [ ] Frontend (Next.js) déployé sur Vercel ou Cloud Run
- [ ] Variables d'environnement configurées

---

## 📋 Ressources Créées

| Ressource | Nom | Type | Status |
|-----------|-----|------|--------|
| Artifact Registry | `vil-pipeline` | Docker | ✅ Créé |
| Service Account | `vil-jobs-runner` | IAM | ✅ Créé |
| Service Account | `vil-scheduler` | IAM | ✅ Créé |
| Workload Identity Pool | `github-action` | OAuth | ✅ Créé |
| OIDC Provider | `github-provider` | OAuth | ✅ Créé |
| Secrets (8) | llm-api-key, etc. | Secret Manager | ✅ Créés |
| Cloud Run Jobs (3) | vil-load-corpus, etc. | Compute | ⏳ Attente d'image |
| Cloud Scheduler (3) | Scheduler jobs | Scheduler | ⏳ À créer |

---

## 📝 Prochaines Étapes - Priorité

### 1️⃣ URGENT - Secrets GitHub (5 min)
```
URL: https://github.com/Maxim903/Vantedge-legal-intelligence/settings/secrets/actions

Ajouter 3 secrets:
- GCP_PROJECT_ID: test-barometre-juridique
- GCP_WORKLOAD_IDENTITY_PROVIDER: projects/31886648583/locations/global/workloadIdentityPools/github-action/providers/github-provider
- GCP_SERVICE_ACCOUNT: github-actions@test-barometre-juridique.iam.gserviceaccount.com
```

### 2️⃣ IMPORTANT - Mettre à jour les secrets GCP (10 min)
```bash
# Pour chaque secret, remplacer PLACEHOLDER par votre valeur réelle
echo -n "VOTRE_CLÉ_LLM" | gcloud secrets versions add llm-api-key --data-file=-
echo -n "VOTRE_LOGIN_DATAFORSEO" | gcloud secrets versions add dataforseo-login --data-file=-
# ... etc
```

### 3️⃣ Faire un push sur main (automatique)
```bash
git push origin main
# GitHub Actions va:
# - Builder l'image Docker
# - Pousser vers Artifact Registry
# - Mettre à jour les Cloud Run Jobs (s'ils existent)
```

### 4️⃣ Déployer les Cloud Run Jobs (5 min)
```bash
bash scripts/deploy-jobs.sh
```

### 5️⃣ Configurer Cloud Scheduler (5 min)
```bash
bash scripts/setup-scheduler.sh
```

### 6️⃣ Déployer le Frontend (10-15 min)
```bash
# Option A: Vercel
npm install -g vercel
cd apps/web
vercel deploy --prod

# Option B: Cloud Run
bash scripts/deploy-frontend.sh
```

---

## 🔧 Scripts Disponibles

| Script | Description | Status |
|--------|-------------|--------|
| `.github/workflows/deploy-pipeline.yml` | Workflow GitHub Actions | ✅ Prêt |
| `scripts/test-github-oidc.sh` | Test configuration OIDC | ✅ Exécutable |
| `scripts/deploy-jobs.sh` | Déployer Cloud Run Jobs | ✅ Prêt |
| `scripts/setup-scheduler.sh` | Configurer Cloud Scheduler | ✅ Prêt |
| `GITHUB_OIDC_SETUP.md` | Guide détaillé OIDC | ✅ Documentation |
| `DEPLOYMENT.md` | Guide complet de déploiement | ✅ Mis à jour |

---

## 🎯 Résumé de l'État

**Completion**: 60% ✅ (Infra) + 10% ⏳ (Jobs) + 10% ⏳ (Scheduler) + 10% ⏳ (Frontend) + 10% ⏳ (Config)

**Prêt à avancer**:
- ✅ Infrastructure GCP entièrement configurée
- ✅ GitHub OIDC prêt pour CI/CD automatisé
- ✅ Secrets créés et accessibles
- ⏳ En attente : Secrets GitHub + Push pour déclencher GitHub Actions

**Blocage actuel** : Les secrets GitHub doivent être ajoutés pour que GitHub Actions puisse construire l'image Docker.

---

## 📞 Support

Pour tester la configuration OIDC:
```bash
bash scripts/test-github-oidc.sh
```

Pour vérifier l'état des ressources GCP:
```bash
# Lister les artifacts
gcloud artifacts docker images list europe-west9-docker.pkg.dev/test-barometre-juridique/vil-pipeline

# Lister les secrets
gcloud secrets list --project=test-barometre-juridique

# Lister les service accounts
gcloud iam service-accounts list --project=test-barometre-juridique
```

---

**Généré par** : Copilot  
**Dernière mise à jour** : 2026-11-18  
**Validé avec** : `bash scripts/test-github-oidc.sh`
