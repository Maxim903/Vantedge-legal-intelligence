SELECT
  gap_score_id,
  notion_id,
  code_id,
  livre_id,
  pays_langue_id,
  CAST(date_calcul AS STRING) AS date_calcul,
  version_score,
  indice_demande,
  indice_saturation,
  indice_importance_normative,
  score_ecart,
  criticite_semantique,
  taille_cohorte
FROM `marts.fait_gap_score`
WHERE notion_id IN UNNEST(@notion_ids)
ORDER BY notion_id, date_calcul DESC, code_id, livre_id, pays_langue_id, version_score, gap_score_id
