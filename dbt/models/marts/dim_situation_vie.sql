select
    {{ dbt_utils.generate_surrogate_key(['situation_normalisee']) }} as situation_id,
    array_agg(situation_de_vie order by score_confiance desc, extrait_le desc limit 1)[offset(0)]
        as libelle
from {{ ref('int_extractions_retenues') }}
where situation_normalisee is not null
group by situation_normalisee
