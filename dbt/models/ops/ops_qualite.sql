with horloge as (
    select {{ qualite_maintenant() }} as maintenant
),

notions_sans_requete as (
    select
        'notion_sans_requete' as type_controle,
        notions.notion_id,
        cast(null as string) as requete_id,
        cast(null as string) as pays_langue_id,
        notions.libelle,
        cast(null as date) as derniere_collecte_volume,
        cast(null as int64) as nombre_quarantaine,
        cast(null as int64) as nombre_extractions,
        cast(null as float64) as taux_quarantaine
    from {{ ref('dim_notion') }} as notions
    where not exists (
        select 1
        from {{ ref('fait_notion_requete') }} as liens
        where liens.notion_id = notions.notion_id
    )
),

volumes as (
    select
        {{ normaliser_requete('mot_cle') }} as texte,
        {{ pays_localisation('localisation') }} as pays,
        langue,
        max(date_archive) as derniere_collecte_volume
    from {{ source('raw', 'dataforseo_volumes') }}
    cross join horloge
    where mot_cle is not null
        and volume > 0
        and date_archive <= date(horloge.maintenant)
    group by texte, pays, langue
),

requetes_sans_volume as (
    select
        'requete_sans_volume_60j' as type_controle,
        cast(null as string) as notion_id,
        requetes.requete_id,
        requetes.pays_langue_id,
        requetes.texte as libelle,
        volumes.derniere_collecte_volume,
        cast(null as int64) as nombre_quarantaine,
        cast(null as int64) as nombre_extractions,
        cast(null as float64) as taux_quarantaine
    from {{ ref('dim_requete') }} as requetes
    inner join {{ ref('dim_pays_langue') }} as contextes
        on requetes.pays_langue_id = contextes.pays_langue_id
    left join volumes
        on requetes.texte = volumes.texte
        and contextes.pays = volumes.pays
        and contextes.langue = volumes.langue
    cross join horloge
    where volumes.derniere_collecte_volume is null
        or volumes.derniere_collecte_volume <= date_sub(
            date(horloge.maintenant), interval 60 day
        )
),

quarantaine as (
    select
        countif(extractions.statut = 'QUARANTINE') as nombre_quarantaine,
        count(*) as nombre_extractions
    from {{ source('ops', 'extraction_results') }} as extractions
    cross join horloge
    where extractions.extrait_le >= timestamp_sub(horloge.maintenant, interval 60 day)
        and extractions.extrait_le <= horloge.maintenant
)

select * from notions_sans_requete
union all
select * from requetes_sans_volume
union all
select
    'taux_quarantaine_60j' as type_controle,
    cast(null as string) as notion_id,
    cast(null as string) as requete_id,
    cast(null as string) as pays_langue_id,
    cast(null as string) as libelle,
    cast(null as date) as derniere_collecte_volume,
    nombre_quarantaine,
    nombre_extractions,
    safe_divide(nombre_quarantaine, nombre_extractions) as taux_quarantaine
from quarantaine
