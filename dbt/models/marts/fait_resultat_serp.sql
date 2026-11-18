{{ config(
    partition_by={'field': 'date_resultat', 'data_type': 'date'}
) }}

select
    requetes.requete_id,
    contextes.pays_langue_id,
    serp.date_archive as date_resultat,
    serp.rang_absolu as position,
    serp.domaine,
    serp.url,
    serp.archive_blob as source_payload
from (
    select *, {{ pays_localisation('localisation') }} as pays
    from {{ ref('stg_serp') }}
) as serp
inner join {{ ref('dim_pays_langue') }} as contextes
    on serp.pays = contextes.pays and serp.langue = contextes.langue
inner join {{ ref('dim_requete') }} as requetes
    on serp.requete = requetes.texte
    and contextes.pays_langue_id = requetes.pays_langue_id
