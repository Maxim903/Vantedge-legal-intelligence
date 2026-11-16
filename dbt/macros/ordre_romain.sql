{# Extrait le numéro d'ordre (chiffres romains) d'un libellé « Livre III : … »,
   « Titre Ier : … » ou « Chapitre IV : … ». NULL si le libellé n'en contient pas. #}
{% macro ordre_romain(libelle) -%}
case regexp_extract(upper({{ libelle }}), r'^(?:LIVRE|TITRE|CHAPITRE)\s+([IVXL]+)')
{%- set dizaines = ['', 'X', 'XX', 'XXX', 'XL', 'L', 'LX', 'LXX', 'LXXX', 'XC'] %}
{%- set unites = ['', 'I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX'] %}
{%- for d in range(0, 10) %}{% for u in range(0, 10) %}{% if d + u > 0 %}
    when '{{ dizaines[d] }}{{ unites[u] }}' then {{ d * 10 + u }}
{%- endif %}{% endfor %}{% endfor %}
end
{%- endmacro %}
