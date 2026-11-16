with serp as (
    select
        {{ normaliser_requete('mot_cle') }} as requete,
        cast(localisation as int64) as localisation,
        cast(langue as string) as langue,
        cast(type_resultat as string) as type_resultat,
        cast(rang_groupe as int64) as rang_groupe,
        cast(rang_absolu as int64) as rang_absolu,
        cast(domaine as string) as domaine,
        cast(titre as string) as titre,
        cast(url as string) as url,
        cast(date_archive as date) as date_archive,
        archive_blob
    from {{ source('raw', 'dataforseo_serp') }}
    where mot_cle is not null and rang_absolu is not null
),

-- Conserve toutes les lignes de la dernière archive de chaque requête.
derniere_archive as (
    select *
    from serp
    qualify rank() over (
        partition by requete, localisation, langue
        order by date_archive desc, archive_blob desc
    ) = 1
)

select
    {{ dbt_utils.generate_surrogate_key(['requete']) }} as requete_id,
    {{ dbt_utils.generate_surrogate_key(
        ['requete', 'localisation', 'langue', 'rang_absolu']
    ) }} as resultat_serp_id,
    *
from derniere_archive
qualify row_number() over (
    partition by requete, localisation, langue, rang_absolu
    order by rang_groupe
) = 1
