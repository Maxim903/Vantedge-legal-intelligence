-- Périmètre aligné sur dim_notion : seules les extractions retenues (statut et seuil de confiance).
select
    extractions.extraction_id,
    extractions.article_version_id,
    extractions.notion_id,
    case
        when extractions.situation_normalisee is not null
            then {{ dbt_utils.generate_surrogate_key(['extractions.situation_normalisee']) }}
    end as situation_id,
    extractions.score_confiance,
    modeles.modele_prompt_id,
    extractions.extrait_le,
    extractions.statut_validation,
    brut.valide_par
from {{ ref('int_extractions_retenues') }} as extractions
inner join {{ ref('stg_extractions') }} as brut
    on extractions.extraction_id = brut.extraction_id
left join {{ ref('ref_modele_prompt') }} as modeles
    on extractions.modele_llm = modeles.modele_llm
    and extractions.version_prompt = modeles.prompt_hash
