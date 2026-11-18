## Annexe A – Les 22 tables du schéma en flocon

Proposition de découpage du dataset marts [À valider] : 12 dimensions, 6 tables de faits, 4 tables de ponts et de référence. La hiérarchie Code → Livre → Titre → Chapitre → Article est normalisée (flocon).

| # | Table | Type | Description |
|---|---|---|---|
| 1 | dim_code | Dimension | Codes juridiques (Code du travail, Code civil…). |
| 2 | dim_livre | Dimension | Livres d'un code (rattachés à dim_code). |
| 3 | dim_titre | Dimension | Titres d'un livre. |
| 4 | dim_chapitre | Dimension | Chapitres d'un titre. |
| 5 | dim_article | Dimension | Articles (identifiant LEGIARTI stable). |
| 6 | dim_article_version | Dimension | Versions d'un article : dates, état, texte de référence. |
| 7 | dim_notion | Dimension | Notions juridiques extraites. |
| 8 | dim_situation_vie | Dimension | Situations de vie (licenciement, congé, etc.). |
| 9 | dim_requete | Dimension | Requêtes web (texte, langue, pays). |
| 10 | dim_intention | Dimension | Types d'intention de recherche. |
| 11 | dim_pays_langue | Dimension | Combinaisons pays / langue. |
| 12 | dim_date | Dimension | Calendrier (jour, mois, année). |
| 13 | fait_extraction | Fait | Extraction IA : notion, article_version, confiance, modèle, prompt. |
| 14 | fait_notion_requete | Fait | Rattachement notion / requête avec score. |
| 15 | fait_metrique_mensuelle | Fait | Volume, CPC, concurrence par requête et par mois. |
| 16 | fait_resultat_serp | Fait | Résultats SERP : domaine, URL, position, date. |
| 17 | fait_gap_score | Fait | Indices D, S, I, écart, criticité, version_score. |
| 18 | fait_cout_api | Fait | Coûts LLM et DataForSEO par lot. |
| 19 | pont_article_renvoi | Pont | Liens RENVOIE_A / MODIFIE / ABROGE entre articles. |
| 20 | pont_notion_situation | Pont | Rattachement notion / situation de vie. |
| 21 | ref_taxonomie_intention | Référence | Taxonomie et règles de classification des intentions. |
| 22 | ref_modele_prompt | Référence | Registre des modèles et versions de prompts. |

## Protection de la branche principale

- Ne jamais pousser directement sur `main` ; tout changement doit passer par une branche dédiée et une Pull Request.
- Ne fusionner une Pull Request qu'après le succès du workflow CI requis.
- Si les règles de protection GitHub ne sont pas configurées ou ne sont pas disponibles, respecter ces règles manuellement sans les contourner.