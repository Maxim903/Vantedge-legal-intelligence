MATCH (notion:Notion)-[:APPARTIENT_A]->(situation:SituationDeVie)
WITH DISTINCT situation, notion
ORDER BY situation.situation_id, notion.notion_id
WITH situation, collect({notion_id: notion.notion_id, libelle: notion.libelle}) AS notions
RETURN situation.situation_id AS situation_id, situation.libelle AS libelle,
       size(notions) AS nombre_notions, notions
ORDER BY nombre_notions DESC, situation_id
