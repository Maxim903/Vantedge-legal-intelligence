select
    cast(article_version_id as string) as article_version_id,
    cast(article_id as string) as article_id,
    cast(date_debut as date) as date_debut,
    cast(date_fin as date) as date_fin,
    cast(etat as string) as etat,
    cast(texte as string) as texte,
    cast(texte_ref as string) as texte_ref,
    cast(date_chargement as date) as date_chargement
from {{ source('raw', 'article_versions') }}
where article_version_id is not null
qualify row_number() over (
    partition by article_version_id
    order by date_chargement desc
) = 1
