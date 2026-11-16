with volumes as (
    select
        {{ normaliser_requete('mot_cle') }} as requete,
        cast(localisation as int64) as localisation,
        cast(langue as string) as langue,
        cast(volume as int64) as volume,
        cast(concurrence as string) as concurrence,
        cast(indice_concurrence as int64) as indice_concurrence,
        cast(cpc as float64) as cpc,
        cast(cpc_bas as float64) as cpc_bas,
        cast(cpc_haut as float64) as cpc_haut,
        volumes_mensuels,
        cast(date_archive as date) as date_archive,
        archive_blob
    from {{ source('raw', 'dataforseo_volumes') }}
    where mot_cle is not null
)

select
    {{ dbt_utils.generate_surrogate_key(['requete']) }} as requete_id,
    requete,
    localisation,
    langue,
    volume,
    concurrence,
    indice_concurrence,
    cpc,
    cpc_bas,
    cpc_haut,
    volumes_mensuels,
    date_archive,
    archive_blob
from volumes
qualify row_number() over (
    partition by requete, localisation, langue
    order by date_archive desc, archive_blob desc
) = 1
