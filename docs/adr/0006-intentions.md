# ADR-0006 : Méthode de classification des intentions de recherche

## Contexte

Le modèle de données (`dim_intention`, `dim_requete`, `ref_taxonomie_intention`) associe
à chaque requête de recherche une intention dominante parmi quatre catégories canoniques :
`informationnelle`, `transactionnelle`, `commerciale` et `navigationnelle`.
Cette intention est essentielle pour calculer la criticité sémantique et la part d'intentions
commerciales/transactionnelles des notions juridiques.

Deux options sont envisagées pour attribuer cette intention :
1. L'API DataForSEO (endpoint Labs Search Intent / SERP analysis).
2. Une classification interne par règles taxonomiques déterministes.

## Décision

Pour le MVP, choisir la **classification interne** déterministe basée sur une taxonomie de
règles lexicales.

L'intention dominante retenue pour chaque requête est l'une des quatre valeurs canoniques
définies dans `dim_intention` :
- `informationnelle` : recherche d'information, définition, droits, calcul, démarche générale
  (intention par défaut dans le corpus juridique).
- `transactionnelle` : recherche d'une action directe, d'une assistance juridique ou d'un
  modèle (ex. avocat, saisine, formulaire Cerfa, modèle de lettre, recours).
- `commerciale` : comparaison de solutions, prestations, prestataires ou logiciels payants
  (ex. comparatif, tarif, solution RH, logiciel).
- `navigationnelle` : recherche ciblant un organisme, site officiel ou portail institutionnel
  (ex. Légifrance, Service-Public, URSSAF, Code du travail numérique).

En cas de signaux multiples, un ordre de priorité déterministe est appliqué :
`transactionnelle` > `commerciale` > `navigationnelle` > `informationnelle`.

## Alternatives

| Critère | Classification interne | API DataForSEO (Search Intent) |
|---|---|---|
| Coût | Nul (0 €) ; aucun appel d'API supplémentaire. | Coût par requête supplémentaire (consommation du budget DataForSEO). |
| Latence et disponibilité | Immédiate et 100 % locale ; pas de dépendance réseau ni de quotas. | Dépendante de la disponibilité du service externe, avec gestion de cache et de retries. |
| Adéquation au droit français | Règles adaptées au vocabulaire juridique et aux démarches françaises (Cerfa, prud'hommes, conventions, etc.). | Modèle générique international, souvent calibré sur l'e-commerce anglophone et moins précis sur le droit social français. |
| Traçabilité et auditabilité | Totalement transparente, reproductible et documentée dans `ref_taxonomie_intention`. | Boîte noire algorithmique sans explication des critères d'attribution. |

L'API DataForSEO Search Intent reste une alternative envisageable pour un enrichissement ultérieur
ou une analyse comparative (benchmark).

## Conséquences

- Zéro surcoût d'API pour la détermination des intentions de recherche.
- Les intentions sont produites de façon reproductible et instantanée lors de l'exécution du job.
- Les résultats sont enregistrés dans la table `raw.requetes_intentions` avec l'intention dominante,
  le score de confiance et la méthode appliquée.
- Les règles lexicales pourront évoluer par version de taxonomie.

## Statut

Accepté
