select
    article_id,
    case
        when chapitre_id is null then null
        else {{ dbt_utils.generate_surrogate_key(['chapitre_id']) }}
    end as chapitre_id,
    numero
from {{ ref('stg_articles') }}
