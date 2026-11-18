CREATE TABLE IF NOT EXISTS `raw.article_versions` (
  article_version_id STRING NOT NULL,
  article_id STRING NOT NULL,
  date_debut DATE NOT NULL,
  date_fin DATE,
  etat STRING NOT NULL,
  texte STRING,
  texte_ref STRING,
  date_chargement DATE DEFAULT CURRENT_DATE() NOT NULL
)
PARTITION BY date_chargement
OPTIONS (description = 'Versions temporelles des articles juridiques');
