# Alertes et réponse opérationnelle

## Périmètre et notification

Ce document décrit les signaux disponibles et les personnes à prévenir
manuellement. Le dépôt ne configure ni planification de ces contrôles, ni
notification automatique, ni liste de contacts ou d'astreinte. Les rôles
ci-dessous sont des destinataires **recommandés, à désigner** ; aucun canal
ou délai de prise en charge n'est encore défini. Un résultat dbt, une ligne
BigQuery ou un échec CI ne constitue pas à lui seul une notification.

| Signal et source | Seuil ou condition | Qui prévenir | Que faire |
|---|---|---|---|
| Fraîcheur des sources dbt | Avertissement après 30 jours, erreur après 60 jours depuis la dernière donnée non future. | Responsable pipeline/données ; responsable de la source si nécessaire. | Identifier la source et vérifier la dernière ingestion, les erreurs et la disponibilité de la source. Corriger puis relancer le contrôle ; voir les limites ci-dessous. |
| Échec d'un job ou de son journal | `FAILED` dans `ops.pipeline_runs`, ou échec du processus/de la journalisation. | Responsable pipeline ; responsable infrastructure si accès ou service indisponible. | Consulter les logs et le journal ; corriger la cause et évaluer les écritures déjà effectuées avant toute reprise. Un échec du journal peut laisser une ligne `RUNNING`, voire aucune ligne. |
| Job restant `RUNNING` | Durée anormale par rapport à la durée habituelle du job ; aucun seuil automatique configuré. | Responsable pipeline/infrastructure. | Vérifier si le processus tourne encore et consulter ses logs. Un arrêt brutal peut laisser une ligne ouverte ; ne pas relancer en parallèle sans vérifier les effets du premier job. |
| Budget d'exécution atteint | `BUDGET_EXHAUSTED` ; `DRY_RUN_OVER_BUDGET` indique une estimation excessive en simulation. Le plafond est fixé pour chaque exécution. | Responsable pipeline et responsable du budget. | Examiner les compteurs, le coût estimé et les éléments restants ; vérifier la facturation fournisseur. Faire approuver un nouveau budget avant reprise. Un dry-run est lui aussi journalisé. |
| Notion sans requête | Au moins une ligne `notion_sans_requete` dans `ops.ops_qualite` ; aucun seuil global configuré. | Responsable données métier/pipeline. | Examiner la notion et les rattachements, puis vérifier la génération des requêtes et la reconstruction des marts. Une absence peut nécessiter une décision métier. |
| Requête sans volume récent | Ligne `requete_sans_volume_60j` : aucune collecte non future de volume strictement positif, ou dernière collecte positive datant d'au moins 60 jours calendaires. | Responsable collecte marché/données. | Vérifier la requête, le pays/la langue, la collecte et le chargement DataForSEO. Zéro et `NULL` ne sont pas positifs ; une collecte positive antérieure récente reste valable. |
| Quarantaine IA | `taux_quarantaine_60j` dans `ops.ops_qualite` ; aucun seuil d'alerte configuré. `NULL` signifie absence de résultats, pas un taux nul. | Responsable IA et personne chargée de la revue. | Examiner les nombres et les raisons de quarantaine dans `ops.extraction_results`, puis le modèle et le prompt. Les résultats en quarantaine ne sont pas retraités automatiquement ; décider de la suite après revue. |
| Divergence graphe | Le contrôle de cohérence signale un écart de comptes ou des données invalides, avec code de sortie non nul ; `INCONSISTENT` indique un écart détecté. | Responsable graphe et responsable données. | Exécuter le contrôle hors synchronisation/reconstruction des marts, analyser les catégories signalées et leurs sources. Une synchronisation ne supprime pas les anciens éléments ; ne pas supposer qu'une relance suffit. |
| Échec CI | Un job CI échoue ; pas de seuil numérique. | Auteur du changement et responsable du composant concerné. | Consulter les logs du job, corriger la cause et relancer les contrôles concernés. Ne pas fusionner avant le succès de la CI requise. |
| Secret exposé | Toute exposition avérée ou suspectée, sans seuil numérique. | Responsable sécurité/infrastructure et équipe concernée, immédiatement. | Révoquer ou faire tourner le secret, mettre à jour les environnements et suivre le [runbook des secrets](secrets.md). Ne pas transmettre la valeur dans l'alerte. |

## Vérifications

Avec un projet et des identifiants BigQuery autorisés, les commandes dbt et les
conditions préalables sont décrites dans la section
[qualité et fraîcheur](../../README.md#qualité-et-fraîcheur-dbt). Les contrôles
couvrent `raw.articles`, `raw.article_versions`, `raw.entites_extraites`,
`raw.requetes_intentions`, `raw.dataforseo_volumes`, `raw.dataforseo_serp` et
`ops.extraction_results`. Les dates futures sont exclues. Une source vide ou
une erreur d'accès nécessite aussi une investigation : ne pas considérer
l'absence de mesure comme un succès.

Pour les articles et leurs versions, la date reflète les insertions ou
modifications, pas nécessairement chaque passage du pipeline : une source
inchangée peut être signalée ancienne. `raw.requetes_candidates` n'a pas
d'horodatage ; `raw.dataforseo_intent` n'est pas couverte. La fraîcheur doit
être lancée explicitement : le workflow CI du dépôt ne l'exécute pas.

Dans BigQuery, sélectionner le bon projet et consulter en lecture seule :

```sql
SELECT type_controle, notion_id, requete_id, pays_langue_id, libelle,
       derniere_collecte_volume, nombre_quarantaine, nombre_extractions,
       taux_quarantaine
FROM `ops.ops_qualite`
ORDER BY type_controle, notion_id, requete_id;
```

Le taux de quarantaine porte sur les résultats d'extraction des 60 derniers
jours glissants, bornes incluses. Pour examiner les exécutions récentes :

```sql
SELECT run_id, job, debut, fin, statut, compteurs, erreur, cout_estime
FROM `ops.pipeline_runs`
WHERE debut >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
ORDER BY debut DESC;
```

Le journal conserve les types d'exceptions sans leurs messages ; les exceptions
propagées et les anciennes lignes peuvent contenir des données sensibles.
Limiter l'accès à `ops` et aux logs, et ne diffuser que les informations
nécessaires. Un échec de démarrage
de la journalisation peut empêcher la création de toute ligne ; consulter aussi
les logs du processus ou de l'orchestrateur. Adapter la période de consultation
si l'exécution recherchée est plus ancienne.

Pour la commande de contrôle du graphe et ses limites, voir
[contrôle de cohérence du graphe](../../README.md#contrôle-de-cohérence-du-graphe).
Une égalité des comptes ne prouve pas l'égalité des éléments individuels.
