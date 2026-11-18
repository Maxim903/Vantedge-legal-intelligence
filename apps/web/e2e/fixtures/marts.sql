-- Jeu synthétique destiné exclusivement au projet BigQuery dédié à la CI.
CREATE TABLE IF NOT EXISTS `marts.dim_code` (code_id STRING, legifrance_id STRING);
CREATE TABLE IF NOT EXISTS `marts.dim_livre` (livre_id STRING, code_id STRING);
CREATE TABLE IF NOT EXISTS `marts.dim_titre` (titre_id STRING, livre_id STRING);
CREATE TABLE IF NOT EXISTS `marts.dim_chapitre` (chapitre_id STRING, titre_id STRING);
CREATE TABLE IF NOT EXISTS `marts.dim_article` (article_id STRING, chapitre_id STRING, numero STRING);
CREATE TABLE IF NOT EXISTS `marts.dim_article_version` (article_version_id STRING, article_id STRING, etat STRING, date_debut DATE, date_fin DATE);
CREATE TABLE IF NOT EXISTS `marts.fait_extraction` (notion_id STRING, article_version_id STRING);
CREATE TABLE IF NOT EXISTS `marts.dim_notion` (notion_id STRING, libelle STRING, definition_courte STRING, score_confiance FLOAT64);
CREATE TABLE IF NOT EXISTS `marts.dim_pays_langue` (pays_langue_id STRING, pays STRING, langue STRING);
CREATE TABLE IF NOT EXISTS `marts.dim_situation_vie` (situation_id STRING, libelle STRING);
CREATE TABLE IF NOT EXISTS `marts.pont_notion_situation` (notion_id STRING, situation_id STRING);
CREATE TABLE IF NOT EXISTS `marts.fait_gap_score` (gap_score_id STRING, notion_id STRING, code_id STRING, livre_id STRING, pays_langue_id STRING, date_calcul DATE, version_score STRING, indice_demande FLOAT64, indice_saturation FLOAT64, indice_importance_normative FLOAT64, score_ecart FLOAT64, criticite_semantique FLOAT64, taille_cohorte INT64);
CREATE TABLE IF NOT EXISTS `marts.fait_notion_requete` (notion_id STRING, requete_id STRING, score_rattachement FLOAT64);
CREATE TABLE IF NOT EXISTS `marts.dim_requete` (requete_id STRING, texte STRING, pays_langue_id STRING, intention_type STRING);
CREATE TABLE IF NOT EXISTS `marts.fait_metrique_mensuelle` (requete_id STRING, pays_langue_id STRING, mois DATE, volume FLOAT64);
CREATE TABLE IF NOT EXISTS `marts.fait_resultat_serp` (requete_id STRING, pays_langue_id STRING, date_resultat DATE, position INT64, domaine STRING, url STRING);

MERGE `marts.dim_code` AS t USING (SELECT 'e2e-code' AS id) AS s ON t.code_id = s.id
WHEN NOT MATCHED THEN INSERT (code_id, legifrance_id) VALUES (s.id, 'LEGITEXT000006072050');
MERGE `marts.dim_pays_langue` AS t USING (SELECT 'e2e-fr' AS id) AS s ON t.pays_langue_id = s.id
WHEN NOT MATCHED THEN INSERT (pays_langue_id, pays, langue) VALUES (s.id, 'FR', 'fr');
MERGE `marts.dim_notion` AS t USING (SELECT 'e2e-notion' AS id) AS s ON t.notion_id = s.id
WHEN NOT MATCHED THEN INSERT (notion_id, libelle, definition_courte, score_confiance)
VALUES (s.id, 'Notion synthétique E2E', 'Donnée de test.', 0.9);
MERGE `marts.fait_gap_score` AS t USING (SELECT 'e2e-score' AS id) AS s ON t.gap_score_id = s.id
WHEN NOT MATCHED THEN INSERT (gap_score_id, notion_id, code_id, livre_id, pays_langue_id, date_calcul, version_score, indice_demande, indice_saturation, indice_importance_normative, score_ecart, criticite_semantique, taille_cohorte)
VALUES (s.id, 'e2e-notion', 'e2e-code', NULL, 'e2e-fr', DATE '2026-01-01', 'e2e-v1', 60, 20, 40, 48, 30, 1);
