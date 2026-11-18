CREATE TABLE IF NOT EXISTS `ops.couts_api` (
  cout_id STRING NOT NULL,
  lot_id STRING NOT NULL,
  fournisseur STRING NOT NULL,
  service STRING NOT NULL,
  date_cout DATE NOT NULL,
  montant NUMERIC NOT NULL,
  devise STRING NOT NULL,
  details JSON
)
PARTITION BY date_cout
OPTIONS (description = 'Couts reels des appels API par lot');