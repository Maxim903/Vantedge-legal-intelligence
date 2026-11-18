-- Un parent par livre : celui qui regroupe le plus d'articles.
with candidats as (
    select
        livre_id as legifrance_id,
        code_id as parent_legifrance_id,
        any_value(livre) as libelle,
        count(*) as nb_articles
    from {{ ref('stg_articles') }}
    where livre_id is not null and code_id is not null
    group by livre_id, code_id
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
    {{ dbt_utils.generate_surrogate_key(['legifrance_id']) }} as livre_id,
    {{ dbt_utils.generate_surrogate_key(['parent_legifrance_id']) }} as code_id,
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
