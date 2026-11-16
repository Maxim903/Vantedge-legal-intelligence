select distinct
    notion_id,
    {{ dbt_utils.generate_surrogate_key(['situation_normalisee']) }} as situation_id
from {{ ref('int_extractions_retenues') }}
where situation_normalisee is not null
