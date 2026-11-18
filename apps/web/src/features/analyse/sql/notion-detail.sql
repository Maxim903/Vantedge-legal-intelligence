SELECT notion_id, libelle, definition_courte, score_confiance
FROM `marts.dim_notion`
WHERE notion_id = @notion_id
LIMIT 2
