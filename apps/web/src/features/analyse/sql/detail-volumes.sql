SELECT
  CAST(metrique.mois AS STRING) AS mois,
  SUM(metrique.volume * lien.score_rattachement) / SUM(lien.score_rattachement) AS volume
FROM `marts.fait_notion_requete` AS lien
JOIN `marts.dim_requete` AS requete ON requete.requete_id = lien.requete_id
JOIN `marts.dim_pays_langue` AS marche ON marche.pays_langue_id = requete.pays_langue_id
JOIN `marts.fait_metrique_mensuelle` AS metrique
  ON metrique.requete_id = requete.requete_id
  AND metrique.pays_langue_id = requete.pays_langue_id
WHERE lien.notion_id = @notion_id
  AND marche.pays = 'FR' AND marche.langue = 'fr'
  AND metrique.volume IS NOT NULL AND lien.score_rattachement > 0
GROUP BY metrique.mois
ORDER BY metrique.mois
