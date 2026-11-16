{# Échoue pour chaque paire de lignes d'un même article dont les périodes
   [debut, fin[ se chevauchent : à une date donnée, une seule version est active.
   Une fin NULL signifie une période ouverte. #}
{% test periodes_sans_chevauchement(model, key_column, partition_column, start_column, end_column) %}

select
    a.{{ partition_column }},
    a.{{ key_column }} as cle_a,
    b.{{ key_column }} as cle_b
from {{ model }} as a
inner join {{ model }} as b
    on a.{{ partition_column }} = b.{{ partition_column }}
    and a.{{ key_column }} < b.{{ key_column }}
where a.{{ start_column }} < coalesce(b.{{ end_column }}, date '9999-12-31')
    and b.{{ start_column }} < coalesce(a.{{ end_column }}, date '9999-12-31')

{% endtest %}
