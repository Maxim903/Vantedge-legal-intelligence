select
    {{ dbt_utils.generate_surrogate_key([normaliser_requete('requete')]) }}
        as requete_id,
    {{ normaliser_requete('requete') }} as requete,
    cast(intention_type as string) as intention_type,
    cast(score_confiance as float64) as score_confiance,
    cast(methode as string) as methode,
    cast(date_classification as date) as date_classification
from {{ source('raw', 'requetes_intentions') }}
where requete is not null and trim(requete) != ''
qualify row_number() over (
    partition by {{ normaliser_requete('requete') }}
    order by date_classification desc
) = 1
