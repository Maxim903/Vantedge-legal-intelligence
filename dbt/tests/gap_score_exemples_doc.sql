-- Recalcule les 3 exemples de docs/03-donnees/score-ecart.md avec les macros du modèle.
-- Les percentiles hypothétiques de la doc sont des entrées ; D_brut et D sont recalculés.
with requetes as (
    select 1 as exemple, 1200.0 as volume, 0.8 as poids union all
    select 1, 500, 0.4 union all
    select 2, 5000, 1.0 union all
    select 2, 3000, 0.5 union all
    select 3, 100, 1.0 union all
    select 3, 50, 1.0
),

demande as (
    select exemple, sum(volume * poids) / sum(poids) as demande_brute
    from requetes
    group by exemple
),

entrees as (
    select 1 as exemple, 81 as rang, 20 as p_c, 30 as p_a, 70 as p_n, 50 as p_g, 60 as t union all
    select 2, 91, 80, 90, 90, 80, 75 union all
    select 3, 21, 10, 30, 40, 20, 20
),

attendu as (
    select 1 as exemple, 966.6666667 as demande_brute, 80 as d, 25 as s, 60 as ecart, 60 as i, 60 as criticite union all
    select 2, 4333.3333333, 90, 85, 13.5, 85, 80 union all
    select 3, 75, 20, 20, 16, 30, 25
),

calcule as (
    select
        entrees.exemple,
        demande.demande_brute,
        {{ gap_percentile_depuis_rang('entrees.rang', 101) }} as d,
        {{ gap_saturation('entrees.p_c', 'entrees.p_a') }} as s,
        {{ gap_importance('entrees.p_n', 'entrees.p_g') }} as i,
        entrees.t
    from entrees
    inner join demande using (exemple)
),

final as (
    select
        *,
        {{ gap_ecart('d', 's') }} as ecart,
        {{ gap_criticite('i', 't') }} as criticite
    from calcule
)

select final.exemple
from final
inner join attendu using (exemple)
where abs(final.demande_brute - attendu.demande_brute) > 0.001
    or abs(final.d - attendu.d) > 1e-6
    or abs(final.s - attendu.s) > 1e-6
    or abs(final.ecart - attendu.ecart) > 1e-6
    or abs(final.i - attendu.i) > 1e-6
    or abs(final.criticite - attendu.criticite) > 1e-6
