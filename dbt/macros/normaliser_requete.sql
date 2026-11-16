{% macro normaliser_requete(colonne) -%}
lower(trim(regexp_replace({{ colonne }}, r'\s+', ' ')))
{%- endmacro %}
