with codes as (
    select distinct code_id as legifrance_id
    from {{ ref('stg_articles') }}
    where code_id is not null
)

select
    {{ dbt_utils.generate_surrogate_key(['codes.legifrance_id']) }} as code_id,
    codes.legifrance_id,
    coalesce(seed.libelle, codes.legifrance_id) as libelle,
    cast(
        coalesce(
            seed.ordre,
            row_number() over (order by codes.legifrance_id) + 1000
        ) as int64
    ) as ordre
from codes
left join {{ ref('codes') }} as seed
    on codes.legifrance_id = seed.legifrance_id
