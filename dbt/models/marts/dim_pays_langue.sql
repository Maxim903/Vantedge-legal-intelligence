select
    {{ dbt_utils.generate_surrogate_key(['pays', 'langue']) }} as pays_langue_id,
    pays,
    langue
from {{ ref('pays_langue') }}
