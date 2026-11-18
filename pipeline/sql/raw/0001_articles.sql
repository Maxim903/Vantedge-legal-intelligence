CREATE TABLE IF NOT EXISTS `raw.articles` (
  article_id STRING NOT NULL,
  chapitre_id STRING,
  numero STRING,
  date_chargement DATE DEFAULT CURRENT_DATE() NOT NULL
)
PARTITION BY date_chargement
OPTIONS (description = 'Articles juridiques du corpus');
