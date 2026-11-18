CREATE TABLE IF NOT EXISTS `raw.entites_extraites` (
  extraction_id STRING NOT NULL,
  article_version_id STRING NOT NULL,
  notion_libelle STRING NOT NULL,
  situation_de_vie STRING,
  score_confiance FLOAT64 NOT NULL,
  modele_llm STRING NOT NULL,
  version_prompt STRING NOT NULL,
  extrait_le TIMESTAMP NOT NULL,
  statut_validation STRING NOT NULL,
  valide_par STRING
)
PARTITION BY DATE(extrait_le)
OPTIONS (description = 'Notions extraites et leur validation');
