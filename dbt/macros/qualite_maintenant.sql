{% macro qualite_maintenant() -%}
    {{ dbt.current_timestamp() }}
{%- endmacro %}
