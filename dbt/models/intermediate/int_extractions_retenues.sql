-- Extractions exploitables : statut retenu et confiance strictement au-dessus du seuil.
select
    extraction_id,
    article_version_id,
    notion_libelle,
    situation_de_vie,
    score_confiance,
    modele_llm,
    version_prompt,
    extrait_le,
    statut_validation,
    {{ notion_id('notion_libelle') }} as notion_id,
    case
        when situation_de_vie is null or trim(situation_de_vie) = '' then null
        else {{ normaliser_requete('situation_de_vie') }}
    end as situation_normalisee
from {{ ref('stg_extractions') }}
where statut_validation in (
        {%- for statut in var('statuts_notions_retenus') %}'{{ statut }}'{{ ', ' if not loop.last }}{% endfor -%}
    )
    and score_confiance > {{ var('seuil_confiance') }}
    and notion_libelle is not null
    and trim(notion_libelle) != ''
