# Score d'écart et criticité sémantique

## Portée et statut des formules

Le chapitre 8 définit les dimensions, l'équation de l'écart et la criticité comme une moyenne pondérée. Il laisse les formules détaillées et les pondérations « à valider et à calibrer ». Le présent document propose une règle v1 explicite pour rendre les calculs reproductibles ; les pondérations égales et les règles de percentile restent à valider sur un échantillon de notions relues manuellement.

Les exemples ci-dessous sont illustratifs. Ils supposent un même périmètre de calcul comprenant 101 notions.

## Variables

- `n` : une notion juridique.
- `q` : une requête rattachée à la notion.
- `w(n,q)` : score de rattachement de la requête à la notion, compris entre 0 et 1.
- `V(q,m)` : volume de la requête `q` pour le mois `m`.
- `C(q)` : mesure de concurrence publicitaire associée à la requête.
- `A(q)` : autorité moyenne des domaines observés dans le top 10 de la SERP de la requête.
- `N(n)` : nombre d'articles en vigueur liés à la notion.
- `G(n)` : mesure de centralité de la notion dans le graphe ; la mesure retenue (par exemple degré ou PageRank) est fixée par version.
- `T(n)` : part des intentions transactionnelles ou commerciales des requêtes rattachées à la notion.
- `P(x)` : rang percentile de `x` dans le périmètre analysé, sur une échelle de 0 à 100.

Les mesures `C(q)` et `A(q)` sont mises sur une échelle cohérente au sein du périmètre avant leur combinaison. Les méthodes de transformation et les sources sont enregistrées dans la configuration de la version du score.

## Normalisation percentile

Les dimensions de demande, de saturation et d'importance normative sont exprimées entre 0 et 100 par rang percentile dans une cohorte comparable. La cohorte d'un calcul est définie par son périmètre juridique et marché (code ou livre, pays, langue et date de calcul). Une valeur plus élevée correspond à une demande, une saturation ou une importance plus élevée.

Pour `N` observations, en utilisant le rang moyen en cas d'ex æquo :

```text
P(x) = 100 * (rang_moyen(x) - 1) / (N - 1), si N > 1
P(x) = 50, si N = 1
```

Les ex æquo reçoivent le même rang moyen. Dans les exemples avec 101 notions sans ex æquo, le rang 81 correspond ainsi au percentile 80. Un indice dont une donnée nécessaire est manquante est marqué non calculable plutôt que complété implicitement. La taille et les limites de la cohorte sont conservées avec le résultat, car un changement de cohorte peut modifier les percentiles.

## Formules proposées

### D – Demande

Pour chaque requête, calculer le volume mensuel moyen sur les 12 derniers mois, puis pondérer par le score de rattachement :

```text
V_moyen(q) = moyenne de V(q,m) sur les 12 derniers mois
D_brut(n) = somme_q(w(n,q) * V_moyen(q)) / somme_q(w(n,q))
D(n) = P(D_brut(n))
```

Une notion sans requête rattachée avec un score exploitable n'a pas de score D calculable.

### S – Saturation

La saturation combine concurrence publicitaire et autorité des domaines du top 10. Les pondérations ne sont pas définies dans le chapitre 8 ; la proposition v1 donne un poids égal aux deux composantes :

```text
C_brut(n) = moyenne pondérée de C(q), avec les poids w(n,q)
A_brut(n) = moyenne pondérée de A(q), avec les poids w(n,q)
S(n) = 0.5 * P(C_brut(n)) + 0.5 * P(A_brut(n))
```

Un S élevé indique une forte saturation et réduit le score d'écart.

### I – Importance normative

L'importance normative combine le nombre d'articles en vigueur et la centralité de la notion dans le graphe. La proposition v1 leur donne un poids égal :

```text
I(n) = 0.5 * P(N(n)) + 0.5 * P(G(n))
```

La mesure de centralité utilisée pour `G(n)` doit être fixée et conservée dans la version du score.

### Écart

Appliquer la formule définie au chapitre 8 :

```text
Ecart(n) = D(n) * (1 - S(n) / 100)
```

L'écart varie de 0 à 100 : une demande élevée et une saturation faible donnent une opportunité plus élevée.

### Criticité sémantique

Calculer la part des intentions transactionnelles ou commerciales, pondérée par le score de rattachement, puis prendre une moyenne pondérée de cette part et de `I`. Les pondérations ne sont pas précisées dans le chapitre 8 ; la proposition v1 utilise des poids égaux :

```text
T(n) = 100 * somme_q(w(n,q) * indicatrice(intention(q) transactionnelle ou commerciale))
       / somme_q(w(n,q))
Criticite(n) = 0.5 * I(n) + 0.5 * T(n)
```

`T` et `Criticite` sont exprimés entre 0 et 100. Les scores dérivés `Ecart` et `Criticite` ne sont pas reclassés en percentiles après application de leurs formules.

## Exemples numériques

Les percentiles indiqués sont hypothétiques et calculés dans la même cohorte de 101 notions. Pour chaque exemple, `P(C_brut)` et `P(A_brut)` sont les rangs percentiles des deux composantes de saturation ; `P(N)` et `P(G)` sont ceux des composantes d'importance normative.

### 1. Demande forte et saturation faible

Deux requêtes ont des volumes mensuels moyens de 1 200 et 500, avec des scores de rattachement de 0,8 et 0,4 :

```text
D_brut = (1 200 * 0,8 + 500 * 0,4) / (0,8 + 0,4)
       = (960 + 200) / 1,2
       = 966,67
```

Supposons que ce volume pondéré soit au rang 81 sur 101 : `D = 100 * (81 - 1) / 100 = 80`.

```text
P(C_brut) = 20 ; P(A_brut) = 30
S = 0,5 * 20 + 0,5 * 30 = 25
Ecart = 80 * (1 - 25 / 100) = 60

P(N) = 70 ; P(G) = 50
I = 0,5 * 70 + 0,5 * 50 = 60
T = 60
Criticite = 0,5 * 60 + 0,5 * 60 = 60
```

Résultat : écart `60/100` et criticité `60/100`.

### 2. Demande forte et saturation forte

Deux requêtes ont des volumes mensuels moyens de 5 000 et 3 000, avec des scores de rattachement de 1 et 0,5 :

```text
D_brut = (5 000 * 1 + 3 000 * 0,5) / (1 + 0,5)
       = (5 000 + 1 500) / 1,5
       = 4 333,33
```

Supposons que ce volume pondéré soit au rang 91 sur 101 : `D = 100 * (91 - 1) / 100 = 90`.

```text
P(C_brut) = 80 ; P(A_brut) = 90
S = 0,5 * 80 + 0,5 * 90 = 85
Ecart = 90 * (1 - 85 / 100) = 13,5

P(N) = 90 ; P(G) = 80
I = 0,5 * 90 + 0,5 * 80 = 85
T = 75
Criticite = 0,5 * 85 + 0,5 * 75 = 80
```

Résultat : malgré une demande élevée, la forte saturation limite l'écart à `13,5/100` ; la criticité est `80/100`.

### 3. Demande faible et saturation faible

Deux requêtes ont des volumes mensuels moyens de 100 et 50, avec des scores de rattachement de 1 et 1 :

```text
D_brut = (100 * 1 + 50 * 1) / (1 + 1)
       = 150 / 2
       = 75
```

Supposons que ce volume pondéré soit au rang 21 sur 101 : `D = 100 * (21 - 1) / 100 = 20`.

```text
P(C_brut) = 10 ; P(A_brut) = 30
S = 0,5 * 10 + 0,5 * 30 = 20
Ecart = 20 * (1 - 20 / 100) = 16

P(N) = 40 ; P(G) = 20
I = 0,5 * 40 + 0,5 * 20 = 30
T = 20
Criticite = 0,5 * 30 + 0,5 * 20 = 25
```

Résultat : la faible saturation ne compense pas la faible demande ; l'écart est `16/100` et la criticité `25/100`.

## Politique de version (`version_score`)

- Chaque résultat stocke `version_score`, sa date de calcul et le périmètre utilisé. Chaque score présenté indique au minimum sa version et sa date de calcul.
- Une version identifie de façon immuable les formules, pondérations, sources, fenêtre de 12 mois, mesure de centralité, règle percentile, cohorte et traitement des données manquantes.
- Toute modification susceptible de changer une valeur (formule, pondération, source, fenêtre, centralité, normalisation ou périmètre) crée une nouvelle `version_score`. Les résultats historiques ne sont pas écrasés ; un recalcul produit de nouveaux résultats associés à la nouvelle version.
- Une correction documentaire ou une modification qui ne change aucun résultat peut être publiée comme révision de documentation sans changer `version_score`.
- Les formules et pondérations sont calibrées sur un échantillon de notions relues manuellement. La calibration, les résultats d'évaluation et la décision d'adoption sont conservés avec la définition de version.
- Identifiant proposé pour la première version : `gap-v1`. Le choix des pondérations égales, la normalisation percentile et les autres paramètres proposés restent à valider avant gel de cette version.