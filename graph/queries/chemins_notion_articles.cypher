MATCH chemin = (notion:Notion {notion_id: $notion_id})-[:SE_FONDE_SUR]->(:Article)
               -[:RENVOIE_A|MODIFIE|ABROGE*0..3]->(article:Article)
WHERE all(noeud IN tail(nodes(chemin)) WHERE noeud:Article)
  AND all(noeud IN nodes(chemin)
          WHERE single(autre IN nodes(chemin) WHERE autre = noeud))
RETURN article.article_id AS article_id, article.numero AS numero,
       length(chemin) - 1 AS nombre_liens_normatifs, chemin
ORDER BY nombre_liens_normatifs, article_id,
         [noeud IN nodes(chemin) | coalesce(noeud.article_id, noeud.notion_id)],
         [relation IN relationships(chemin) | type(relation)]
