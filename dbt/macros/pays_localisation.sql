{# Expression SQL : code pays d'une localisation DataForSEO (NULL si inconnue). #}
{% macro pays_localisation(colonne) -%}
    case {{ colonne }}
        {%- for code, pays in var('localisations_pays').items() %}
        when {{ code }} then '{{ pays }}'
        {%- endfor %}
    end
{%- endmacro %}
