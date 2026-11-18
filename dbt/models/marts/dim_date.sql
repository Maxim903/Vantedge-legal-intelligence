with calendrier as (
    {{ dbt_utils.date_spine(
        datepart='day',
        start_date="cast('2020-01-01' as date)",
        end_date="cast('2036-01-01' as date)"
    ) }}
)

select
    cast(date_day as date) as date_id,
    extract(day from date_day) as jour,
    extract(month from date_day) as mois,
    extract(year from date_day) as annee
from calendrier
