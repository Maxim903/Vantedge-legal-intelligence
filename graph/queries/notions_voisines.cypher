MATCH (source:Notion {notion_id: $notion_id})-[:SE_FONDE_SUR]->(article:Article)
      <-[:SE_FONDE_SUR]-(voisine:Notion)
WHERE voisine <> source
WITH DISTINCT voisine, article
ORDER BY article.article_id
WITH voisine, collect({article_id: article.article_id, numero: article.numero}) AS articles
RETURN voisine.notion_id AS notion_id, voisine.libelle AS libelle,
       size(articles) AS nombre_articles_communs, articles AS articles_communs
ORDER BY nombre_articles_communs DESC, notion_id
