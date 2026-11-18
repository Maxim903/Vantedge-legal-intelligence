{#
    Score d'écart v1 (docs/03-donnees/score-ecart.md), calculé à la date du jour, par
    notion, code juridique et pays/langue. Cohorte de normalisation percentile : toutes
    les notions calculables d'un même code et d'un même pays/langue. livre_id reste NULL
    (périmètre = code entier).

    Écarts par rapport à la doc, faute de données dans le projet :
    - A(q), autorité des domaines du top 10 : proxy de concentration,
      100 * (1 - domaines distincts / résultats) sur les 10 premières positions de la
      dernière SERP. Moins il y a de domaines distincts, plus la SERP est saturée.
    - G(n), centralité : degré de la notion, soit le nombre d'articles distincts
      extraits pour la notion (toutes versions) plus le nombre de situations de vie
      distinctes.
    - N(n) : articles distincts du code dont la version est en vigueur à la date de calcul.
    - T(n) : une requête sans intention connue compte pour 0 mais reste au dénominateur.
    - Seules les notions disposant d'un volume (12 derniers mois complets), d'une
      concurrence et d'une SERP sont calculables ; les autres ne produisent pas de ligne.
#}
{% set version_score = 'v1' %}

with parametres as (
    select current_date() as date_calcul
),

fenetre as (
    select
        date_sub(date_trunc(date_calcul, month), interval 12 month) as debut,
        date_trunc(date_calcul, month) as fin
    from parametres
),

rattachements as (
    select
        liens.notion_id,
        liens.requete_id,
        liens.score_rattachement as poids,
        requetes.pays_langue_id,
        coalesce(requetes.intention_type in ('transactionnelle', 'commerciale'), false)
            as est_transactionnelle
    from {{ ref('fait_notion_requete') }} as liens
    inner join {{ ref('dim_requete') }} as requetes using (requete_id)
    where liens.score_rattachement > 0
),

volumes as (
    select requete_id, pays_langue_id, avg(volume) as volume_moyen, avg(concurrence) as concurrence
    from {{ ref('fait_metrique_mensuelle') }}
    cross join fenetre
    where mois >= fenetre.debut and mois < fenetre.fin
    group by requete_id, pays_langue_id
),

autorite_serp as (
    select
        requete_id,
        pays_langue_id,
        100 * (1 - count(distinct domaine) / count(*)) as autorite
    from {{ ref('fait_resultat_serp') }}
    where position <= 10 and domaine is not null
    group by requete_id, pays_langue_id, date_resultat
    qualify date_resultat = max(date_resultat) over (partition by requete_id, pays_langue_id)
),

demande_marche as (
    select
        rattachements.notion_id,
        rattachements.pays_langue_id,
        sum(poids * volume_moyen) / sum(poids) as demande_brute,
        sum(poids * concurrence) / sum(poids) as concurrence_brute
    from rattachements
    inner join volumes using (requete_id, pays_langue_id)
    where volume_moyen is not null and concurrence is not null
    group by notion_id, pays_langue_id
),

autorite_marche as (
    select
        rattachements.notion_id,
        rattachements.pays_langue_id,
        sum(poids * autorite) / sum(poids) as autorite_brute
    from rattachements
    inner join autorite_serp using (requete_id, pays_langue_id)
    group by notion_id, pays_langue_id
),

transactionnel as (
    select
        notion_id,
        pays_langue_id,
        100 * sum(if(est_transactionnelle, poids, 0)) / sum(poids) as part_transactionnelle
    from rattachements
    group by notion_id, pays_langue_id
),

situations as (
    select notion_id, count(distinct situation_id) as nb_situations
    from {{ ref('fait_extraction') }}
    group by notion_id
),

articles_par_code as (
    select
        extractions.notion_id,
        livres.code_id,
        count(distinct articles.article_id) as nb_articles_lies,
        count(distinct if(
            versions.etat = 'VIGUEUR'
                and versions.date_debut <= parametres.date_calcul
                and (versions.date_fin is null or versions.date_fin >= parametres.date_calcul),
            articles.article_id,
            null
        )) as nb_articles_en_vigueur
    from {{ ref('fait_extraction') }} as extractions
    inner join {{ ref('dim_article_version') }} as versions using (article_version_id)
    inner join {{ ref('dim_article') }} as articles on versions.article_id = articles.article_id
    inner join {{ ref('dim_chapitre') }} as chapitres on articles.chapitre_id = chapitres.chapitre_id
    inner join {{ ref('dim_titre') }} as titres on chapitres.titre_id = titres.titre_id
    inner join {{ ref('dim_livre') }} as livres on titres.livre_id = livres.livre_id
    cross join parametres
    group by extractions.notion_id, livres.code_id
),

base as (
    select
        demande_marche.notion_id,
        articles_par_code.code_id,
        demande_marche.pays_langue_id,
        demande_marche.demande_brute,
        demande_marche.concurrence_brute,
        autorite_marche.autorite_brute,
        articles_par_code.nb_articles_en_vigueur,
        articles_par_code.nb_articles_lies + coalesce(situations.nb_situations, 0) as degre,
        transactionnel.part_transactionnelle
    from demande_marche
    inner join autorite_marche using (notion_id, pays_langue_id)
    inner join transactionnel using (notion_id, pays_langue_id)
    inner join articles_par_code using (notion_id)
    left join situations using (notion_id)
),

indices as (
    select
        *,
        count(*) over (partition by code_id, pays_langue_id) as taille_cohorte,
        {{ gap_percentile('demande_brute', 'code_id, pays_langue_id') }} as indice_demande,
        {{ gap_percentile('concurrence_brute', 'code_id, pays_langue_id') }} as p_concurrence,
        {{ gap_percentile('autorite_brute', 'code_id, pays_langue_id') }} as p_autorite,
        {{ gap_percentile('nb_articles_en_vigueur', 'code_id, pays_langue_id') }} as p_articles,
        {{ gap_percentile('degre', 'code_id, pays_langue_id') }} as p_centralite
    from base
),

scores as (
    select
        *,
        {{ gap_saturation('p_concurrence', 'p_autorite') }} as indice_saturation,
        {{ gap_importance('p_articles', 'p_centralite') }} as indice_importance_normative
    from indices
)

select
    {{ dbt_utils.generate_surrogate_key([
        'notion_id', "'" ~ version_score ~ "'", 'parametres.date_calcul',
        'code_id', 'cast(null as string)', 'pays_langue_id'
    ]) }} as gap_score_id,
    notion_id,
    code_id,
    cast(null as string) as livre_id,
    pays_langue_id,
    parametres.date_calcul,
    '{{ version_score }}' as version_score,
    cast(indice_demande as float64) as indice_demande,
    cast(indice_saturation as float64) as indice_saturation,
    cast(indice_importance_normative as float64) as indice_importance_normative,
    cast({{ gap_ecart('indice_demande', 'indice_saturation') }} as float64) as score_ecart,
    cast({{ gap_criticite('indice_importance_normative', 'part_transactionnelle') }} as float64)
        as criticite_semantique,
    taille_cohorte
from scores
cross join parametres
