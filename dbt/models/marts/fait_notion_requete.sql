-- requete_id est celui de dim_requete (texte + pays + langue), pas celui de staging.
select
    rattachements.notion_id,
    requetes.requete_id,
    rattachements.score_rattachement
from {{ ref('stg_requetes') }} as rattachements
inner join {{ ref('dim_requete') }} as requetes
    on rattachements.requete = requetes.texte
inner join {{ ref('dim_notion') }} as notions
    on rattachements.notion_id = notions.notion_id
