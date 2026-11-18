# ADR-0007 : Hébergement de l'application web

## Contexte

L'application Next.js assure le rendu serveur, l'authentification, les routes
Stripe et l'accès serveur à BigQuery et Neo4j. Une exportation purement statique
ne suffit donc pas. Le projet vise des ressources en UE, notamment BigQuery à
Paris (`europe-west9`), sans que la région de l'application garantisse à elle
seule la localisation des autres services, journaux ou échanges.

Le dépôt ne configure actuellement ni hébergement web de production ni
pipeline de publication de l'application. La décision et les coûts restent à
valider avant mise en production.

## Décision

Proposer **Cloud Run en `europe-west9`** pour le MVP : il rapproche le calcul
de BigQuery et permet d'utiliser l'identité de service Google existante
`sa-app-reader` par ADC, sans clé de compte de service. L'application doit être
emballée dans sa propre image Node.js ; l'image des jobs Python n'est pas
adaptée. Le domaine HTTPS passera par un load balancer applicatif externe et
un backend serverless. La configuration et la procédure figurent dans le
[runbook](../runbooks/deploiement-web.md).

Cette recommandation ne constitue pas une validation de sécurité, de conformité
ou de budget. Tester l'architecture complète et confirmer le choix avant
création des ressources de production.

## Alternatives

| Critère | Cloud Run, Paris | Vercel, Paris |
|---|---|---|
| Exécution Next.js | Serveur Node.js conteneurisé ; image, cache multi-instance et exploitation à configurer. | Intégration Next.js gérée ; vérifier le build monorepo et la compatibilité des fonctionnalités utilisées. |
| Région | Service en `europe-west9`. Le load balancer global a ses propres points d'entrée et règles de traitement. | Fonctions configurables en `cdg1` ; la région par défaut des nouveaux projets est `iad1`. CDN et middleware de routage peuvent être mondiaux. |
| Identité BigQuery | Identité Cloud Run `sa-app-reader` et ADC, avec droits IAM limités. | Une identité fédérée Google compatible avec ADC doit être conçue et testée ; aucune intégration n'est configurée dans le dépôt. Ne pas utiliser de clé JSON longue durée par défaut. |
| Domaine et retour arrière | Load balancer, certificat et DNS à gérer ; retour à une révision Cloud Run. | Domaine et certificat gérés par la plateforme ; retour à un déploiement éligible, selon l'offre. |
| Coûts et exploitation | Conteneur, trafic, instances, load balancer et services associés ; chiffrage et supervision à établir. | Facturation, limites de fonctions, builds et options selon l'offre ; chiffrage à établir. |

Vercel est une alternative si sa simplicité d'exploitation compense la
configuration d'une identité Google sans clé, les contraintes de plan et les
vérifications de localisation. Pour chaque option, confirmer région des
fonctions, routage, logs, sauvegardes, sous-traitants, transferts et DPA ; ni
`cdg1` ni `europe-west9` ne prouvent une résidence de bout en bout.

## Conséquences

- Préparer et tester une image web, une publication contrôlée après CI et des
  environnements isolés ; aucun de ces éléments n'est encore fourni.
- Configurer le domaine, TLS, les secrets et les permissions minimales, puis
  vérifier les parcours d'authentification, d'analyse et de paiement.
- Prévoir la coordination du cache Next.js entre instances et vérifier les
  limites de temps et de connexions vers les services externes.
- Renseigner l'hébergeur et les flux réels dans le
  [registre RGPD](../06-securite-conformite/rgpd.md) et les mentions légales
  après validation.

Références : [régions Vercel](https://vercel.com/docs/regions),
[régions des fonctions Vercel](https://vercel.com/docs/functions/configuring-functions/region),
[domaines Cloud Run](https://cloud.google.com/run/docs/mapping-custom-domains),
[hébergement Next.js](https://nextjs.org/docs/app/guides/self-hosting).

## Statut

Proposé
