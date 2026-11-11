CREATE TABLE IF NOT EXISTS `ops.extraction_results` (
  article_version_id STRING NOT NULL,
  version_prompt STRING NOT NULL,
  modele_llm STRING NOT NULL,
  statut STRING NOT NULL,
  resultat_json STRING NOT NULL,
  raison STRING,
  extrait_le TIMESTAMP NOT NULL,
  run_id STRING NOT NULL
)
PARTITION BY DATE(extrait_le)
CLUSTER BY article_version_id, version_prompt, modele_llm
OPTIONS (description = 'Resultats et quarantaines des extractions');
