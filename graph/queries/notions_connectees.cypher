MATCH (notion:Notion)
OPTIONAL MATCH (notion)-[relation]-()
RETURN notion.notion_id AS notion_id, notion.libelle AS libelle,
       count(DISTINCT relation) AS degre
ORDER BY degre DESC, notion_id
LIMIT $limite
