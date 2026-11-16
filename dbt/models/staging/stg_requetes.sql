with requetes as (
    select
        cast(notion_id as string) as notion_id,
        {{ normaliser_requete('requete') }} as requete,
        cast(score_rattachement as float64) as score_rattachement
    from {{ source('raw', 'requetes_candidates') }}
    where requete is not null and trim(requete) != ''
)

select
    {{ dbt_utils.generate_surrogate_key(['requete']) }} as requete_id,
    notion_id,
    requete,
    score_rattachement
from requetes
qualify row_number() over (
    partition by notion_id, requete
    order by score_rattachement desc
) = 1
