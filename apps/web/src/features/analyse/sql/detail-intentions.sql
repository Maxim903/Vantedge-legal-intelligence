SELECT
  requete.intention_type,
  COUNT(*) AS nombre_requetes
FROM `marts.fait_notion_requete` AS lien
JOIN `marts.dim_requete` AS requete ON requete.requete_id = lien.requete_id
JOIN `marts.dim_pays_langue` AS marche ON marche.pays_langue_id = requete.pays_langue_id
WHERE lien.notion_id = @notion_id AND marche.pays = 'FR' AND marche.langue = 'fr'
GROUP BY requete.intention_type
ORDER BY nombre_requetes DESC, requete.intention_type
