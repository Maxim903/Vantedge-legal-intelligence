WITH resultats AS (
  SELECT
    requete.requete_id,
    requete.texte,
    serp.date_resultat,
    serp.position,
    serp.domaine,
    serp.url
  FROM `marts.fait_notion_requete` AS lien
  JOIN `marts.dim_requete` AS requete ON requete.requete_id = lien.requete_id
  JOIN `marts.dim_pays_langue` AS marche ON marche.pays_langue_id = requete.pays_langue_id
  JOIN `marts.fait_resultat_serp` AS serp
    ON serp.requete_id = requete.requete_id AND serp.pays_langue_id = requete.pays_langue_id
  WHERE lien.notion_id = @notion_id AND marche.pays = 'FR' AND marche.langue = 'fr'
  QUALIFY serp.date_resultat = MAX(serp.date_resultat) OVER (PARTITION BY requete.requete_id)
)
SELECT requete_id, texte, CAST(date_resultat AS STRING) AS date_resultat, position, domaine, url
FROM resultats
WHERE position BETWEEN 1 AND 10
ORDER BY texte, requete_id, position
