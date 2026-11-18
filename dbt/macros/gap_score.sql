{# Formules v1 de docs/03-donnees/score-ecart.md, partagées par fait_gap_score et son test. #}

{# Rang percentile (0-100) avec rang moyen en cas d'ex æquo ; 50 si une seule observation. #}
{% macro gap_percentile(valeur, cohorte) -%}
    case
        when count(*) over (partition by {{ cohorte }}) = 1 then 50.0
        else 100 * (
            -- rang moyen = moyenne du rang minimal et du rang maximal du groupe d'ex æquo
            (
                rank() over (partition by {{ cohorte }} order by {{ valeur }})
                + count(*) over (partition by {{ cohorte }} order by {{ valeur }})
            ) / 2
            - 1
        ) / (count(*) over (partition by {{ cohorte }}) - 1)
    end
{%- endmacro %}

{% macro gap_percentile_depuis_rang(rang, n) -%}
    (100 * ({{ rang }} - 1) / ({{ n }} - 1))
{%- endmacro %}

{% macro gap_saturation(p_concurrence, p_autorite) -%}
    (0.5 * {{ p_concurrence }} + 0.5 * {{ p_autorite }})
{%- endmacro %}

{% macro gap_importance(p_articles, p_centralite) -%}
    (0.5 * {{ p_articles }} + 0.5 * {{ p_centralite }})
{%- endmacro %}

{% macro gap_ecart(demande, saturation) -%}
    ({{ demande }} * (1 - {{ saturation }} / 100))
{%- endmacro %}

{% macro gap_criticite(importance, part_transactionnelle) -%}
    (0.5 * {{ importance }} + 0.5 * {{ part_transactionnelle }})
{%- endmacro %}
