# Schéma du dataset `marts`

Ce document détaille les 22 tables proposées dans l'annexe A. Les clés primaires et étrangères ci-dessous sont des contraintes logiques : BigQuery ne les applique pas et elles doivent être vérifiées par les tests du pipeline.

`PK` : clé primaire ; `FK` : clé étrangère ; `UK` : clé unique logique. Les clés composites sont indiquées comme telles. Les types sont des types natifs BigQuery.

## Dimensions

### 1. `dim_code`

Grain : un code juridique.

| Colonne | Type BigQuery | Description | Clé |
|---|---|---|---|
| `code_id` | STRING | Identifiant stable interne du code. | PK |
| `legifrance_id` | STRING | Identifiant de texte Légifrance, par exemple LEGITEXT. | UK |
| `libelle` | STRING | Libellé du code. | |
| `ordre` | INT64 | Ordre de présentation. | |

### 2. `dim_livre`

Grain : un livre d'un code.

| Colonne | Type BigQuery | Description | Clé |
|---|---|---|---|
| `livre_id` | STRING | Identifiant stable interne du livre. | PK |
| `code_id` | STRING | Code auquel le livre appartient. | FK `dim_code.code_id` |
| `legifrance_id` | STRING | Identifiant Légifrance du livre. | UK |
| `libelle` | STRING | Libellé du livre. | |
| `ordre` | INT64 | Ordre du livre dans le code. | |

### 3. `dim_titre`

Grain : un titre d'un livre.

| Colonne | Type BigQuery | Description | Clé |
|---|---|---|---|
| `titre_id` | STRING | Identifiant stable interne du titre. | PK |
| `livre_id` | STRING | Livre auquel le titre appartient. | FK `dim_livre.livre_id` |
| `legifrance_id` | STRING | Identifiant Légifrance du titre. | UK |
| `libelle` | STRING | Libellé du titre. | |
| `ordre` | INT64 | Ordre du titre dans le livre. | |

### 4. `dim_chapitre`

Grain : un chapitre d'un titre.

| Colonne | Type BigQuery | Description | Clé |
|---|---|---|---|
| `chapitre_id` | STRING | Identifiant stable interne du chapitre. | PK |
| `titre_id` | STRING | Titre auquel le chapitre appartient. | FK `dim_titre.titre_id` |
| `legifrance_id` | STRING | Identifiant Légifrance du chapitre. | UK |
| `libelle` | STRING | Libellé du chapitre. | |
| `ordre` | INT64 | Ordre du chapitre dans le titre. | |

### 5. `dim_article`

Grain : un article juridique, indépendamment de ses versions.

| Colonne | Type BigQuery | Description | Clé |
|---|---|---|---|
| `article_id` | STRING | Identifiant stable de l'article, de type LEGIARTI. | PK |
| `chapitre_id` | STRING | Chapitre auquel l'article appartient. | FK `dim_chapitre.chapitre_id` |
| `numero` | STRING | Numéro de l'article. | |

### 6. `dim_article_version`

Grain : une version temporelle d'un article.

| Colonne | Type BigQuery | Description | Clé |
|---|---|---|---|
| `article_version_id` | STRING | Identifiant stable de la version. | PK |
| `article_id` | STRING | Article concerné par cette version. | FK `dim_article.article_id` |
| `date_debut` | DATE | Début de validité de la version. | |
| `date_fin` | DATE | Fin de validité ; NULL si la période est ouverte. | |
| `etat` | STRING | État de la version : `VIGUEUR`, `MODIFIE` ou `ABROGE`. | |
| `texte_ref` | STRING | Référence ou pointeur vers le texte de cette version dans BigQuery. | |

Clé unique logique proposée : (`article_id`, `date_debut`).

### 7. `dim_notion`

Grain : une notion juridique canonique.

| Colonne | Type BigQuery | Description | Clé |
|---|---|---|---|
| `notion_id` | STRING | Identifiant stable de la notion. | PK |
| `libelle` | STRING | Libellé de la notion. | |
| `definition_courte` | STRING | Définition courte de la notion. | |
| `score_confiance` | FLOAT64 | Score de confiance associé à la notion, de 0 à 1. | |

### 8. `dim_situation_vie`

Grain : une situation de vie canonique.

| Colonne | Type BigQuery | Description | Clé |
|---|---|---|---|
| `situation_id` | STRING | Identifiant stable de la situation de vie. | PK |
| `libelle` | STRING | Libellé de la situation de vie. | |

### 9. `dim_requete`

Grain : une requête distinguée par son texte, son pays et sa langue.

| Colonne | Type BigQuery | Description | Clé |
|---|---|---|---|
| `requete_id` | STRING | Hash stable de la requête et de son contexte pays/langue. | PK |
| `texte` | STRING | Texte saisi dans le moteur de recherche. | |
| `pays_langue_id` | STRING | Combinaison pays/langue de la requête. | FK `dim_pays_langue.pays_langue_id` |
| `intention_type` | STRING | Type d'intention dominante de la requête. | FK `dim_intention.type` |

### 10. `dim_intention`

Grain : un type d'intention de recherche.

| Colonne | Type BigQuery | Description | Clé |
|---|---|---|---|
| `type` | STRING | Type : `informationnelle`, `transactionnelle`, `navigationnelle` ou `commerciale`. | PK |

### 11. `dim_pays_langue`

Grain : une combinaison de pays et de langue.

| Colonne | Type BigQuery | Description | Clé |
|---|---|---|---|
| `pays_langue_id` | STRING | Identifiant stable de la combinaison. | PK |
| `pays` | STRING | Code pays, par exemple `FR`. | |
| `langue` | STRING | Code langue, par exemple `fr`. | |

Clé unique logique : (`pays`, `langue`).

### 12. `dim_date`

Grain : un jour du calendrier.

| Colonne | Type BigQuery | Description | Clé |
|---|---|---|---|
| `date_id` | DATE | Date calendaire. | PK |
| `jour` | INT64 | Jour du mois. | |
| `mois` | INT64 | Mois de l'année, de 1 à 12. | |
| `annee` | INT64 | Année calendaire. | |

## Tables de faits

### 13. `fait_extraction`

Grain : une notion extraite d'une version d'article par une exécution de modèle/prompt.

| Colonne | Type BigQuery | Description | Clé |
|---|---|---|---|
| `extraction_id` | STRING | Identifiant de l'enregistrement d'extraction. | PK |
| `article_version_id` | STRING | Version d'article analysée. | FK `dim_article_version.article_version_id` |
| `notion_id` | STRING | Notion produite ou confirmée par l'extraction. | FK `dim_notion.notion_id` |
| `situation_id` | STRING | Situation de vie associée, si présente. | FK `dim_situation_vie.situation_id` |
| `score_confiance` | FLOAT64 | Confiance de l'extraction, de 0 à 1. | |
| `modele_prompt_id` | STRING | Version du modèle et du prompt utilisés. | FK `ref_modele_prompt.modele_prompt_id` |
| `extrait_le` | TIMESTAMP | Date et heure de l'extraction. | |
| `statut_validation` | STRING | Statut : `AUTO`, `A_REVOIR`, `VALIDE` ou `REJETE`. | |
| `valide_par` | STRING | Identifiant de la personne ayant validé l'extraction, si applicable. | |

### 14. `fait_notion_requete`

Grain : un rattachement entre une notion et une requête.

| Colonne | Type BigQuery | Description | Clé |
|---|---|---|---|
| `notion_id` | STRING | Notion rattachée. | PK (composite), FK `dim_notion.notion_id` |
| `requete_id` | STRING | Requête rattachée à la notion. | PK (composite), FK `dim_requete.requete_id` |
| `score_rattachement` | FLOAT64 | Score de rattachement de la requête à la notion, de 0 à 1. | |

### 15. `fait_metrique_mensuelle`

Grain : une requête, un mois et une combinaison pays/langue.

| Colonne | Type BigQuery | Description | Clé |
|---|---|---|---|
| `requete_id` | STRING | Requête mesurée. | PK (composite), FK `dim_requete.requete_id` |
| `pays_langue_id` | STRING | Pays et langue de la mesure. | PK (composite), FK `dim_pays_langue.pays_langue_id` |
| `mois` | DATE | Mois de mesure, stocké comme le premier jour du mois. | PK (composite), FK `dim_date.date_id` |
| `volume` | INT64 | Volume mensuel estimé. | |
| `cpc` | FLOAT64 | Coût par clic. | |
| `concurrence` | FLOAT64 | Indicateur de concurrence publicitaire. | |
| `source_payload` | STRING | Chemin GCS du payload source. | |

### 16. `fait_resultat_serp`

Grain : une position dans les résultats SERP pour une requête, une date et un pays/langue.

| Colonne | Type BigQuery | Description | Clé |
|---|---|---|---|
| `requete_id` | STRING | Requête recherchée. | PK (composite), FK `dim_requete.requete_id` |
| `pays_langue_id` | STRING | Pays et langue du résultat. | PK (composite), FK `dim_pays_langue.pays_langue_id` |
| `date_resultat` | DATE | Date d'observation du résultat. | PK (composite), FK `dim_date.date_id` |
| `position` | INT64 | Position du résultat dans la SERP. | PK (composite) |
| `domaine` | STRING | Domaine du résultat. | |
| `url` | STRING | URL du résultat. | |
| `source_payload` | STRING | Chemin GCS du payload source, si disponible. | |

### 17. `fait_gap_score`

Grain : un score de notion pour une version de formule, une date de calcul et un périmètre.

| Colonne | Type BigQuery | Description | Clé |
|---|---|---|---|
| `gap_score_id` | STRING | Identifiant de l'enregistrement de score. | PK |
| `notion_id` | STRING | Notion évaluée. | FK `dim_notion.notion_id` |
| `code_id` | STRING | Code juridique du périmètre. | FK `dim_code.code_id` |
| `livre_id` | STRING | Livre du périmètre, si le calcul est limité à un livre. | FK `dim_livre.livre_id` |
| `pays_langue_id` | STRING | Pays et langue du périmètre marché. | FK `dim_pays_langue.pays_langue_id` |
| `date_calcul` | DATE | Date de calcul du score. | FK `dim_date.date_id` |
| `version_score` | STRING | Identifiant immuable de la formule, par exemple `gap-v1`. | |
| `indice_demande` | FLOAT64 | Indice D, de 0 à 100. | |
| `indice_saturation` | FLOAT64 | Indice S, de 0 à 100. | |
| `indice_importance_normative` | FLOAT64 | Indice I, de 0 à 100. | |
| `score_ecart` | FLOAT64 | Score d'écart D × (1 − S/100), de 0 à 100. | |
| `criticite_semantique` | FLOAT64 | Criticité sémantique, de 0 à 100. | |
| `taille_cohorte` | INT64 | Nombre de notions dans le périmètre de normalisation percentile. | |

Clé unique logique proposée : (`notion_id`, `version_score`, `date_calcul`, `code_id`, `livre_id`, `pays_langue_id`).

### 18. `fait_cout_api`

Grain : un poste de coût associé à un lot d'ingestion ou d'enrichissement.

| Colonne | Type BigQuery | Description | Clé |
|---|---|---|---|
| `cout_id` | STRING | Identifiant de l'enregistrement de coût. | PK |
| `lot_id` | STRING | Identifiant du lot associé, correspondant à `ops.pipeline_runs` hors des 22 tables. | |
| `fournisseur` | STRING | Fournisseur facturé, par exemple LLM ou DataForSEO. | |
| `service` | STRING | Service ou endpoint à l'origine du coût. | |
| `date_cout` | DATE | Date d'imputation du coût. | FK `dim_date.date_id` |
| `montant` | NUMERIC | Montant du coût. | |
| `devise` | STRING | Code de devise du montant. | |
| `details` | JSON | Détails disponibles du coût ou de la consommation. | |

## Tables de pont

### 19. `pont_article_renvoi`

Grain : une relation normative orientée entre deux articles.

| Colonne | Type BigQuery | Description | Clé |
|---|---|---|---|
| `article_source_id` | STRING | Article à l'origine du lien. | PK (composite), FK `dim_article.article_id` |
| `type_relation` | STRING | Type de lien : `RENVOIE_A`, `MODIFIE` ou `ABROGE`. | PK (composite) |
| `article_cible_id` | STRING | Article cible du lien. | PK (composite), FK `dim_article.article_id` |

### 20. `pont_notion_situation`

Grain : un rattachement entre une notion et une situation de vie.

| Colonne | Type BigQuery | Description | Clé |
|---|---|---|---|
| `notion_id` | STRING | Notion rattachée. | PK (composite), FK `dim_notion.notion_id` |
| `situation_id` | STRING | Situation de vie associée. | PK (composite), FK `dim_situation_vie.situation_id` |

## Tables de référence

### 21. `ref_taxonomie_intention`

Grain : un type d'intention dans une version de taxonomie.

| Colonne | Type BigQuery | Description | Clé |
|---|---|---|---|
| `version_taxonomie` | STRING | Version de la taxonomie. | PK (composite) |
| `type` | STRING | Type d'intention référencé. | PK (composite), FK `dim_intention.type` |
| `definition` | STRING | Définition du type d'intention. | |
| `regles_classification` | JSON | Règles utilisées pour classer les intentions. | |
| `date_debut` | DATE | Début de validité de cette entrée de taxonomie. | |
| `date_fin` | DATE | Fin de validité ; NULL si la période est ouverte. | |

### 22. `ref_modele_prompt`

Grain : une combinaison versionnée de modèle et de prompt.

| Colonne | Type BigQuery | Description | Clé |
|---|---|---|---|
| `modele_prompt_id` | STRING | Identifiant stable de la combinaison modèle/prompt. | PK |
| `modele_llm` | STRING | Fournisseur et nom du modèle LLM. | |
| `version_modele` | STRING | Version du modèle. | |
| `version_prompt` | STRING | Version du prompt. | |
| `prompt_hash` | STRING | Empreinte du contenu exact du prompt. | |
| `date_debut` | DATE | Date de début d'utilisation de cette combinaison. | |
| `date_fin` | DATE | Date de fin d'utilisation ; NULL si la période est ouverte. | |

Clé unique logique proposée : (`modele_llm`, `version_modele`, `version_prompt`).

## Hypothèses

- L'annexe A fournit les 22 noms, catégories et grains généraux, mais pas les colonnes détaillées ni leurs types ; les colonnes additionnelles, identifiants internes, types et descriptions de ce document sont des propositions de modélisation.
- Les identifiants `*_id` internes sont des `STRING` stables. Les identifiants Légifrance stables servent de clés naturelles lorsqu'ils existent ; `article_id` est l'identifiant LEGIARTI.
- Les clés primaires et étrangères sont logiques et non garanties par BigQuery ; le pipeline doit contrôler unicité et intégrité référentielle.
- Les faits sont historisés sans écrasement lorsque le modèle le requiert. `fait_extraction` conserve les résultats d'extraction et leur validation ; les libellés canoniques sont stockés dans les dimensions.
- `dim_requete` référence une seule intention dominante et normalise le pays/langue vers `dim_pays_langue`. L'identifiant `requete_id` est un hash du texte, du pays et de la langue, conformément au principe de clé d'idempotence.
- La granularité de `fait_metrique_mensuelle` inclut pays/langue, bien que la clé du chapitre 7 ne mentionne que requête et mois ; ceci permet de respecter la variation par pays et langue du chapitre 6.
- `fait_resultat_serp` reprend la date et la position de la clé décrite au chapitre 7 et ajoute pays/langue à sa granularité. Les dates mensuelles de `fait_metrique_mensuelle` sont représentées par le premier jour du mois.
- `fait_gap_score` ajoute code/livre, pays/langue, date de calcul et taille de cohorte afin d'identifier le périmètre et de reproduire les percentiles. Sa clé unique logique est à confirmer selon les périmètres réellement autorisés.
- `fait_extraction` suppose une ligne par notion extraite d'une version d'article ; `situation_id` est nullable. Les sorties brutes multi-notions et leur JSON restent conservés dans les couches raw/staging.
- Les coûts sont enregistrés par poste et par lot ; `lot_id` référence `ops.pipeline_runs`, table hors des 22 tables du dataset marts.
- Les relations normatives sont modélisées au niveau des articles stables, sans versionner chaque lien par période. Une gestion temporelle des liens nécessiterait des colonnes et une clé supplémentaires.
- Les noms de colonnes suivent `snake_case` ASCII sans accents. Les valeurs d'état, de relation et de validation sont des chaînes contrôlées par le pipeline.