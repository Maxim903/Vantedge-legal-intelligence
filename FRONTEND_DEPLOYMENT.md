# 🚀 Guide de Déploiement du Frontend - Vantedge Legal Intelligence

## Vue d'ensemble

Le frontend de Vantedge Legal Intelligence est une application **Next.js 16** déployée sur **Google Cloud Run**.

### Architecture

```
GitHub Repository
    ↓
  Push to main branch
    ↓
GitHub Actions Workflow (deploy-frontend.yml)
    ↓
1. Build Docker image
2. Push to Artifact Registry
3. Deploy to Cloud Run
    ↓
Production URL
```

---

## 📋 Prérequis

### Pour le déploiement automatique (GitHub Actions)

✅ Déjà configurés:
- Workload Identity Pool (GitHub OIDC)
- Service Account avec les rôles nécessaires
- Secrets GitHub configurés

Secrets requise dans GitHub:
- `GCP_PROJECT_ID` = `test-barometre-juridique`
- `GCP_WORKLOAD_IDENTITY_PROVIDER` = `projects/31886648583/locations/global/workloadIdentityPools/github-action/providers/github-provider`
- `GCP_SERVICE_ACCOUNT` = `github-actions@test-barometre-juridique.iam.gserviceaccount.com`

Variables de dépôt GitHub requises pour compiler le client Supabase:

- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- `STRIPE_PRICE_PRO`

Ne pas utiliser la clé Supabase `service_role` comme variable `NEXT_PUBLIC_*`.
Le dépôt Artifact Registry `vil-frontend` doit exister avant le lancement du workflow.
Le service Cloud Run référence les secrets `supabase-service-role-key`, `stripe-secret-key` et `stripe-webhook-secret`.

### Pour déploiement manuel

```bash
# Installer gcloud CLI
curl https://sdk.cloud.google.com | bash
exec -l $SHELL

# Configurer gcloud
gcloud auth login
gcloud config set project test-barometre-juridique

# Installer Docker
# macOS: brew install docker-desktop
# Linux: sudo apt-get install docker.io
```

---

## 🏗️ Structure du Projet Frontend

```
apps/web/
├── src/
│   ├── app/              # Next.js App Router
│   ├── components/       # React components
│   ├── lib/             # Utilities & helpers
│   └── styles/          # Tailwind CSS
├── public/              # Static assets
├── Dockerfile           # Docker image definition
├── .dockerignore        # Files to exclude from Docker build
├── next.config.ts       # Next.js configuration
├── package.json         # Dependencies
├── tsconfig.json        # TypeScript configuration
└── ...
```

---

## 🚀 Déploiement Automatique (GitHub Actions)

### Workflow

Le workflow `deploy-frontend.yml` s'exécute automatiquement quand:

1. **Un commit est poussé sur `main`** avec des changements dans `apps/web/`
2. **Ou manuellement** via le bouton "Run workflow" sur GitHub

### Étapes du workflow

1. ✅ **Checkout** - Récupère le code
2. 🔐 **Auth GCP** - Authentification via OIDC
3. 🏗️ **Build** - Construit l'image Docker
4. 📤 **Push** - Upload vers Artifact Registry
5. 🚀 **Deploy** - Déploie sur Cloud Run
6. ✅ **Verify** - Teste l'accès au service

### Pour déclencher manuellement

1. Allez sur [GitHub Actions](https://github.com/Maxim903/Vantedge-legal-intelligence/actions)
2. Sélectionnez `Deploy Frontend to Cloud Run`
3. Cliquez `Run workflow` → Branch: `main`

---

## 📦 Déploiement Manuel

### 1️⃣ Build l'image Docker

```bash
cd /workspaces/Vantedge-legal-intelligence

docker build \
  -f apps/web/Dockerfile \
  -t europe-west9-docker.pkg.dev/test-barometre-juridique/vil-frontend/vil-web:latest \
  .
```

### 2️⃣ Authentifier Docker

```bash
gcloud auth configure-docker europe-west9-docker.pkg.dev
```

### 3️⃣ Push vers Artifact Registry

```bash
docker push europe-west9-docker.pkg.dev/test-barometre-juridique/vil-frontend/vil-web:latest
```

### 4️⃣ Déployer sur Cloud Run

```bash
gcloud run deploy vil-web \
  --image=europe-west9-docker.pkg.dev/test-barometre-juridique/vil-frontend/vil-web:latest \
  --region=europe-west9 \
  --project=test-barometre-juridique \
  --platform=managed \
  --allow-unauthenticated \
  --port=3000 \
  --memory=1Gi \
  --cpu=2 \
  --timeout=3600 \
  --max-instances=10 \
  --min-instances=1 \
  --set-env-vars="NODE_ENV=production"
```

### 5️⃣ Obtenir l'URL du service

```bash
gcloud run services describe vil-web \
  --region=europe-west9 \
  --project=test-barometre-juridique \
  --format="value(status.url)"
```

---

## 🔧 Configuration du Frontend

### Variables d'environnement

Les variables d'environnement doivent être **publiques** (préfixe `NEXT_PUBLIC_`) pour être accessibles côté client.

#### Pour Cloud Run

Fichier: `apps/web/.env.cloud.example`

```bash
# Supabase (Auth & Realtime)
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key

# Backends
NEXT_PUBLIC_API_URL=https://your-cloud-run-job.region-run.googleapis.com
NEXT_PUBLIC_BACKEND_URL=https://your-backend-service.region-run.googleapis.com
```

#### Mettre à jour les env vars

```bash
gcloud run services update vil-web \
  --region=europe-west9 \
  --update-env-vars="NEXT_PUBLIC_API_URL=https://your-url.com"
```

---

## 🐳 Docker Image Details

### Base Image
- **Builder**: `node:20-alpine` (slim, optimisé)
- **Runtime**: `node:20-alpine` (security optimized)

### Optimisations

✅ **Multi-stage build** - Réduit la taille de l'image
✅ **Non-root user** - Security best practice
✅ **Health check** - Détecte les défaillances
✅ **dumb-init** - Gère les signaux correctement
✅ **Alpine Linux** - Petit et efficace

### Taille estimée

- Builder stage: ~1.2GB (images temporaires, non conservées)
- Runtime image: ~300-400MB
- Après compression: ~100-150MB

---

## 📊 Cloud Run Configuration

| Paramètre | Valeur | Description |
|-----------|--------|-------------|
| **Service Name** | `vil-web` | Identifiant du service |
| **Region** | `europe-west9` | Bruxelles (proche des données) |
| **Memory** | 1Gi | Mémoire allouée |
| **CPU** | 2 | Nombre de CPUs |
| **Timeout** | 3600s | 1 heure (long requests) |
| **Min Instances** | 1 | Au moins 1 instance toujours active |
| **Max Instances** | 10 | Maximum 10 instances pour scaling |
| **Allow Unauthenticated** | ✅ | Public (sans auth requise) |

---

## 🔍 Monitoring & Logs

### Voir les logs en temps réel

```bash
# Derniers 50 logs
gcloud run logs read vil-web --region=europe-west9 --limit=50

# Logs en continu
gcloud run logs read vil-web --region=europe-west9 --follow
```

### Accéder aux métriques

1. Console: https://console.cloud.google.com/run/detail/europe-west9/vil-web/metrics
2. Ou via CLI:

```bash
gcloud monitoring dashboards list --project=test-barometre-juridique
```

### Cloud Logging

https://console.cloud.google.com/logs?resource=cloud_run_revision&service=vil-web

---

## ✅ Post-Déploiement

### 1️⃣ Vérifier que le service est actif

```bash
# Vérifier l'état
gcloud run services describe vil-web --region=europe-west9

# Tester l'accès
curl https://vil-web-xxx.region-run.app/
```

### 2️⃣ Vérifier les logs

```bash
gcloud run logs read vil-web --limit=20
```

### 3️⃣ Mettre à jour les secrets GitHub

Si la URL a changé, mettez à jour dans GitHub:
```
Settings → Secrets and variables → Actions
```

### 4️⃣ Configurer le domaine personnalisé (optionnel)

```bash
gcloud run domain-mappings create \
  --service=vil-web \
  --domain=vil.example.com \
  --region=europe-west9
```

---

## 🚨 Troubleshooting

| Problème | Cause | Solution |
|----------|-------|----------|
| **Service non disponible** | Build échoué | `gcloud run logs read vil-web --limit=50` |
| **502 Bad Gateway** | Erreur application | Vérifier les logs pour les stacktraces |
| **Health check failed** | Endpoint `/health` manquant | Ajouter une route `/health` ou `/` |
| **Out of memory** | Trop peu de RAM | `gcloud run services update vil-web --memory=2Gi` |
| **Timeout** | Requête trop longue | Augmenter `--timeout` ou optimiser le code |

---

## 🔄 Mise à Jour du Service

### Après un commit sur `main`

✅ Automatique via GitHub Actions (quelques minutes)

### Mise à jour manuelle

```bash
# Après pushing une nouvelle image
gcloud run deploy vil-web \
  --image=europe-west9-docker.pkg.dev/test-barometre-juridique/vil-frontend/vil-web:latest \
  --region=europe-west9
```

### Rollback à une version antérieure

```bash
# Lister les images
gcloud artifacts docker images list europe-west9-docker.pkg.dev/test-barometre-juridique/vil-frontend/vil-web

# Déployer une version spécifique
gcloud run deploy vil-web \
  --image=europe-west9-docker.pkg.dev/test-barometre-juridique/vil-frontend/vil-web:COMMIT_SHA \
  --region=europe-west9
```

---

## 📈 Coûts Estimés

| Ressource | Usage | Coût/mois |
|-----------|-------|-----------|
| **Cloud Run** | 1GB mem × 1-10 instances | $5-50 |
| **Artifact Registry** | ~200MB × 20 images | $0.10 |
| **Cloud Logging** | ~10GB logs/mois | $0.50 |
| **Networking** | Egress data | Variable |
| **Total** | | **~$10-60** |

*Note: Les 2 premiers mois sont gratuits avec le crédit de démarrage GCP*

---

## 🔐 Sécurité

✅ **Bonnes pratiques appliquées:**
- Non-root user dans le container
- HTTPS obligatoire (enforced par Cloud Run)
- Secrets dans Secret Manager (pas en dur)
- Authentification OIDC pour GitHub Actions
- Logs centralisés et auditables
- VPC Security Command Center (optionnel)

---

## 📚 Ressources

- [Next.js Documentation](https://nextjs.org/docs)
- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [Node.js Alpine Considerations](https://github.com/nodejs/docker-node)

---

## 🤝 Support

Pour des questions:
1. Vérifiez les logs: `gcloud run logs read vil-web --limit=100`
2. Consultez le [Cloud Run Troubleshooting Guide](https://cloud.google.com/run/docs/troubleshooting)
3. Ouvrez une issue GitHub
