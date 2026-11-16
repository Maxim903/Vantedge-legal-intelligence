{{ config(
    partition_by={'field': 'date_cout', 'data_type': 'date'}
) }}

select
    cast(cout_id as string) as cout_id,
    cast(lot_id as string) as lot_id,
    cast(fournisseur as string) as fournisseur,
    cast(service as string) as service,
    cast(date_cout as date) as date_cout,
    cast(montant as numeric) as montant,
    cast(devise as string) as devise,
    details
from {{ source('ops', 'couts_api') }}
