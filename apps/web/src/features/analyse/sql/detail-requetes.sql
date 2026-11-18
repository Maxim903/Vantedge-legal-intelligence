SELECT requete.requete_id, requete.texte, lien.score_rattachement
FROM `marts.fait_notion_requete` AS lien
JOIN `marts.dim_requete` AS requete ON requete.requete_id = lien.requete_id
JOIN `marts.dim_pays_langue` AS marche ON marche.pays_langue_id = requete.pays_langue_id
WHERE lien.notion_id = @notion_id AND marche.pays = 'FR' AND marche.langue = 'fr'
ORDER BY lien.score_rattachement DESC, requete.texte, requete.requete_id
