{# Utilise le schéma personnalisé tel quel (staging, marts) au lieu de le préfixer
   par le dataset du profil. #}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {{ custom_schema_name | trim if custom_schema_name is not none else target.schema }}
{%- endmacro %}
