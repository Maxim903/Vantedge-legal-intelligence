# ADR-0001 : Persistance polyglotte

## Contexte

Le produit doit gérer des données transactionnelles, analytiques, de graphe et des payloads bruts immuables. Ces besoins relèvent de responsabilités distinctes.

## Décision

Adopter une persistance polyglotte avec des responsabilités séparées : Supabase (PostgreSQL) pour l'OLTP, BigQuery comme entrepôt analytique, Neo4j pour le graphe de connaissances et Google Cloud Storage pour les payloads JSON bruts DataForSEO.

## Alternatives

- Utiliser une base de données unique pour les usages transactionnels, analytiques et graphe.
- Stocker les payloads bruts dans l'entrepôt analytique plutôt que dans un stockage d'objets.

Ces options ne séparent pas les responsabilités adaptées à chaque type de stockage.

## Conséquences

- Chaque composant utilise le système adapté à son rôle.
- Les données et traitements doivent être synchronisés entre plusieurs systèmes.
- Les payloads DataForSEO sont archivés tels quels dans GCS et ne sont jamais modifiés.
- Les ressources sont hébergées dans une région européenne.

## Statut

Accepté