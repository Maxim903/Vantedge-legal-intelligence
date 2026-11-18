SELECT notion.notion_id, notion.libelle, notion.definition_courte, notion.score_confiance
FROM `marts.dim_notion` AS notion
WHERE notion.notion_id = @notion_id
  AND (
  EXISTS (
    SELECT 1
    FROM `marts.fait_extraction` AS extraction
    JOIN `marts.dim_article_version` AS version ON version.article_version_id = extraction.article_version_id
    JOIN `marts.dim_article` AS article ON article.article_id = version.article_id
    JOIN `marts.dim_chapitre` AS chapitre ON chapitre.chapitre_id = article.chapitre_id
    JOIN `marts.dim_titre` AS titre ON titre.titre_id = chapitre.titre_id
    JOIN `marts.dim_livre` AS livre ON livre.livre_id = titre.livre_id
    JOIN `marts.dim_code` AS code ON code.code_id = livre.code_id
    WHERE extraction.notion_id = notion.notion_id
      AND code.legifrance_id = 'LEGITEXT000006072050'
  )
  OR EXISTS (
    SELECT 1
    FROM `marts.fait_gap_score` AS score
    JOIN `marts.dim_code` AS code ON code.code_id = score.code_id
    JOIN `marts.dim_pays_langue` AS marche ON marche.pays_langue_id = score.pays_langue_id
    WHERE score.notion_id = notion.notion_id
      AND code.legifrance_id = 'LEGITEXT000006072050'
      AND score.livre_id IS NULL
      AND marche.pays = 'FR' AND marche.langue = 'fr'
  )
  )
LIMIT 2
