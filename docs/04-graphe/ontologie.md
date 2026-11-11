# Ontologie du graphe de connaissances

## Vue d'ensemble

Le nœud pivot est la `Notion` juridique. Elle se fonde sur des articles (norme) et s'exprime par des requêtes web (marché). Les métriques et intentions sont portées par la `Requete`, non par la notion.

Le graphe est global et en lecture seule pour les utilisateurs. Les projets et données des utilisateurs restent dans Supabase ; aucune donnée personnelle n'entre dans Neo4j.

## Nœuds, propriétés et clés d'unicité

| Nœud | Propriétés principales | Clé d'unicité du modèle |
|---|---|---|
| `Code`, `Livre`, `Titre` | `libelle`, `ordre` | Identifiant Légifrance |
| `Article` | `numero`, `etat`, `date_debut`, `date_fin`, `texte_ref` (pointeur BigQuery) | `article_id` (LEGIARTI…) |
| `Notion` | `libelle`, `definition_courte`, `score_confiance` | `notion_id` |
| `SituationDeVie` | `libelle` | `situation_id` |
| `Requete` | `texte`, `langue`, `pays` | `requete_id` (hash) |
| `Intention` | `type` (informationnelle, transactionnelle, navigationnelle, commerciale) | `type` |
| `Metrique` | `mois`, `volume`, `cpc`, `concurrence` | `requete_id` + `mois` |
| `ResultatSERP` | `domaine`, `url`, `position`, `date` | `requete_id` + `date` + `position` |

### Contraintes d'unicité explicites dans l'annexe B

L'annexe B définit les contraintes Neo4j suivantes :

| Nœud | Propriété contrainte |
|---|---|
| `Article` | `article_id` |
| `Notion` | `notion_id` |
| `SituationDeVie` | `situation_id` |
| `Requete` | `requete_id` |
| `Intention` | `type` |

Les clés d'unicité du tableau de modèle pour `Code`, `Livre`, `Titre`, `Metrique` et `ResultatSERP` ne sont pas définies par une contrainte Cypher dans l'annexe B.

## Relations

Convention : MAJUSCULES, sans accents, accord correct.

| Relation | Sens |
|---|---|
| `(:Notion)-[:SE_FONDE_SUR]->(:Article)` | La notion trouve son fondement dans l'article. |
| `(:Notion)-[:APPARTIENT_A]->(:SituationDeVie)` | Rattachement à une situation de vie. |
| `(:Notion)-[:EST_EXPRIMEE_PAR {score}]->(:Requete)` | La requête exprime la notion (score de rattachement). |
| `(:Requete)-[:A_POUR_INTENTION]->(:Intention)` | Intention de recherche dominante. |
| `(:Requete)-[:A_POUR_METRIQUE]->(:Metrique)` | Une métrique par mois. |
| `(:Requete)-[:A_POUR_RESULTAT]->(:ResultatSERP)` | Résultats observés dans la SERP. |
| `(:Article)-[:RENVOIE_A \| MODIFIE \| ABROGE]->(:Article)` | Liens normatifs entre articles. |
| `(:Code)-[:CONTIENT]->(:Livre)-[:CONTIENT]->(:Titre)-[:CONTIENT]->(:Article)` | Hiérarchie du code. |

## Exemple de sous-graphe en texte

```text
(:Notion {notion_id})-[:SE_FONDE_SUR]->(:Article {article_id})
(:Notion)-[:APPARTIENT_A]->(:SituationDeVie {situation_id})
(:Notion)-[:EST_EXPRIMEE_PAR {score}]->(:Requete {requete_id})
(:Requete)-[:A_POUR_INTENTION]->(:Intention {type})
(:Requete)-[:A_POUR_METRIQUE]->(:Metrique {mois, volume, cpc, concurrence})
(:Requete)-[:A_POUR_RESULTAT]->(:ResultatSERP {domaine, url, position, date})
(:Article)-[:RENVOIE_A | MODIFIE | ABROGE]->(:Article)
(:Code)-[:CONTIENT]->(:Livre)-[:CONTIENT]->(:Titre)-[:CONTIENT]->(:Article)
```