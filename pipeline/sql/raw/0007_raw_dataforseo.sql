CREATE TABLE IF NOT EXISTS `raw.dataforseo_volumes` (
  archive_blob STRING NOT NULL,
  date_archive DATE NOT NULL,
  mot_cle STRING NOT NULL,
  localisation INT64,
  langue STRING,
  volume INT64,
  concurrence STRING,
  indice_concurrence INT64,
  cpc FLOAT64,
  cpc_bas FLOAT64,
  cpc_haut FLOAT64,
  volumes_mensuels ARRAY<STRUCT<annee INT64, mois INT64, volume INT64>>
)
PARTITION BY date_archive
CLUSTER BY archive_blob
OPTIONS (description = 'Volumes Google Ads DataForSEO charges depuis les archives GCS');

CREATE TABLE IF NOT EXISTS `raw.dataforseo_serp` (
  archive_blob STRING NOT NULL,
  date_archive DATE NOT NULL,
  mot_cle STRING NOT NULL,
  localisation INT64,
  langue STRING,
  type_resultat STRING,
  rang_groupe INT64,
  rang_absolu INT64,
  domaine STRING,
  titre STRING,
  url STRING
)
PARTITION BY date_archive
CLUSTER BY archive_blob
OPTIONS (description = 'Resultats SERP DataForSEO charges depuis les archives GCS');

CREATE TABLE IF NOT EXISTS `raw.dataforseo_intent` (
  archive_blob STRING NOT NULL,
  date_archive DATE NOT NULL,
  mot_cle STRING NOT NULL,
  intention STRING,
  probabilite FLOAT64
)
PARTITION BY date_archive
CLUSTER BY archive_blob
OPTIONS (description = 'Intentions DataForSEO chargees depuis les archives GCS');
