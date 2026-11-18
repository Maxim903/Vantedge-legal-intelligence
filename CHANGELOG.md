# Changelog

Les changements notables du projet sont documentés ici selon
[Keep a Changelog](https://keepachangelog.com/fr/1.1.0/).

## [Unreleased]

### Added

- Inscription, connexion et réinitialisation du mot de passe avec Supabase.
- Espace compte, projets et historique des analyses, avec politiques RLS.
- Abonnement Stripe en mode test : Checkout, portail et traitement des webhooks
  signés.
- Ouverture d'analyse associée à un projet, avec contrôle et consommation
  atomique du quota ; réouverture sans nouvelle consommation.
- Tableau des notions et scores d'écart : tri, filtre par situation de vie,
  pagination et définitions des indices.
- Détail d'une notion : articles, requêtes, métriques, intentions et résultats
  SERP disponibles, ainsi que notions liées et graphique avec repli en liste.
- Ingestion du corpus LEGI, extraction des notions et collecte des données de
  marché, avec suivi des coûts et des exécutions.
- Modèles dbt des données juridiques et de marché, scores d'écart et contrôles
  de qualité et de fraîcheur.
- Export et synchronisation des données vers Neo4j, requêtes de graphe et
  contrôle de cohérence avec BigQuery.
- Tests du pipeline, de l'application, des politiques RLS et de l'accessibilité,
  ainsi qu'un parcours de bout en bout avec services de test.
- Configuration de l'image du pipeline, publication Artifact Registry et script
  de déploiement des jobs Cloud Run et de leurs déclencheurs.
- Documentation du périmètre, de la sécurité, des environnements, de l'exploitation
  et de la [recette MVP](docs/01-specification/recette-mvp.md).

La recette et la mise en production restent à valider. Le MVP vise le Livre I
du Code du travail et le marché France/fr ; les scores actuels portent sur le
code entier, et les notions liées peuvent concerner d'autres codes. La
facturation réelle est hors périmètre MVP.
