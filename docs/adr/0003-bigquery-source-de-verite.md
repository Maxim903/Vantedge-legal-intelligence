# ADR-0003 : BigQuery comme source de vérité

## Contexte

BigQuery et Neo4j étaient susceptibles d'être alimentés séparément à partir du même JSON, ce qui pouvait produire des données divergentes. Une base de données n'est pas un nœud sémantique du graphe.

## Décision

BigQuery, et plus précisément ses tables curées, est la source de vérité unique. Neo4j et l'interface sont des projections de ces données. Neo4j est alimenté depuis BigQuery ; les nœuds `:Article` portent l'identifiant Légifrance de type LEGIARTI qui relie l'article à BigQuery.

## Alternatives

- Maintenir BigQuery et Neo4j comme sources de vérité indépendantes.
- Alimenter séparément BigQuery et Neo4j à partir du même JSON brut.
- Représenter BigQuery comme un nœud du graphe.

## Conséquences

- Les données curées sont centralisées dans BigQuery et Neo4j en est une projection.
- Le graphe peut être resynchronisé depuis les tables curées.
- La synchronisation vers Neo4j dépend du passage préalable des données par BigQuery.
- Les identifiants Légifrance relient les articles du graphe aux données d'article dans BigQuery.

## Statut

Accepté