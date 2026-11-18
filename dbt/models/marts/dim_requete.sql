-- Une requête est identifiée par son texte et son contexte pays/langue.
-- Le MVP ne couvre que France/fr : toutes les requêtes reçoivent ce contexte.
with texte as (
    select requete as texte from {{ ref('stg_requetes') }}
    union distinct
    select requete from {{ ref('stg_intentions') }}
),

contexte as (
    select pays_langue_id, pays, langue
    from {{ ref('dim_pays_langue') }}
    where pays = 'FR' and langue = 'fr'
)

select
    {{ dbt_utils.generate_surrogate_key(['texte.texte', 'contexte.pays', 'contexte.langue']) }}
        as requete_id,
    texte.texte,
    contexte.pays_langue_id,
    intentions.intention_type
from texte
cross join contexte
left join {{ ref('stg_intentions') }} as intentions
    on texte.texte = intentions.requete
