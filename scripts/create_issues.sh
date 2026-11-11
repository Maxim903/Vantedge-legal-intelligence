#!/usr/bin/env bash

set -euo pipefail

command -v gh >/dev/null 2>&1 || {
  printf 'Erreur : gh doit être installé.\n' >&2
  exit 1
}

gh auth status >/dev/null

titles=(
  "Phase 0 – Cadrage"
  "Phase 1 – Fondations"
  "Phase 2 – Tranche verticale"
  "Phase 3 – Ingestion et IA"
  "Phase 4 – Neo4j"
  "Phase 5 – Tableau de bord complet"
)

bodies=(
  "- [ ] Définir et figer le périmètre MVP et l'ontologie.
- [ ] Définir le score d'écart v1.
- [ ] Valider la conformité, le budget et le choix des fournisseurs.
- [ ] Préparer le registre RGPD initial.
- [ ] Faire valider le document d'ontologie."
  "- [ ] Configurer BigQuery : datasets raw, staging, marts et ops.
- [ ] Mettre en place Supabase Auth et les politiques RLS.
- [ ] Configurer Stripe en mode test et le traitement des webhooks.
- [ ] Configurer les secrets, les environnements et la CI/CD.
- [ ] Vérifier le parcours d'inscription jusqu'à l'abonnement de test."
  "- [ ] Charger et versionner un livre du Code du travail.
- [ ] Réaliser la première extraction IA.
- [ ] Construire un écran de liste des notions.
- [ ] Démontrer le parcours complet de bout en bout."
  "- [ ] Préparer le jeu de test annoté et les mesures de qualité.
- [ ] Mettre en place l'enrichissement DataForSEO et l'archivage GCS.
- [ ] Alimenter staging et les 22 tables marts.
- [ ] Mesurer précision et rappel sur le jeu annoté.
- [ ] Atteindre les seuils de qualité fixés."
  "- [ ] Synchroniser Neo4j depuis les tables marts BigQuery.
- [ ] Mettre en place les requêtes d'analyse de graphe et de centralité.
- [ ] Calculer et versionner le score v1.
- [ ] Vérifier la cohérence des écarts sur un échantillon relu."
  "- [ ] Compléter les widgets et les parcours du tableau de bord.
- [ ] Mettre en place les quotas et le monitoring.
- [ ] Préparer l'application, les alertes et la documentation.
- [ ] Réaliser la recette et valider la mise en production."
)

existing_titles=$(gh api --paginate \
  'repos/{owner}/{repo}/issues?state=all&per_page=100' \
  --jq '.[] | select(.pull_request == null) | .title')

for index in "${!titles[@]}"; do
  title=${titles[$index]}

  if grep -Fqx -- "$title" <<< "$existing_titles"; then
    printf 'Issue déjà présente, ignorée : %s\n' "$title"
    continue
  fi

  gh issue create --title "$title" --body "${bodies[$index]}"
  existing_titles+=$'\n'"$title"
done