CREATE TABLE IF NOT EXISTS `ops.archives_chargees` (
  archive_blob STRING NOT NULL,
  endpoint STRING NOT NULL,
  table_cible STRING NOT NULL,
  lignes INT64 NOT NULL,
  run_id STRING NOT NULL,
  date_chargement TIMESTAMP NOT NULL
)
PARTITION BY DATE(date_chargement)
OPTIONS (description = 'Archives GCS DataForSEO deja chargees dans raw');
