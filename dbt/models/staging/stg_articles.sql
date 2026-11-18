select
    cast(article_id as string) as article_id,
    cast(code_id as string) as code_id,
    cast(livre_id as string) as livre_id,
    cast(livre as string) as livre,
    cast(titre_id as string) as titre_id,
    cast(titre as string) as titre,
    cast(chapitre_id as string) as chapitre_id,
    cast(chapitre as string) as chapitre,
    cast(numero as string) as numero,
    cast(date_chargement as date) as date_chargement
from {{ source('raw', 'articles') }}
where article_id is not null
qualify row_number() over (
    partition by article_id
    order by date_chargement desc
) = 1
