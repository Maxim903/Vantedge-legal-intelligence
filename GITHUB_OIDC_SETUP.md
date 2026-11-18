# 🔐 GitHub OIDC - Configuration Complétée

**Date** : 2026-11-18  
**Projet GCP** : `test-barometre-juridique` (ID: 31886648583)  
**Repository** : `Maxim903/Vantedge-legal-intelligence`

## ✅ Ressources Créées

| Ressource | Détail |
|-----------|--------|
| **Workload Identity Pool** | `github-action` |
| **OIDC Provider** | `github-provider` |
| **Service Account** | `github-actions@test-barometre-juridique.iam.gserviceaccount.com` |
| **Resource Name** | `projects/31886648583/locations/global/workloadIdentityPools/github-action` |
| **Provider URI** | `projects/31886648583/locations/global/workloadIdentityPools/github-action/providers/github-provider` |

## 🔒 Secrets GitHub à Configurer

### Étape 1 : Accès à GitHub

Allez sur https://github.com/Maxim903/Vantedge-legal-intelligence/settings/secrets/actions

### Étape 2 : Créer les 3 secrets

Cliquez sur **"New repository secret"** pour chaque entrée :

```
Nom: GCP_PROJECT_ID
Valeur: test-barometre-juridique

---

Nom: GCP_WORKLOAD_IDENTITY_PROVIDER
Valeur: projects/31886648583/locations/global/workloadIdentityPools/github-action/providers/github-provider

---

Nom: GCP_SERVICE_ACCOUNT
Valeur: github-actions@test-barometre-juridique.iam.gserviceaccount.com
```

## 🛠️ Rôles IAM Configurés

Le service account `github-actions` a les permissions suivantes :

- ✅ `roles/iam.workloadIdentityUser` → Peut s'authentifier via OIDC
- ✅ `roles/artifactregistry.writer` → Push vers Artifact Registry
- ✅ `roles/run.developer` → Déployer sur Cloud Run
- ✅ `roles/secretmanager.secretAccessor` → Accéder aux secrets

## 🚀 Workflow GitHub Actions

Le workflow `.github/workflows/deploy-pipeline.yml` fait :

1. **Build** : Construit l'image Docker quand on pousse sur `main`
2. **Push** : Envoie l'image vers Artifact Registry
3. **Deploy** : Mets à jour les Cloud Run Jobs avec la nouvelle image
4. **Verify** : Liste les jobs déployés

### Déclencheurs

- 🔄 Push sur `main` avec changements dans `pipeline/**`
- 🔄 Pull Request sur `main`
- ⚙️ Workflow dispatch (manuel)

## 📋 Vérification

Pour tester que tout fonctionne :

```bash
# 1. Vérifier le provider OIDC
gcloud iam workload-identity-pools providers list \
  --location=global \
  --workload-identity-pool=github-action \
  --project=test-barometre-juridique

# 2. Vérifier le service account
gcloud iam service-accounts describe \
  github-actions@test-barometre-juridique.iam.gserviceaccount.com \
  --project=test-barometre-juridique

# 3. Vérifier les permissions
gcloud projects get-iam-policy test-barometre-juridique \
  --flatten="bindings[].members" \
  --filter="bindings.members:github-actions@*"

# 4. Vérifier les images Artifact Registry
gcloud artifacts docker images list \
  europe-west9-docker.pkg.dev/test-barometre-juridique/vil-pipeline
```

## 🔗 Ressources Utiles

- [Google GitHub Actions Auth](https://github.com/google-github-actions/auth)
- [Workload Identity Federation Docs](https://cloud.google.com/iam/docs/workload-identity-federation)
- [Cloud Run Jobs](https://cloud.google.com/run/docs/quickstarts/jobs/create-execute-jobs)
- [Artifact Registry](https://cloud.google.com/artifact-registry/docs)

## 🎯 Prochaines Étapes

1. ✅ Ajouter les 3 secrets dans GitHub (voir section "Secrets GitHub à Configurer")
2. ⏳ Faire un push sur `main` pour déclencher le workflow
3. 👀 Vérifier que l'image est bien pushée dans Artifact Registry
4. 🔍 Vérifier les logs du workflow dans GitHub
5. 🚀 Les Cloud Run Jobs seront mis à jour automatiquement

---

**Configuration complétée par** : Copilot  
**Dernière mise à jour** : 2026-11-18
