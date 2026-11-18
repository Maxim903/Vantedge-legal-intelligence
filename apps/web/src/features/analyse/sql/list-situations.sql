SELECT situation.situation_id, situation.libelle
FROM `marts.dim_situation_vie` AS situation
WHERE EXISTS (
  SELECT 1
  FROM `marts.pont_notion_situation` AS pont
  JOIN `marts.fait_gap_score` AS score ON score.notion_id = pont.notion_id
  JOIN `marts.dim_code` AS code ON code.code_id = score.code_id
  JOIN `marts.dim_pays_langue` AS marche ON marche.pays_langue_id = score.pays_langue_id
  WHERE pont.situation_id = situation.situation_id
    AND code.legifrance_id = 'LEGITEXT000006072050'
    AND marche.pays = 'FR'
    AND marche.langue = 'fr'
    AND score.livre_id IS NULL
)
ORDER BY LOWER(situation.libelle), situation.situation_id
