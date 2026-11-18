{#
    LIMITE : les liens entre articles (renvois, modifications, abrogations) ne sont
    pas encore chargés dans le dataset raw : le parseur LEGI ne lit pas les balises
    LIENS et aucune table raw.* ne les contient. Ce modèle produit donc une table
    vide mais correctement typée. Quand raw.article_liens existera (colonnes
    article_source_id, type_relation, article_cible_id), remplacer le corps par une
    lecture de cette source, filtrée sur les trois types et sur les articles présents
    dans dim_article, dédupliquée sur la clé composite.
#}
select
    cast(null as string) as article_source_id,
    cast(null as string) as type_relation,
    cast(null as string) as article_cible_id
from (select 1)
where false
