# Vintage Legal Intelligence

## Dossier de spécification et d'architecture

Version 2.0 – révisée et corrigée  
Du corpus juridique à l'analyse de marché : architecture, données, IA, graphe, SaaS  
11 novembre 2026 – Document de travail (MVP)

> Vintage Legal Intelligence – Dossier de spécification et d'architecture v2.0 Page 2

## Sommaire

| N° | Chapitre |
|---|---|
| 0 | Synthèse et corrections apportées |
| 1 | Vision, périmètre et positionnement |
| 2 | Principes d'architecture |
| 3 | Stack technique |
| 4 | Sources de données et gestion des versions |
| 5 | Pipeline d'ingestion et d'enrichissement |
| 6 | Modèle de données BigQuery |
| 7 | Graphe de connaissances Neo4j |
| 8 | Score d'écart et criticité sémantique |
| 9 | Architecture applicative et sécurité |
| 10 | Interface utilisateur |
| 11 | Qualité de l'IA et évaluation |
| 12 | Orchestration, observabilité et coûts |
| 13 | Conformité : RGPD et cadre juridique |
| 14 | Feuille de route du MVP |
| 15 | Risques et mesures |
| 16 | Décisions ouvertes |
| A | Annexe A – Les 22 tables du schéma en flocon |
| B | Annexe B – Contraintes et requêtes Neo4j |
| C | Annexe C – Glossaire |

> Vintage Legal Intelligence – Dossier de spécification et d'architecture v2.0 Page 3

## 0. Synthèse et corrections apportées

Cette version 2.0 reprend le dossier initial et corrige les erreurs de fond, les incohérences de modélisation et de pipeline, puis comble les manques nécessaires à un MVP réaliste. Les points marqués [À valider] sont des propositions de conception qui nécessitent une décision de votre part (voir chapitre 16).

### 0.1 Corrections de fond

| # | Version initiale | Problème | Correction apportée |
|---|---|---|---|
| 1 | « authentification (RLS) » | RLS (Row Level Security) est un mécanisme d'autorisation et d'isolation des données, pas d'authentification. | Supabase Auth pour l'authentification ; RLS pour l'isolation des données par utilisateur. |
| 2 | « abonnements SaaS » gérés par Supabase | Supabase ne gère pas la facturation. | Ajout de Stripe, synchronisé avec Supabase par webhooks. |
| 3 | « Entité juridique » | En droit français, désigne une personne morale (SAS, association…). Ambigu avec des concepts de droit. | Renommé « Notion juridique » (nœud :Notion). |
| 4 | BigQuery représenté comme un nœud du graphe | Une base de données n'est pas un nœud sémantique. | Nœuds :Article dans Neo4j, avec identifiant Légifrance (LEGIARTI…) pointant vers BigQuery. |
| 5 | Relations : EST_EXPRIME_PAR, GENERE_INTENTION, A_POUR_VOLUME | Nommage incohérent (passif/actif), accord fautif (« entité » est féminin), accents. | Convention unique, sans accents : SE_FONDE_SUR, EST_EXPRIMEE_PAR, A_POUR_INTENTION, A_POUR_METRIQUE. |
| 6 | Volume, CPC et intention rattachés à l'entité | Ce sont des attributs de la requête, variables dans le temps, par pays et par langue. | Notion → Requête → Intention / Métrique mensuelle / Résultat SERP. |
| 7 | Widgets « SUPABASE (OLTP) » / « NEO4J (ANALYTIQUE) » | Noms de technologies, pas de fonctions ; Neo4j n'est pas l'entrepôt analytique (c'est BigQuery). | « Mon compte et projets » / « Analyse loi vs marché ». |
| 8 | « Historique des sessions » | Confusion avec les sessions d'authentification. | « Historique des recherches et analyses ». |
| 9 | « schéma en flocon à 22 tables » non détaillé ; corpus brut et tables analytiques mélangés | Composant flou, non vérifiable. | Datasets raw / staging / marts séparés ; liste des 22 tables en annexe A. |

### 0.2 Incohérences de pipeline corrigées

- Sortie de l'agent IA non persistée : ajout d'une table entites_extraites (modèle, version du prompt, date, score de confiance) pour rejouer, auditer et corriger.
- Double alimentation divergente (Neo4j et BigQuery lisant le même JSON) : Neo4j est désormais alimenté depuis les tables BigQuery curées (source de vérité unique).
- Ordre des phases inversé : l'ontologie est figée avant l'extraction (phase 0).
- « ELT » : remplacé par « pipeline d'ingestion et d'enrichissement », plus exact (une étape d'IA précède le chargement).
- Couche API absente : ajout d'une couche serveur ; les identifiants Neo4j ne sont jamais exposés au navigateur.

> Vintage Legal Intelligence – Dossier de spécification et d'architecture v2.0 Page 4

## 1. Vision, périmètre et positionnement

Vintage Legal Intelligence est un SaaS d'analyse qui confronte la norme juridique (articles de loi) à l'expression empirique du marché (requêtes web, volumes, intentions, résultats de recherche). Il permet d'identifier les notions juridiques fortement recherchées, mal couvertes, ou sémantiquement critiques, afin d'orienter une stratégie de contenu et d'acquisition.

### 1.1 Proposition de valeur

- Cartographier les notions juridiques d'un code et les situations de vie associées.
- Mesurer la demande réelle (volume, CPC, concurrence, intention) par notion.
- Révéler les écarts entre ce que dit la loi et ce que cherchent les gens (analyse d'écart).

### 1.2 Périmètre du MVP

| Inclus | Exclus (hors MVP) |
|---|---|
| Un seul code : Code du travail, limité à un livre (ex. Livre I) | Code civil et autres codes |
| France, langue française (fr) | Autres pays et langues |
| Extraction IA, enrichissement DataForSEO, score d'écart v1 | Recommandations de contenu générées automatiquement |
| Tableau de bord, comptes, abonnement, quotas | API publique, export massif, marque blanche |

### 1.3 Positionnement juridique

Important. Le produit fournit une analyse de marché et de données, et non une consultation juridique. En France, la consultation juridique à titre professionnel est encadrée (loi n° 71-1130 du 31 décembre 1971). L'interface, les CGU et les exports doivent porter une mention claire : « Cet outil ne fournit aucun conseil juridique. »

> Vintage Legal Intelligence – Dossier de spécification et d'architecture v2.0 Page 5

## 2. Principes d'architecture

- Persistance polyglotte, responsabilités distinctes : OLTP (Supabase), entrepôt analytique (BigQuery), graphe (Neo4j), stockage d'objets (GCS).
- Source de vérité unique : BigQuery (tables curées). Neo4j et l'interface en sont des projections.
- Immuabilité du brut : les payloads DataForSEO sont archivés tels quels dans GCS, jamais modifiés.
- Reproductibilité : chaque sortie d'IA est rattachée à un modèle, une version de prompt et une date.
- Idempotence : un même appel (mot-clé + localisation + langue + date) n'est jamais payé deux fois.
- Moindre privilège : comptes de service dédiés par composant, secrets dans un gestionnaire de secrets.
- Données UE : toutes les ressources dans une région européenne.
- Progressivité : tranche verticale minimale d'abord, élargissement ensuite.

## 3. Stack technique

| Composant | Technologie | Rôle |
|---|---|---|
| Front-end | Next.js, React, Tailwind CSS | Interface, tableaux de bord, navigation dans les notions. |
| Authentification et OLTP | Supabase (PostgreSQL, Supabase Auth, RLS) | Comptes, projets, quotas, historique des analyses ; isolation par utilisateur via RLS. |
| Facturation | Stripe (Checkout, Customer Portal, webhooks) | Abonnements et paiements ; état synchronisé dans Supabase. |
| Entrepôt analytique | Google BigQuery (région europe-west9) | Corpus juridique versionné, extractions IA, données de marché, tables analytiques (datasets raw, staging, marts). |
| Stockage d'objets | Google Cloud Storage (région UE) | Landing zone des payloads JSON bruts DataForSEO (immuables). |
| Graphe de connaissances | Neo4j (AuraDB, région UE) [À valider] | Relations notion / article / requête, analyses de graphe. Alimenté depuis BigQuery. |
| Couche API serveur | Routes serveur Next.js ou service Cloud Run | Seul point d'accès à Neo4j et BigQuery depuis l'application ; contrôle des quotas. |
| Orchestration | Cloud Run Jobs + Cloud Scheduler (MVP) [À valider] | Exécution des lots, reprises sur erreur ; Airflow/Prefect si la complexité l'exige. |
| IA | Fournisseur LLM à choisir [À valider] | Extraction de notions et situations de vie, sortie JSON validée par schéma. |
| Secrets et sécurité | Secret Manager, IAM, comptes de service | Aucune clé en clair ; droits minimaux. |

> Vintage Legal Intelligence – Dossier de spécification et d'architecture v2.0 Page 6

## 4. Sources de données et gestion des versions

### 4.1 Corpus juridique

Le corpus doit provenir d'une source officielle citée explicitement : API Légifrance (PISTE), base LEGI de la DILA (jeux de données diffusés notamment sur data.gouv.fr). Les textes sont réutilisables sous Licence Ouverte (Etalab) ; vérifier les conditions exactes avant mise en production.

| Code | Identifiant Légifrance (LEGITEXT) |
|---|---|
| Code du travail | LEGITEXT000006072050 |
| Code civil | LEGITEXT000006070721 |

Chaque article est identifié par un identifiant stable de type LEGIARTI… ; c'est la clé qui relie BigQuery et Neo4j.

### 4.2 Versionnement des articles

Un article de loi évolue : en vigueur, modifié, abrogé. Sans gestion de versions, la « norme » analysée devient fausse. Le modèle impose donc :

- une table article_version avec date_debut, date_fin, etat (VIGUEUR, MODIFIE, ABROGE) ;
- une extraction IA rattachée à une version d'article, jamais à l'article seul ;
- un rafraîchissement périodique du corpus, avec détection des changements et ré-extraction ciblée.

### 4.3 Données de marché (DataForSEO)

| Élément | Spécification |
|---|---|
| Cible | France (code de localisation DataForSEO 2250, à vérifier), langue fr |
| Volumes, CPC, concurrence | API Keywords Data (endpoint exact à confirmer selon le plan tarifaire) |
| Intentions de recherche | API Labs (search intent) ou classification interne [À valider] |
| Résultats de recherche | API SERP, profondeur limitée (ex. top 10) pour maîtriser les coûts |
| Clé d'idempotence | hash(mot-clé + localisation + langue + endpoint + période) |
| Cache | Une requête déjà archivée dans GCS n'est pas rejouée avant expiration (ex. 30 jours pour les volumes) |
| Rafraîchissement | Mensuel pour les volumes ; à la demande pour la SERP [À valider] |

> Vintage Legal Intelligence – Dossier de spécification et d'architecture v2.0 Page 7

## 5. Pipeline d'ingestion et d'enrichissement

Le flux ci-dessous remplace l'ancien « ELT ». Chaque étape écrit son résultat dans un stockage persistant, ce qui permet de rejouer le pipeline à partir de n'importe quel point.

1. BigQuery raw : corpus juridique versionné Code du travail (MVP) ; Code civil ensuite
2. Extraction par lots Sélection des articles en vigueur non encore traités
3. Agent IA d'analyse sémantique Sortie JSON validée par schéma : notions, situations de vie, score de confiance
4. BigQuery : entites_extraites (+ validation humaine) Modèle, version du prompt, date, article_version_id
5. API DataForSEO Volumes, CPC, intentions, SERP (avec cache et clé d'idempotence)
6. GCS : payloads JSON bruts immuables Chemin partitionné par date et clé d'idempotence
7. BigQuery staging puis marts (22 tables) Parsing, dédoublonnage, historisation mensuelle
8. Synchronisation par lots vers Neo4j Projection du graphe depuis les tables marts
9. API serveur puis Next.js Accès contrôlé, quotas, journalisation

### Règles de fonctionnement

- Un lot échoué est repris sans doublon (idempotence) ; les erreurs sont tracées dans une table pipeline_runs.
- Le JSON du LLM est refusé s'il ne respecte pas le schéma ; il est alors relancé ou mis en file de revue.
- Aucune écriture dans Neo4j sans passage préalable par BigQuery.

> Vintage Legal Intelligence – Dossier de spécification et d'architecture v2.0 Page 8

## 6. Modèle de données BigQuery

| Dataset | Contenu | Règles |
|---|---|---|
| raw | Corpus juridique brut versionné ; copie des payloads chargés depuis GCS | Aucune transformation ; append-only. |
| staging | Données nettoyées : JSON aplati, types corrects, dédoublonnage | Reconstructible depuis raw. |
| marts | Schéma en flocon (22 tables, annexe A) : dimensions, faits, ponts | Source de vérité pour l'application et Neo4j. |
| ops | Journal du pipeline, coûts, évaluations de qualité | Suivi et audit. |

### 6.1 Table entites_extraites (extrait)

```text
entites_extraites
 extraction_id STRING (cle)
 article_version_id STRING (LEGIARTI + version)
 notion_libelle STRING
 situation_de_vie STRING
 score_confiance FLOAT64 (0 a 1)
 modele_llm STRING
 version_prompt STRING
 extrait_le TIMESTAMP
 statut_validation STRING (AUTO | A_REVOIR | VALIDE | REJETE)
 valide_par STRING
```

### 6.2 Table métrique mensuelle (extrait)

```text
fait_metrique_mensuelle
 requete_id STRING
 mois DATE
 pays STRING (FR)
 langue STRING (fr)
 volume INT64
 cpc FLOAT64
 concurrence FLOAT64
 source_payload STRING (chemin GCS)
```

Le volume est stocké par mois, par pays et par langue : il n'est jamais un attribut figé de la notion.

> Vintage Legal Intelligence – Dossier de spécification et d'architecture v2.0 Page 9

## 7. Graphe de connaissances Neo4j

Le nœud pivot est la Notion juridique. Elle se fonde sur des articles (norme) et s'exprime par des requêtes web (marché). Les métriques et intentions sont portées par la Requête, non par la notion.

```text
SE_FONDE_SUR APPARTIENT_A
EST_EXPRIMEE_PAR
A_POUR_INTENTION A_POUR_METRIQUE A_POUR_RESULTAT
Article SituationDeVie
Notion
Requete
Intention Metrique ResultatSERP
```

### 7.1 Nœuds

| Nœud | Propriétés principales | Clé d'unicité |
|---|---|---|
| Code, Livre, Titre | libelle, ordre | identifiant Légifrance |
| Article | numero, etat, date_debut, date_fin, texte_ref (pointeur BigQuery) | article_id (LEGIARTI…) |
| Notion | libelle, definition_courte, score_confiance | notion_id |
| SituationDeVie | libelle | situation_id |
| Requete | texte, langue, pays | requete_id (hash) |
| Intention | type (informationnelle, transactionnelle, navigationnelle, commerciale) | type |
| Metrique | mois, volume, cpc, concurrence | requete_id + mois |
| ResultatSERP | domaine, url, position, date | requete_id + date + position |

### 7.2 Relations (convention : MAJUSCULES, sans accents, accord correct)

| Relation | Sens |
|---|---|
| (:Notion)-[:SE_FONDE_SUR]->(:Article) | La notion trouve son fondement dans l'article. |
| (:Notion)-[:APPARTIENT_A]->(:SituationDeVie) | Rattachement à une situation de vie. |
| (:Notion)-[:EST_EXPRIMEE_PAR {score}]->(:Requete) | La requête exprime la notion (score de rattachement). |
| (:Requete)-[:A_POUR_INTENTION]->(:Intention) | Intention de recherche dominante. |
| (:Requete)-[:A_POUR_METRIQUE]->(:Metrique) | Une métrique par mois. |
| (:Requete)-[:A_POUR_RESULTAT]->(:ResultatSERP) | Résultats observés dans la SERP. |

| Relation | Sens |
|---|---|
| (:Article)-[:RENVOIE_A \| MODIFIE \| ABROGE]->(:Article) | Liens normatifs entre articles. |
| (:Code)-[:CONTIENT]->(:Livre)-[:CONTIENT]->(:Titre)-[:CONTIENT]->(:Article) | Hiérarchie du code. |

Le graphe est global et en lecture seule pour les utilisateurs. Les projets et données des utilisateurs restent dans Supabase ; aucune donnée personnelle n'entre dans Neo4j.

> Vintage Legal Intelligence – Dossier de spécification et d'architecture v2.0 Page 10

## 8. Score d'écart et criticité sémantique

L'analyse d'écart (« Gap Analysis ») est la valeur centrale du produit. Elle n'était pas spécifiée ; voici une définition de départ [À valider et à calibrer]. Tous les indices sont normalisés de 0 à 100 (rang percentile au sein du périmètre analysé).

| Indice | Définition | Source |
|---|---|---|
| D – Demande | Volume mensuel moyen sur 12 mois des requêtes rattachées à la notion, pondéré par le score de rattachement. | marts : fait_metrique_mensuelle |
| S – Saturation | Niveau de concurrence (concurrence publicitaire, autorité des domaines du top 10). | Métriques + SERP |
| I – Importance normative | Poids de la notion dans la norme : nombre d'articles en vigueur, centralité dans le graphe (ex. degré, PageRank). | Neo4j / marts |
| Écart | D × (1 − S/100) : demande forte et offre faible = opportunité. | Calculé dans BigQuery |
| Criticité sémantique | Moyenne pondérée de I et de la part d'intentions transactionnelles ou commerciales. | Calculé dans BigQuery |

Gouvernance. Formules et pondérations sont versionnées (version_score) et calibrées sur un échantillon de notions relues manuellement. Tout score affiché indique sa version et sa date de calcul.

## 9. Architecture applicative et sécurité

### 9.1 Flux d'accès

```text
Navigateur --(session Supabase Auth)--> Next.js (routes serveur)
Next.js (serveur) --> Supabase : profil, projets, quotas (RLS)
Next.js (serveur) --> Neo4j : requetes de graphe (identifiants cote serveur uniquement)
Next.js (serveur) --> BigQuery : agregats analytiques (compte de service lecture seule)
Stripe --(webhook signe)--> Route serveur --> Supabase : etat de l'abonnement
```

### 9.2 Règles de sécurité

- Les identifiants Neo4j et BigQuery ne sont jamais exposés au navigateur.
- Webhooks Stripe : vérification de la signature ; traitement idempotent.
- RLS activée sur toutes les tables Supabase contenant des données utilisateur ; tests automatisés des politiques.
- Quotas vérifiés côté serveur (jamais côté client) avant tout appel coûteux.
- Comptes de service distincts : ingestion (écriture raw), application (lecture marts), synchronisation Neo4j.
- Journalisation des accès et alertes sur usage anormal.

> Vintage Legal Intelligence – Dossier de spécification et d'architecture v2.0 Page 11

## 10. Interface utilisateur

Le tableau de bord présente deux zones nommées par leur fonction et non par leur technologie.

```text
VINTAGE LEGAL INTELLIGENCE
Mon compte et projets Analyse loi vs marché
```

- Profil utilisateur
- Abonnement (géré via Stripe)
- Quotas d'analyses et crédits
- Projets sauvegardés
- Historique des recherches et analyses
- Analyse d'écart : norme vs demande du marché
- Groupes de notions et criticité sémantique
- Synthèse des intentions de recherche
- Détail d'une notion : articles, requêtes, métriques, SERP
- Mention « aucun conseil juridique »

### 10.1 Exigences d'ergonomie

- Chaque score affiche sa définition (infobulle) et sa date de calcul.
- Chaque notion renvoie à l'article source et à sa version en vigueur.
- États vides, chargements et erreurs explicites ; interface responsive.
- Accessibilité (WCAG 2.1 AA visée) : contrastes, navigation clavier, libellés.

## 11. Qualité de l'IA et évaluation

- Sortie contrainte : JSON validé par schéma ; rejet automatique des sorties invalides.
- Traçabilité : toute notion conserve l'article source, le modèle, la version du prompt.
- Jeu de test annoté à la main : 100 à 200 articles relus par un juriste ou une personne formée [À valider], pour mesurer précision et rappel.
- Seuil de confiance : en dessous du seuil, la notion passe en file de revue humaine.
- Échantillonnage continu : revue périodique d'un pourcentage des extractions validées automatiquement.
- Non-régression : tout changement de modèle ou de prompt est re-testé sur le jeu annoté avant déploiement.
- Réserve : un LLM peut halluciner sur du contenu juridique ; aucune notion non vérifiable ne doit être présentée comme certaine.

> Vintage Legal Intelligence – Dossier de spécification et d'architecture v2.0 Page 12

## 12. Orchestration, observabilité et coûts

### 12.1 Orchestration et déploiement

- Jobs conteneurisés (Cloud Run Jobs) déclenchés par Cloud Scheduler ; reprise automatique avec limite de tentatives.
- Environnements séparés : développement, préproduction, production.
- CI/CD : tests unitaires, tests de schéma, tests des politiques RLS, déploiement automatisé.
- Infrastructure décrite en code (Terraform recommandé) [À valider].

### 12.2 Observabilité

- Table ops.pipeline_runs : lot, durée, statut, erreurs, volumétrie.
- Alertes : échec de lot, dérive du taux de rejet du LLM, dépassement budgétaire.
- Tableau de bord interne de qualité des données (complétude, fraîcheur).

### 12.3 Suivi des coûts

| Poste | Levier de maîtrise |
|---|---|
| LLM | Traitement par lots, texte tronqué au nécessaire, cache par article_version_id, budget mensuel plafonné. |
| DataForSEO | Cache et idempotence, limitation de la profondeur SERP, priorisation des notions à forte criticité. |
| BigQuery | Tables partitionnées par date, clustering, limites de requêtes, vues matérialisées. |
| Neo4j | Taille d'instance adaptée ; projection limitée aux données utiles. |

> Vintage Legal Intelligence – Dossier de spécification et d'architecture v2.0 Page 13

## 13. Conformité : RGPD et cadre juridique

- Hébergement UE : BigQuery europe-west9 (Paris), GCS et Supabase en région UE, Neo4j AuraDB en région UE.
- Données personnelles limitées à Supabase (comptes, projets) ; registre des traitements, politique de confidentialité, durées de conservation.
- Droits des personnes : accès, rectification, suppression, export.
- Sous-traitants : accords de traitement (DPA) avec Supabase, Stripe, Google, Neo4j, DataForSEO et le fournisseur LLM ; vérifier les transferts hors UE.
- Contenus juridiques : respect de la Licence Ouverte (mention de la source et de la date de mise à jour).
- CGU : exclusion explicite du conseil juridique, limitation de responsabilité, conditions d'usage des données.

> Vintage Legal Intelligence – Dossier de spécification et d'architecture v2.0 Page 14

## 14. Feuille de route du MVP

L'ordre corrige l'erreur initiale : l'ontologie et le périmètre sont figés avant l'extraction IA, et Neo4j arrive après validation de la valeur de l'analyse.

| Phase | Objectifs | Livrables | Critère de sortie |
|---|---|---|---|
| 0. Cadrage | Périmètre MVP, ontologie, définition du score d'écart, conformité, budget, choix des fournisseurs. | Ontologie figée, spécification du score v1, budget, registre RGPD initial. | Document d'ontologie validé. |
| 1. Fondations | BigQuery (raw, staging, marts, ops), Supabase Auth + RLS, Stripe, secrets, CI/CD. | Environnements, schéma raw, comptes et abonnement de test. | Parcours inscription → abonnement fonctionnel. |
| 2. Tranche verticale | Un livre du Code du travail, de l'extraction à un écran simple. | Corpus versionné chargé, première extraction, écran de liste de notions. | Démonstration de bout en bout. |
| 3. Ingestion et IA | Extraction à grande échelle, évaluation, DataForSEO, GCS, staging et marts. | Jeu de test annoté, métriques de qualité, 22 tables alimentées. | Précision et rappel atteignant le seuil fixé. |
| 4. Neo4j | Synchronisation depuis BigQuery, analyses de graphe, calcul du score. | Graphe projeté, requêtes de centralité, score v1 versionné. | Écarts cohérents sur un échantillon relu. |
| 5. Tableau de bord complet | Widgets complets, quotas, monitoring, déploiement en production. | Application complète, alertes, documentation. | Recette validée, mise en production. |

## 15. Risques et mesures

| Risque | Impact | Mesure |
|---|---|---|
| Hallucinations du LLM sur le contenu juridique | Élevé | Schéma strict, référence à l'article, validation humaine d'échantillons, jeu de test. |
| Confusion avec du conseil juridique | Élevé | Mentions dans l'interface et les CGU ; avis d'un juriste sur le positionnement. |
| Corpus obsolète (articles modifiés ou abrogés) | Moyen | Versionnement, rafraîchissement périodique, ré-extraction ciblée. |
| Dérive des coûts (LLM, DataForSEO) | Moyen | Cache, idempotence, budgets plafonnés, alertes. |
| Divergence BigQuery / Neo4j | Moyen | Neo4j uniquement alimenté depuis marts ; reconstruction complète possible. |
| Fuite de secrets ou d'accès | Élevé | Secret Manager, moindre privilège, aucun identifiant côté client. |
| Non-conformité RGPD | Moyen | Hébergement UE, DPA, registre des traitements. |
| Périmètre MVP trop large | Moyen | Un seul livre du Code du travail ; Neo4j introduit après validation. |

> Vintage Legal Intelligence – Dossier de spécification et d'architecture v2.0 Page 15

## 16. Décisions ouvertes

Points à trancher avant la fin de la phase 0 :

| # | Décision | Options |
|---|---|---|
| 1 | Hébergement du graphe | Neo4j AuraDB (géré) ou auto-hébergé ; ou différer Neo4j (graphe calculé dans BigQuery au départ). |
| 2 | Fournisseur et modèle LLM | À comparer sur qualité en français juridique, coût, résidence des données. |
| 3 | Orchestration | Cloud Run Jobs (simple) ou Airflow/Composer, Prefect (plus riche). |
| 4 | Source du corpus | API Légifrance (PISTE) ou base LEGI (dumps DILA). |
| 5 | Formules du score d'écart | Valider les définitions du chapitre 8 et les pondérations. |
| 6 | Fréquence de rafraîchissement | Volumes mensuels ; SERP à la demande ou périodique. |
| 7 | Validation humaine | Qui relit, quel volume, quel seuil de confiance. |
| 8 | Modèle tarifaire | Paliers d'abonnement, quotas, crédits. |

> Vintage Legal Intelligence – Dossier de spécification et d'architecture v2.0 Page 16

## Annexe A – Les 22 tables du schéma en flocon

Proposition de découpage du dataset marts [À valider] : 12 dimensions, 6 tables de faits, 4 tables de ponts et de référence. La hiérarchie Code → Livre → Titre → Chapitre → Article est normalisée (flocon).

| # | Table | Type | Description |
|---|---|---|---|
| 1 | dim_code | Dimension | Codes juridiques (Code du travail, Code civil…). |
| 2 | dim_livre | Dimension | Livres d'un code (rattachés à dim_code). |
| 3 | dim_titre | Dimension | Titres d'un livre. |
| 4 | dim_chapitre | Dimension | Chapitres d'un titre. |
| 5 | dim_article | Dimension | Articles (identifiant LEGIARTI stable). |
| 6 | dim_article_version | Dimension | Versions d'un article : dates, état, texte de référence. |
| 7 | dim_notion | Dimension | Notions juridiques extraites. |
| 8 | dim_situation_vie | Dimension | Situations de vie (licenciement, congé, etc.). |
| 9 | dim_requete | Dimension | Requêtes web (texte, langue, pays). |
| 10 | dim_intention | Dimension | Types d'intention de recherche. |
| 11 | dim_pays_langue | Dimension | Combinaisons pays / langue. |
| 12 | dim_date | Dimension | Calendrier (jour, mois, année). |
| 13 | fait_extraction | Fait | Extraction IA : notion, article_version, confiance, modèle, prompt. |
| 14 | fait_notion_requete | Fait | Rattachement notion / requête avec score. |
| 15 | fait_metrique_mensuelle | Fait | Volume, CPC, concurrence par requête et par mois. |
| 16 | fait_resultat_serp | Fait | Résultats SERP : domaine, URL, position, date. |
| 17 | fait_gap_score | Fait | Indices D, S, I, écart, criticité, version_score. |
| 18 | fait_cout_api | Fait | Coûts LLM et DataForSEO par lot. |
| 19 | pont_article_renvoi | Pont | Liens RENVOIE_A / MODIFIE / ABROGE entre articles. |
| 20 | pont_notion_situation | Pont | Rattachement notion / situation de vie. |
| 21 | ref_taxonomie_intention | Référence | Taxonomie et règles de classification des intentions. |
| 22 | ref_modele_prompt | Référence | Registre des modèles et versions de prompts. |

> Vintage Legal Intelligence – Dossier de spécification et d'architecture v2.0 Page 17

## Annexe B – Contraintes et requêtes Neo4j

### B.1 Contraintes d'unicité

```cypher
CREATE CONSTRAINT article_id IF NOT EXISTS
 FOR (a:Article) REQUIRE a.article_id IS UNIQUE;
CREATE CONSTRAINT notion_id IF NOT EXISTS
 FOR (n:Notion) REQUIRE n.notion_id IS UNIQUE;
CREATE CONSTRAINT situation_id IF NOT EXISTS
 FOR (s:SituationDeVie) REQUIRE s.situation_id IS UNIQUE;
CREATE CONSTRAINT requete_id IF NOT EXISTS
 FOR (r:Requete) REQUIRE r.requete_id IS UNIQUE;
CREATE CONSTRAINT intention_type IF NOT EXISTS
 FOR (i:Intention) REQUIRE i.type IS UNIQUE;
```

### B.2 Exemple de synchronisation idempotente (MERGE)

```cypher
UNWIND $lignes AS l
MERGE (n:Notion {notion_id: l.notion_id})
 SET n.libelle = l.notion_libelle
MERGE (a:Article {article_id: l.article_id})
MERGE (n)-[:SE_FONDE_SUR]->(a)
MERGE (r:Requete {requete_id: l.requete_id})
 SET r.texte = l.requete_texte, r.langue = l.langue, r.pays = l.pays
MERGE (n)-[e:EST_EXPRIMEE_PAR]->(r)
 SET e.score = l.score;
```

### B.3 Exemple d'analyse : notions à forte demande et faible saturation

```cypher
MATCH (n:Notion)-[:EST_EXPRIMEE_PAR]->(r:Requete)-[:A_POUR_METRIQUE]->(m:Metrique)
WHERE m.mois >= date('2026-01-01')
WITH n, avg(m.volume) AS demande, avg(m.concurrence) AS concurrence
RETURN n.libelle, demande, concurrence,
 demande * (1 - concurrence) AS ecart_brut
ORDER BY ecart_brut DESC LIMIT 20;
```

Les requêtes de l'annexe B sont des exemples d'illustration ; les noms de propriétés suivent le modèle du chapitre 7 et doivent être alignés sur le schéma final.

## Annexe C – Glossaire

| Terme | Définition |
|---|---|
| Notion juridique | Concept de droit (ex. période d'essai, préavis) identifié dans un ou plusieurs articles. Remplace « entité juridique ». |
| Situation de vie | Contexte concret dans lequel une personne rencontre une notion (ex. perdre son emploi). |
| Requête | Expression saisie dans un moteur de recherche, avec langue et pays. |
| Intention de recherche | But de l'internaute : informationnel, transactionnel, navigationnel, commercial. |
| SERP | Page de résultats d'un moteur de recherche. |
| OLTP | Traitement transactionnel en ligne (comptes, projets). |
| RLS | Row Level Security : règles d'accès ligne par ligne dans PostgreSQL. |
| Schéma en flocon | Modélisation analytique avec dimensions normalisées en sous-dimensions. |
| Landing zone | Zone de dépôt des données brutes avant traitement. |
| Idempotence | Propriété d'une opération qui, rejouée, ne produit pas d'effet supplémentaire. |
| LEGIARTI / LEGITEXT | Identifiants Légifrance d'un article et d'un texte (code). |