## Annexe B – Contraintes et requêtes Neo4j

### B.1 Contraintes d'unicité

```cypher
CREATE CONSTRAINT article_id IF NOT EXISTS
 FOR (a:Article) REQUIRE a.article_id IS UNIQUE;
CREATE CONSTRAINT notion_id IF NOT EXISTS
 FOR (n:Notion) REQUIRE n.notion_id IS UNIQUE;
CREATE CONSTRAINT situation_id IF NOT EXISTS
 FOR (s:SituationDeVie) REQUIRE s.situation_id IS UNIQUE;
CREATE CONSTRAINT requete_id IF NOT EXISTS
 FOR (r:Requete) REQUIRE r.requete_id IS UNIQUE;
CREATE CONSTRAINT intention_type IF NOT EXISTS
 FOR (i:Intention) REQUIRE i.type IS UNIQUE;
```

### B.2 Exemple de synchronisation idempotente (MERGE)

```cypher
UNWIND $lignes AS l
MERGE (n:Notion {notion_id: l.notion_id})
 SET n.libelle = l.notion_libelle
MERGE (a:Article {article_id: l.article_id})
MERGE (n)-[:SE_FONDE_SUR]->(a)
MERGE (r:Requete {requete_id: l.requete_id})
 SET r.texte = l.requete_texte, r.langue = l.langue, r.pays = l.pays
MERGE (n)-[e:EST_EXPRIMEE_PAR]->(r)
 SET e.score = l.score;
```

### B.3 Exemple d'analyse : notions à forte demande et faible saturation

```cypher
MATCH (n:Notion)-[:EST_EXPRIMEE_PAR]->(r:Requete)-[:A_POUR_METRIQUE]->(m:Metrique)
WHERE m.mois >= date('2026-01-01')
WITH n, avg(m.volume) AS demande, avg(m.concurrence) AS concurrence
RETURN n.libelle, demande, concurrence,
 demande * (1 - concurrence) AS ecart_brut
ORDER BY ecart_brut DESC LIMIT 20;
```

Les requêtes de l'annexe B sont des exemples d'illustration ; les noms de propriétés suivent le modèle du chapitre 7 et doivent être alignés sur le schéma final.