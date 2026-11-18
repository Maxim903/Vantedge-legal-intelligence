SELECT notion_id, libelle, definition_courte, score_confiance
FROM `marts.dim_notion`
WHERE STRPOS(LOWER(libelle), LOWER(@filtre)) > 0 OR @filtre = ''
ORDER BY
  CASE WHEN @tri = 'asc' THEN LOWER(libelle) END ASC,
  CASE WHEN @tri = 'desc' THEN LOWER(libelle) END DESC,
  notion_id ASC
LIMIT @limite OFFSET @offset
