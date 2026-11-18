ALTER TABLE `raw.article_versions`
ADD COLUMN IF NOT EXISTS texte STRING;
