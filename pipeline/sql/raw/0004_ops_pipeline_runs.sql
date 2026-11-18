CREATE TABLE IF NOT EXISTS `ops.pipeline_runs` (
  run_id STRING NOT NULL,
  job STRING NOT NULL,
  debut TIMESTAMP NOT NULL,
  fin TIMESTAMP,
  statut STRING NOT NULL,
  compteurs JSON,
  erreur STRING,
  cout_estime NUMERIC
)
PARTITION BY DATE(debut)
OPTIONS (description = 'Journal des executions du pipeline');
