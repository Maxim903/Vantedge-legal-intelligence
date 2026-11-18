WITH sources AS (
  SELECT DISTINCT version.article_id
  FROM `marts.fait_extraction` AS extraction
  JOIN `marts.dim_article_version` AS version
    ON version.article_version_id = extraction.article_version_id
  WHERE extraction.notion_id = @notion_id
),
candidates AS (
SELECT
  article.article_id,
  article.numero,
  version.article_version_id,
  version.etat,
  CAST(version.date_debut AS STRING) AS date_debut,
  CAST(version.date_fin AS STRING) AS date_fin,
  version.etat = 'VIGUEUR'
    AND version.date_debut <= CURRENT_DATE()
    AND (version.date_fin IS NULL OR version.date_fin >= CURRENT_DATE()) AS en_vigueur
FROM sources
JOIN `marts.dim_article` AS article ON article.article_id = sources.article_id
JOIN `marts.dim_chapitre` AS chapitre ON chapitre.chapitre_id = article.chapitre_id
JOIN `marts.dim_titre` AS titre ON titre.titre_id = chapitre.titre_id
JOIN `marts.dim_livre` AS livre ON livre.livre_id = titre.livre_id
JOIN `marts.dim_code` AS code ON code.code_id = livre.code_id
JOIN `marts.dim_article_version` AS version ON version.article_id = article.article_id
WHERE code.legifrance_id = 'LEGITEXT000006072050'
)
SELECT *
FROM candidates
QUALIFY ROW_NUMBER() OVER (
  PARTITION BY article_id
  ORDER BY en_vigueur DESC, date_debut DESC, article_version_id DESC
) = 1
ORDER BY numero, article_id
