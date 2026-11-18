# 🚀 Guide de Déploiement Complet - Vantedge Legal Intelligence

## Architecture de Déploiement

```
Frontend (Next.js)
├─ Vercel / Cloud Run / Self-hosted
└─ Public URL

Backend (Pipeline)
├─ Docker Image (Artifact Registry)
├─ Cloud Run Jobs
├─ Cloud Scheduler (Orchestration)
└─ BigQuery (Data warehouse)

Data Layer
├─ Neo4j Aura (Graphe)
├─ Cloud Storage (Raw data)
├─ BigQuery (Marts)
└─ Supabase (Auth/Realtime)
```

---

## 📋 Étapes de Déploiement

### PHASE 0️⃣: Configurer GitHub OIDC pour GitHub Actions (2-3 min)

**✅ Configuration déjà créée pour le projet `test-barometre-juridique`**

Les ressources suivantes ont été créées :
- Workload Identity Pool : `github-action`
- Provider OIDC : `github-provider`
- Service Account : `github-actions@test-barometre-juridique.iam.gserviceaccount.com`

**À faire : Ajouter les secrets GitHub**

1. Allez sur votre repository GitHub : https://github.com/Maxim903/Vantedge-legal-intelligence
2. Cliquez sur **Settings** > **Secrets and variables** > **Actions**
3. Créez 3 secrets (New repository secret) :

| Secret | Valeur |
|--------|--------|
| `GCP_PROJECT_ID` | `test-barometre-juridique` |
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | `projects/31886648583/locations/global/workloadIdentityPools/github-action/providers/github-provider` |
| `GCP_SERVICE_ACCOUNT` | `github-actions@test-barometre-juridique.iam.gserviceaccount.com` |

Exemple de workflow GitHub Actions utilisant OIDC :

```yaml
name: Deploy Pipeline

on:
  push:
    branches: [ main ]
  workflow_dispatch:

env:
  REGISTRY: europe-west9-docker.pkg.dev
  IMAGE_NAME: vil-pipeline

jobs:
  deploy:
    runs-on: ubuntu-latest
    permissions:
      contents: 'read'
      id-token: 'write'

    steps:
      - uses: actions/checkout@v4

      - name: Authenticate to Google Cloud
        uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: ${{ secrets.GCP_WORKLOAD_IDENTITY_PROVIDER }}
          service_account: ${{ secrets.GCP_SERVICE_ACCOUNT }}

      - name: Set up Cloud SDK
        uses: google-github-actions/setup-gcloud@v2

      - name: Configure Docker
        run: |
          gcloud auth configure-docker ${{ env.REGISTRY }}

      - name: Build and Push Docker Image
        run: |
          docker build -f pipeline/Dockerfile \
            -t ${{ env.REGISTRY }}/${{ secrets.GCP_PROJECT_ID }}/vil-pipeline/vil-pipeline:latest \
            -t ${{ env.REGISTRY }}/${{ secrets.GCP_PROJECT_ID }}/vil-pipeline/vil-pipeline:${{ github.sha }} .
          
          docker push ${{ env.REGISTRY }}/${{ secrets.GCP_PROJECT_ID }}/vil-pipeline/vil-pipeline:latest
          docker push ${{ env.REGISTRY }}/${{ secrets.GCP_PROJECT_ID }}/vil-pipeline/vil-pipeline:${{ github.sha }}

      - name: Deploy to Cloud Run
        run: |
          gcloud run jobs update vil-load-corpus \
            --image=${{ env.REGISTRY }}/${{ secrets.GCP_PROJECT_ID }}/vil-pipeline/vil-pipeline:latest \
            --region=europe-west9 \
            --project=${{ secrets.GCP_PROJECT_ID }}
```

---

### PHASE 1️⃣: Setup Infra Google Cloud (5-10 min)

```bash
# 1. Activer les APIs
gcloud services enable \
  run.googleapis.com \
  scheduler.googleapis.com \
  secretmanager.googleapis.com \
  bigquery.googleapis.com \
  storage.googleapis.com \
  artifactregistry.googleapis.com \
  compute.googleapis.com

# 2. Créer le repository Docker Artifact Registry
gcloud artifacts repositories create vil-pipeline \
  --repository-format=docker \
  --location=europe-west9

# 3. Configurer l'authentification Docker
gcloud auth configure-docker europe-west9-docker.pkg.dev
```

### PHASE 2️⃣: Créer les Comptes de Service (5 min)

```bash
PROJECT_ID="votre-projet-gcp"

# Compte de service pour les Jobs
gcloud iam service-accounts create vil-jobs-runner \
  --display-name="Vantedge Legal Intelligence - Jobs Runner"

# Compte de service pour Scheduler
gcloud iam service-accounts create vil-scheduler \
  --display-name="Vantedge Legal Intelligence - Scheduler"

# Accorder les permissions nécessaires
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:vil-jobs-runner@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/bigquery.dataEditor"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:vil-jobs-runner@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/storage.objectUser"
```

### PHASE 3️⃣: Créer les Secrets (5 min)

```bash
# Créer les secrets dans Secret Manager
echo -n "$LLM_API_KEY" | gcloud secrets create llm-api-key --data-file=-
echo -n "$DATAFORSEO_LOGIN" | gcloud secrets create dataforseo-login --data-file=-
echo -n "$DATAFORSEO_PASSWORD" | gcloud secrets create dataforseo-password --data-file=-
echo -n "$NEO4J_URI" | gcloud secrets create neo4j-uri --data-file=-
echo -n "$NEO4J_USER" | gcloud secrets create neo4j-user --data-file=-
echo -n "$NEO4J_PASSWORD" | gcloud secrets create neo4j-password --data-file=-

# Accorder l'accès au compte de service
for secret in llm-api-key dataforseo-login dataforseo-password neo4j-uri neo4j-user neo4j-password; do
  gcloud secrets add-iam-policy-binding "$secret" \
    --member="serviceAccount:vil-jobs-runner@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
done
```

### PHASE 4️⃣: Build et Push l'Image Docker (10-15 min)

```bash
# Build depuis la racine
docker build -f pipeline/Dockerfile -t vil-pipeline:latest .

# Tag pour Artifact Registry
docker tag vil-pipeline:latest \
  europe-west9-docker.pkg.dev/PROJECT_ID/vil-pipeline/vil-pipeline:latest

# Push
docker push europe-west9-docker.pkg.dev/PROJECT_ID/vil-pipeline/vil-pipeline:latest

# Vérifier
docker run --rm europe-west9-docker.pkg.dev/PROJECT_ID/vil-pipeline/vil-pipeline:latest --help
```

### PHASE 5️⃣: Déployer les Jobs Cloud Run (5-10 min)

```bash
# Exporter les variables
export PROJECT_ID="votre-projet"
export IMAGE="europe-west9-docker.pkg.dev/${PROJECT_ID}/vil-pipeline/vil-pipeline:latest"
export JOB_SERVICE_ACCOUNT="vil-jobs-runner@${PROJECT_ID}.iam.gserviceaccount.com"
export SCHEDULER_SERVICE_ACCOUNT="vil-scheduler@${PROJECT_ID}.iam.gserviceaccount.com"
export GCS_BUCKET_RAW="votre-bucket-raw"
export CORPUS_BUCKET="votre-corpus-bucket"
export CORPUS_OBJECT="legi-archive.zip"
export EXTRACTION_MAX_COST="100.00"
export EXTRACTION_COST_PER_CALL="0.01"
export VOLUMES_MAX_COST="50.00"
export VOLUMES_COST_PER_CALL="0.001"
export LLM_SECRET="llm-api-key"
export DATAFORSEO_LOGIN_SECRET="dataforseo-login"
export DATAFORSEO_PASSWORD_SECRET="dataforseo-password"
export NEO4J_URI_SECRET="neo4j-uri"
export NEO4J_USER_SECRET="neo4j-user"
export NEO4J_PASSWORD_SECRET="neo4j-password"

# Exécuter le script de déploiement
bash scripts/deploy_jobs.sh
```

### PHASE 6️⃣: Déployer le Frontend (5-10 min)

**Option A: Vercel (Recommandé)**
```bash
npm install -g vercel
cd apps/web
vercel deploy --prod
```

**Option B: Cloud Run**
```bash
cd apps/web
docker build -t nextjs-app . -f - << 'DOCKERFILE'
FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --frozen-lockfile
COPY . .
RUN npm run build
EXPOSE 3000
CMD ["npm", "start"]
DOCKERFILE

docker tag nextjs-app gcr.io/PROJECT_ID/nextjs-app
docker push gcr.io/PROJECT_ID/nextjs-app

gcloud run deploy nextjs-app \
  --image gcr.io/PROJECT_ID/nextjs-app \
  --region europe-west9 \
  --allow-unauthenticated
```

---

## 🔗 Variables d'Environnement

| Variable | Valeur |
|----------|--------|
| `GCP_PROJECT_ID` | Votre projet GCP |
| `NEO4J_URI` | Depuis `.env` |
| `NEO4J_USER` | Depuis `.env` |
| `NEO4J_PASSWORD` | Depuis `.env` |
| `DATAFORSEO_LOGIN` | Depuis `.env` |
| `DATAFORSEO_PASSWORD` | Depuis `.env` |
| `LLM_API_KEY` | Depuis `.env` |
| `APP_URL` | URL publique de votre app |

---

## ✅ Vérifications Post-Déploiement

```bash
# 1. Vérifier les jobs
gcloud run jobs list --region europe-west9

# 2. Exécuter un job manuellement
gcloud run jobs execute vil-load-corpus --region europe-west9

# 3. Consulter les logs
gcloud run jobs log vil-load-corpus --region europe-west9 --limit 50

# 4. Vérifier le scheduler
gcloud scheduler jobs list --location europe-west9

# 5. Tester l'API
curl https://votre-app-url.com/

# 6. Vérifier Neo4j
cypher-shell -a "neo4j+s://86e6c762.databases.neo4j.io" "MATCH (n) RETURN COUNT(n) as count"
```

---

## 🚨 Troubleshooting

| Problème | Solution |
|----------|----------|
| Erreur d'authentification Docker | `gcloud auth configure-docker` |
| Secrets non trouvés | Vérifier les permissions IAM |
| Job échoue | `gcloud run jobs log <nom-job> --limit 50` |
| BigQuery quota dépassée | Augmenter les quotas ou réduire le volume |

---

## 📊 Checklist Déploiement

- [ ] APIs Google Cloud activées
- [ ] Artifact Registry créé
- [ ] Comptes de service créés
- [ ] Secrets stockés dans Secret Manager
- [ ] Image Docker buildée et pushée
- [ ] Jobs Cloud Run déployés
- [ ] Scheduler configuré
- [ ] Frontend déployé (Vercel ou Cloud Run)
- [ ] Variables d'environnement configurées
- [ ] Tests fonctionnels passés
- [ ] Logs de déploiement vérifiés
- [ ] Alerte/monitoring configuré

---

## 🎯 Coûts Estimés (Mensuel)

| Service | Usage | Coût |
|---------|-------|------|
| Cloud Run Jobs | 100 h/mois | ~$10 |
| Cloud Scheduler | 60 exécutions | ~$0.20 |
| BigQuery | 1TB queries | ~$5-10 |
| Cloud Storage | 10GB | ~$0.20 |
| Neo4j Aura | Professional | ~$500 |
| Artifact Registry | 10GB | ~$0.10 |
| **Total** | | **~$515/mois** |

---

## 📚 Ressources

- [Google Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Cloud Scheduler Guide](https://cloud.google.com/scheduler/docs)
- [BigQuery Setup](https://cloud.google.com/bigquery/docs/quickstarts/load-data-console)
- [Neo4j Aura](https://neo4j.com/cloud/aura/)
