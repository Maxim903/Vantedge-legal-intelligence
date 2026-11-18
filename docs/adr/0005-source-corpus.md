# ADR-0005 : Choix de la source du corpus juridique

## Contexte

Le pipeline doit ingérer un corpus juridique officiel, le versionner et permettre
son rafraîchissement. Deux options sont envisagées : les archives LEGI diffusées
par la DILA, notamment sur data.gouv.fr, et l'API Légifrance accessible via
PISTE. Le MVP porte sur un périmètre limité du Code du travail.

## Décision

Pour le MVP, privilégier les archives LEGI de la DILA comme source du corpus.
Cette recommandation reste proposée et devra être validée avant la mise en
production, notamment au regard des modalités de diffusion et de la licence
applicables aux fichiers effectivement utilisés.

La Licence Ouverte Etalab est une piste pour la réutilisation des contenus,
mais son applicabilité et les obligations associées (attribution de la source,
date de mise à jour et éventuelles conditions particulières) sont à vérifier.

## Alternatives

| Critère | Archives LEGI de la DILA | API Légifrance via PISTE |
|---|---|---|
| Coût | Potentiellement adaptée à une ingestion initiale en lot ; coûts d'hébergement et de traitement à estimer. | Coût direct, modalités d'accès et éventuels frais à vérifier selon l'offre et les quotas. |
| Fraîcheur | Dépend de la fréquence de publication des archives et du délai de réingestion. | Permet des consultations à la demande ; fraîcheur effective et disponibilité des versions dépendent de l'API. |
| Quotas | Pas de quota d'appels pour le traitement local des fichiers ; limites de téléchargement ou de diffusion à vérifier. | Soumise aux règles d'accès, quotas et limites de débit PISTE à vérifier. |
| Effort | Nécessite le téléchargement, le parsing, le suivi des versions et l'import des archives. | Nécessite l'intégration et l'authentification PISTE, la gestion des quotas et le mapping des réponses. |

L'API PISTE reste une alternative pertinente si les besoins de fraîcheur ou de
consultation ciblée justifient son intégration, ou si les archives ne couvrent
pas suffisamment le périmètre requis.

## Conséquences

- L'ingestion initiale du MVP est organisée autour des archives LEGI.
- Le pipeline doit conserver la provenance, la date de récupération et la
  version de chaque archive ingérée.
- Le parsing et la réingestion des archives sont à mettre en place et à tester.
- La fréquence de rafraîchissement et la couverture réelle des archives doivent
  être vérifiées avant de fixer un objectif de fraîcheur.
- Les droits de réutilisation, la Licence Ouverte Etalab et les obligations
  d'attribution restent à vérifier avant toute mise en production.
- L'architecture doit permettre d'ajouter ultérieurement PISTE comme source
  complémentaire ou solution de rafraîchissement ciblé.

## Statut

Proposé
