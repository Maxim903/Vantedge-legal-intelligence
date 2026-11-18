select
    article_version_id,
    article_id,
    date_debut,
    date_fin,
    etat,
    texte_ref
from {{ ref('stg_article_versions') }}
