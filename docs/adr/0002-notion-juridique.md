# ADR-0002 : Employer « Notion juridique »

## Contexte

Le terme « Entité juridique » désigne en droit français une personne morale, par exemple une SAS ou une association. Son emploi pour un concept de droit crée une ambiguïté.

## Décision

Renommer « Entité juridique » en « Notion juridique » et nommer `:Notion` le nœud correspondant dans Neo4j.

## Alternatives

- Conserver « Entité juridique », au risque de confondre un concept de droit avec une personne morale.
- Employer une autre terminologie, au prix d'un écart avec la terminologie retenue dans le modèle.

## Conséquences

- Le terme « Notion juridique » désigne le concept de droit identifié dans les articles.
- Le modèle du graphe utilise le label `:Notion`.
- Les schémas, données et interfaces doivent employer cette terminologie de façon cohérente.

## Statut

Accepté