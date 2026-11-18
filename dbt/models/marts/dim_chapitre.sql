-- Un parent par chapitre : celui qui regroupe le plus d'articles.
with candidats as (
    select
        chapitre_id as legifrance_id,
        titre_id as parent_legifrance_id,
        any_value(chapitre) as libelle,
        count(*) as nb_articles
    from {{ ref('stg_articles') }}
    where chapitre_id is not null and titre_id is not null
    group by chapitre_id, titre_id
),

retenus as (
    select *
    from candidats
    qualify row_number() over (
        partition by legifrance_id
        order by nb_articles desc, parent_legifrance_id
    ) = 1
)

select
    {{ dbt_utils.generate_surrogate_key(['legifrance_id']) }} as chapitre_id,
    {{ dbt_utils.generate_surrogate_key(['parent_legifrance_id']) }} as titre_id,
    legifrance_id,
    libelle,
    coalesce(
        {{ ordre_romain('libelle') }},
        cast(
            row_number() over (
                partition by parent_legifrance_id order by legifrance_id
            ) + 1000 as int64
        )
    ) as ordre
from retenus
