{# Reproduit jobs/build_seed_queries.py::_notion_id : normalisation des espaces et
   de la casse, singularisation mot à mot (« -eaux » → « -eau », « -s » sauf
   « -ss », « -us », « -is », mots de plus de 3 lettres), retrait des accents, SHA-256. #}
{% macro notion_id(libelle) -%}
to_hex(sha256(
    regexp_replace(
        normalize(
            regexp_replace(
                regexp_replace(
                    {{ normaliser_requete(libelle) }},
                    r'\b(\pL+)eaux\b', r'\1eau'
                ),
                r'\b(\pL{2,}[^\P{L}siu])s\b', r'\1'
            ),
            NFKD
        ),
        r'\pM', ''
    )
))
{%- endmacro %}
