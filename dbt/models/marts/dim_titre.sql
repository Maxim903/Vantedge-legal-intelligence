-- Un parent par titre : celui qui regroupe le plus d'articles.
with candidats as (
    select
        titre_id as legifrance_id,
        livre_id as parent_legifrance_id,
        any_value(titre) as libelle,
        count(*) as nb_articles
    from {{ ref('stg_articles') }}
    where titre_id is not null and livre_id is not null
    group by titre_id, livre_id
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
    {{ dbt_utils.generate_surrogate_key(['legifrance_id']) }} as titre_id,
    {{ dbt_utils.generate_surrogate_key(['parent_legifrance_id']) }} as livre_id,
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
