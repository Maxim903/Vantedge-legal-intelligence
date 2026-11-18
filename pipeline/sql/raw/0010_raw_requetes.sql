CREATE TABLE IF NOT EXISTS `raw.requetes_candidates` (
  notion_id STRING NOT NULL,
  requete STRING NOT NULL,
  score_rattachement FLOAT64 NOT NULL
)
OPTIONS (description = 'Requetes candidates par notion, reconstruites par build_seed_queries');

CREATE TABLE IF NOT EXISTS `raw.requetes_intentions` (
  requete STRING NOT NULL,
  intention_type STRING NOT NULL,
  score_confiance FLOAT64 NOT NULL,
  methode STRING NOT NULL,
  date_classification DATE NOT NULL
)
OPTIONS (description = 'Intention dominante des requetes candidates, produite par collect_intent');
