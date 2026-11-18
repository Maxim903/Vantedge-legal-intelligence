select
    cast(extraction_id as string) as extraction_id,
    cast(article_version_id as string) as article_version_id,
    cast(notion_libelle as string) as notion_libelle,
    cast(situation_de_vie as string) as situation_de_vie,
    cast(score_confiance as float64) as score_confiance,
    cast(modele_llm as string) as modele_llm,
    cast(version_prompt as string) as version_prompt,
    cast(extrait_le as timestamp) as extrait_le,
    cast(statut_validation as string) as statut_validation,
    cast(valide_par as string) as valide_par
from {{ source('raw', 'entites_extraites') }}
where extraction_id is not null
qualify row_number() over (
    partition by extraction_id
    order by extrait_le desc
) = 1
