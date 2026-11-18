select
    notion_id,
    -- Libellé de l'extraction la plus fiable, la plus récente en cas d'égalité.
    array_agg(notion_libelle order by score_confiance desc, extrait_le desc limit 1)[offset(0)]
        as libelle,
    cast(null as string) as definition_courte,
    max(score_confiance) as score_confiance
from {{ ref('int_extractions_retenues') }}
group by notion_id
