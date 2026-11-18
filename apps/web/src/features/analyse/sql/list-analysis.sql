SELECT
  score.gap_score_id,
  score.notion_id,
  notion.libelle AS notion_libelle,
  score.code_id,
  score.livre_id,
  score.pays_langue_id,
  CAST(score.date_calcul AS STRING) AS date_calcul,
  score.version_score,
  score.indice_demande,
  score.indice_saturation,
  score.indice_importance_normative,
  score.score_ecart,
  score.criticite_semantique,
  score.taille_cohorte
FROM `marts.fait_gap_score` AS score
JOIN `marts.dim_notion` AS notion ON notion.notion_id = score.notion_id
JOIN `marts.dim_code` AS code ON code.code_id = score.code_id
JOIN `marts.dim_pays_langue` AS marche ON marche.pays_langue_id = score.pays_langue_id
WHERE code.legifrance_id = 'LEGITEXT000006072050'
  AND marche.pays = 'FR'
  AND marche.langue = 'fr'
  AND score.livre_id IS NULL
  AND (
    @situation = ''
    OR EXISTS (
      SELECT 1
      FROM `marts.pont_notion_situation` AS pont
      WHERE pont.notion_id = score.notion_id AND pont.situation_id = @situation
    )
  )
ORDER BY
  CASE WHEN @tri = 'notion' AND @ordre = 'asc' THEN LOWER(notion.libelle) END ASC,
  CASE WHEN @tri = 'notion' AND @ordre = 'desc' THEN LOWER(notion.libelle) END DESC,
  CASE WHEN @tri = 'demande' AND @ordre = 'asc' THEN score.indice_demande END ASC,
  CASE WHEN @tri = 'demande' AND @ordre = 'desc' THEN score.indice_demande END DESC,
  CASE WHEN @tri = 'saturation' AND @ordre = 'asc' THEN score.indice_saturation END ASC,
  CASE WHEN @tri = 'saturation' AND @ordre = 'desc' THEN score.indice_saturation END DESC,
  CASE WHEN @tri = 'importance' AND @ordre = 'asc' THEN score.indice_importance_normative END ASC,
  CASE WHEN @tri = 'importance' AND @ordre = 'desc' THEN score.indice_importance_normative END DESC,
  CASE WHEN @tri = 'ecart' AND @ordre = 'asc' THEN score.score_ecart END ASC,
  CASE WHEN @tri = 'ecart' AND @ordre = 'desc' THEN score.score_ecart END DESC,
  CASE WHEN @tri = 'criticite' AND @ordre = 'asc' THEN score.criticite_semantique END ASC,
  CASE WHEN @tri = 'criticite' AND @ordre = 'desc' THEN score.criticite_semantique END DESC,
  score.gap_score_id ASC
LIMIT @limite OFFSET @offset
