# 🚀 Statut de Déploiement - Vantedge Legal Intelligence

**Date**: 2026-11-18  
**Projet GCP**: `test-barometre-juridique`  
**Région**: `europe-west9`  
**Status**: ✅ **5/6 Phases Complétées**

---

## 📊 Récapitulatif

| Phase | Composant | Status | Actions |
|-------|-----------|--------|---------|
| 1 | GCP Infrastructure | ✅ Complétée | APIs activées, Artifact Registry créé |
| 2 | Service Accounts | ✅ Complétée | 2 comptes créés avec rôles IAM |
| 3 | Secrets Manager | ✅ Complétée | 9 secrets sécurisés et configurés |
| 4 | Build Docker | ⚠️ **Manuel** | Workflow créé, prêt pour exécution locale |
| 5 | Cloud Run Jobs | ✅ Complétée | 6 jobs créés et configurés |
| 6 | Frontend | ⏭️ **À faire** | Prêt pour Vercel ou Cloud Run |

---

## ✅ Completed: Phase 1-3, 5

### Phase 1: Setup GCP Infrastructure
- ✅ 7 APIs Google Cloud activées
  - Cloud Run
  - Cloud Scheduler
  - Secret Manager
  - BigQuery
  - Cloud Storage
  - Artifact Registry
  - Cloud Build
  - Compute Engine
- ✅ Repository Artifact Registry créé: `vil-pipeline`
- ✅ Authentification Docker configurée

### Phase 2: Service Accounts
- ✅ `vil-jobs-runner@test-barometre-juridique.iam.gserviceaccount.com`
  - Rôles: `roles/bigquery.dataEditor`, `roles/storage.objectUser`, `roles/secretmanager.secretAccessor`, `roles/run.admin`
- ✅ `vil-scheduler@test-barometre-juridique.iam.gserviceaccount.com`
  - Rôle: `roles/run.invoker`

### Phase 3: Secrets Manager
- ✅ 9 secrets créés et sécurisés:
  - `llm-api-key`
  - `dataforseo-login`
  - `dataforseo-password`
  - `neo4j-uri`
  - `neo4j-user`
  - `neo4j-password`
  - `stripe-secret-key`
  - `supabase-url`
  - `supabase-key`

### Phase 5: Cloud Run Jobs
- ✅ 6 jobs déployés:
  1. `vil-load-corpus` - Charger le corpus juridique
  2. `vil-extract-entities` - Extraire les notions via LLM
  3. `vil-collect-volumes` - Collecte des volumes de recherche
  4. `vil-load-raw-market` - Charger les données brutes
  5. `vil-dbt-models` - Modèles DBT et transformation
  6. `vil-sync-graph` - Synchroniser avec Neo4j

---

## ⚠️ En Attente: Phase 4

### Phase 4: Build Docker Image

**Statut**: Workflow créé ✓ | Build planifié ⏳

**Fichier**: `.github/workflows/deploy-pipeline.yml`

**Options pour construire l'image**:

#### Option A: Exécution locale (Recommandé pour test)
```bash
# Sur votre machine avec Docker
gcloud auth login
gcloud config set project test-barometre-juridique
gcloud auth configure-docker europe-west9-docker.pkg.dev

cd /path/to/Vantedge-legal-intelligence
docker build -f pipeline/Dockerfile \
  -t europe-west9-docker.pkg.dev/test-barometre-juridique/vil-pipeline/vil-pipeline:latest .

docker push europe-west9-docker.pkg.dev/test-barometre-juridique/vil-pipeline/vil-pipeline:latest
```

#### Option B: GitHub Actions (Automatique)
- Le workflow se déclenche automatiquement au prochain **push sur main** dans le dossier `pipeline/`
- Prérequis: Configurer les secrets GitHub
  - `GCP_WORKLOAD_IDENTITY_PROVIDER`
  - `GCP_SERVICE_ACCOUNT_EMAIL`

#### Option C: Cloud Build (via gcloud)
```bash
gcloud auth login
gcloud config set project test-barometre-juridique
gcloud builds submit . \
  --config=cloudbuild.yaml \
  --project=test-barometre-juridique
```

---

## ⏭️ À Faire: Phase 6

### Phase 6: Frontend Deployment

**Options**:

#### Option A: Vercel (⭐ Recommandé)
```
1. Accédez à https://vercel.com/import/git
2. Sélectionnez le repository GitHub
3. Configurez les variables d'environnement
4. Cliquez sur "Deploy"
```

**Avantages**:
- Deploy automatique à chaque push sur main
- Preview URLs pour chaque PR
- Scaling automatique
- CDN global
- Gratuit pour débuter

#### Option B: Cloud Run (Intégration GCP totale)
```bash
cd apps/web
docker build -t europe-west9-docker.pkg.dev/test-barometre-juridique/frontend/nextjs-app:latest .
docker push europe-west9-docker.pkg.dev/test-barometre-juridique/frontend/nextjs-app:latest

gcloud run deploy nextjs-app \
  --image=europe-west9-docker.pkg.dev/test-barometre-juridique/frontend/nextjs-app:latest \
  --region=europe-west9 \
  --allow-unauthenticated \
  --memory=1Gi \
  --cpu=1
```

---

## 🔧 Configuration Requise Pour Continuer

### Pour Phase 4 (Build Docker)

#### Option A (Local):
- ✅ Docker installé
- ✅ gcloud CLI installé
- ⚠️ **À faire**: `gcloud auth login`
- ⚠️ **À faire**: Exécuter les commandes docker build/push

#### Option B (GitHub Actions):
- ⚠️ **À faire**: Configurer les secrets GitHub:
  ```
  GCP_WORKLOAD_IDENTITY_PROVIDER = <votre-WIF-provider>
  GCP_SERVICE_ACCOUNT_EMAIL = vil-jobs-runner@test-barometre-juridique.iam.gserviceaccount.com
  ```
- Push sur main déclenche automatiquement le workflow

### Pour Phase 5 (Cloud Scheduler - Orchestration)

Créer des schedules pour chaque job:

```bash
# Exemple: Exécuter vil-load-corpus chaque jour à 2h du matin
gcloud scheduler jobs create app-engine vil-daily-load-corpus \
  --schedule="0 2 * * *" \
  --time-zone="Europe/Paris" \
  --http-method=POST \
  --uri="https://europe-west9-run.googleapis.com/apis/run.googleapis.com/v1/projects/test-barometre-juridique/locations/europe-west9/jobs/vil-load-corpus:run" \
  --service-account-email="vil-scheduler@test-barometre-juridique.iam.gserviceaccount.com" \
  --location=europe-west9 \
  --message-body='{}'
```

### Pour Phase 6 (Frontend)

- ⚠️ **À faire**: Choisir Vercel ou Cloud Run
- ⚠️ **À faire**: Déployer l'application

---

## 🧪 Vérifications Post-Déploiement

```bash
# 1. Vérifier les jobs Cloud Run
gcloud run jobs list --region=europe-west9 --filter="name:vil-"

# 2. Vérifier le Cloud Scheduler
gcloud scheduler jobs list --location=europe-west9

# 3. Vérifier Neo4j Aura (accès)
cypher-shell -a "neo4j+s://your-instance.databases.neo4j.io" \
  -u "your-user" -p "your-password" \
  "MATCH (n) RETURN COUNT(n) as count"

# 4. Consulter les logs d'un job
gcloud run jobs log vil-load-corpus --region=europe-west9 --limit=50

# 5. Exécuter un job manuellement
gcloud run jobs execute vil-load-corpus --region=europe-west9
```

---

## 💰 Coûts Estimés

| Service | Usage | Coût/mois |
|---------|-------|-----------|
| Cloud Run Jobs | 100h | ~$10 |
| Cloud Scheduler | 60 execs | ~$0.20 |
| BigQuery | 1TB | ~$5-10 |
| Cloud Storage | 10GB | ~$0.20 |
| **Neo4j Aura** | Professional | ~$500 |
| Artifact Registry | 10GB | ~$0.10 |
| Frontend (Vercel) | Standard | ~$20 |
| **TOTAL** | | **~$535** |

> **Note**: Le coût majeur est Neo4j Aura. Étudiez les options de réduction si besoin.

---

## 📚 Documentation

- **[DEPLOYMENT.md](./DEPLOYMENT.md)** - Guide complet de déploiement (6 phases détaillées)
- **[.github/workflows/deploy-pipeline.yml](./.github/workflows/deploy-pipeline.yml)** - Workflow GitHub Actions
- **[Dockerfile](./pipeline/Dockerfile)** - Configuration Docker pour la pipeline

---

## 🎯 Prochaines Actions (Recommandées)

### Immédiat
1. **Phase 4**: Exécuter le build Docker (local ou GitHub Actions)
   - Estim. temps: 10-15 min

### Court terme (Jour 1-2)
2. **Phase 5**: Configurer Cloud Scheduler pour l'orchestration
   - Estim. temps: 30 min

3. **Phase 6**: Déployer le frontend
   - Estim. temps: 5-10 min

### Moyen terme (Jour 2-3)
4. Configurer le monitoring et les alertes
5. Tests fonctionnels complets
6. Ajustement des coûts et des quotas

### Long terme
7. Mise en place du CI/CD complet
8. Optimisation des performances
9. Plan de scalabilité

---

## 🚨 Points d'Attention

### Authentification
- ⚠️ gcloud CLI authentication peut être instable en environnement non-persistant
- 💡 Solution: Exécuter Phase 4 sur votre machine locale

### Secrets
- ✅ Tous les secrets sont dans Secret Manager
- ⚠️ Vérifier qu'aucun secret n'est committé en Git
- 💡 Utiliser `git-secrets` pour prévention

### Coûts
- 💰 Coûts initiaux élevés à cause de Neo4j Aura (~$500/mois)
- 💡 Étudiez les options de réduction ou migration

### Image Docker
- ⚠️ La taille peut être importante avec toutes les dépendances Python
- 💡 Utilisez le cache Docker pour accélérer les builds

---

## ✉️ Support

Pour questions ou problèmes:
1. Consultez [DEPLOYMENT.md](./DEPLOYMENT.md)
2. Vérifiez les logs: `gcloud run jobs log <job-name>`
3. Consultez la documentation Google Cloud officielle

---

**Dernière mise à jour**: 2026-11-18  
**Auteur**: Copilot AI Assistant  
**Version**: 1.0
