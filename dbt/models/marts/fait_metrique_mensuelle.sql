{{ config(
    partition_by={'field': 'mois', 'data_type': 'date', 'granularity': 'month'}
) }}

-- cpc et concurrence viennent de la dernière archive et s'appliquent à chaque mois
-- de l'historique ; seul le volume est mensuel. concurrence = indice DataForSEO / 100.
with metriques as (
    select
        requete,
        {{ pays_localisation('localisation') }} as pays,
        langue,
        volumes_mensuels,
        cpc,
        indice_concurrence / 100 as concurrence,
        archive_blob
    from {{ ref('stg_metriques') }}
)

select
    requetes.requete_id,
    contextes.pays_langue_id,
    date(mensuel.annee, mensuel.mois, 1) as mois,
    mensuel.volume,
    metriques.cpc,
    metriques.concurrence,
    metriques.archive_blob as source_payload
from metriques
cross join unnest(metriques.volumes_mensuels) as mensuel
inner join {{ ref('dim_pays_langue') }} as contextes
    on metriques.pays = contextes.pays and metriques.langue = contextes.langue
inner join {{ ref('dim_requete') }} as requetes
    on metriques.requete = requetes.texte
    and contextes.pays_langue_id = requetes.pays_langue_id
where mensuel.annee is not null and mensuel.mois is not null
