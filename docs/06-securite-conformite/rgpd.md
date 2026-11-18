# Registre des traitements et procédures RGPD

## Statut et responsabilités

Document de travail à valider par le responsable du traitement et, le cas
échéant, son délégué à la protection des données (DPO) ou son conseil. Les
bases légales ci-dessous sont des **propositions**, pas une validation
juridique. Les durées, destinataires, contrats et régions effectives doivent
être vérifiés avant publication de la politique de confidentialité et mise en
production. La présence de ce document ne démontre pas la conformité.

- Responsable du traitement, coordonnées et représentant éventuel :
  **à désigner**.
- DPO si désigné, ou contact chargé des droits et incidents : **à désigner**.
- Canal de réception des demandes et canal d'urgence interne : **à mettre en
  place et publier** ; ne pas supposer qu'une boîte ou une astreinte existe.
- Périmètre : comptes, abonnement et analyses, exploitation et sécurité, et
  données du corpus et du marché lorsqu'elles identifient des personnes.
  Les projets et champs libres peuvent eux aussi contenir des données
  personnelles ; les données publiques ne sont pas automatiquement anonymes.

## Registre des traitements

Les durées sont **non définies** dans le dépôt, sauf indication contraire ;
aucune purge automatique générale n'est constatée. Définir pour chaque ligne
une durée de conservation active, un éventuel archivage distinct, les délais de
purge des sauvegardes et les obligations applicables. Les périodes ci-dessous
sont des critères de détermination, et non des durées configurées.

| Finalité et personnes concernées | Base légale proposée à valider | Données et systèmes | Durée / critère à valider | Destinataires prévus |
|---|---|---|---|---|
| Créer et authentifier les comptes ; utilisateurs et personnes inscrites. | Exécution du contrat ou mesures précontractuelles, art. 6.1.b. | Adresse e-mail, identifiant Auth, nom d'affichage, données d'authentification et de session ; Supabase Auth et `profiles`. | Pendant la relation puis selon les critères d'inactivité, de suppression et de preuve à définir ; sauvegardes incluses. | Personnel habilité au support et à l'administration ; Supabase et son éventuel prestataire d'e-mail à vérifier. |
| Fournir projets, analyses et quotas ; utilisateurs. | Exécution du contrat, art. 6.1.b. | Identifiant utilisateur, nom des projets, paramètres et dates des analyses, compteurs de quota ; Supabase `projects`, `analyses`, `usage_quotas`. Les champs libres peuvent contenir des données sur des tiers. | Pendant l'utilisation du service, puis selon les critères de suppression et de sauvegarde à définir. | Utilisateur concerné, personnel habilité et Supabase. |
| Gérer abonnement et paiement ; clients. | Exécution du contrat, art. 6.1.b ; obligation légale, art. 6.1.c, pour les seules pièces dont la conservation est imposée, à identifier. | E-mail transmis au checkout, identifiants client et abonnement Stripe, plan, statut, période ; données de paiement et de facturation traitées par Stripe ; identifiants d'événements dans Supabase. | Relation commerciale, puis durée légale ou probatoire propre à chaque pièce à déterminer ; ne pas conserver tout le dossier sous un motif comptable général. | Personnel habilité à la facturation, Stripe, Supabase et, si applicable, prestataires comptables à identifier. |
| Exploiter et sécuriser le service ; utilisateurs et opérateurs. | Intérêt légitime, art. 6.1.f : assurer sécurité, disponibilité et diagnostic, sous réserve d'une mise en balance documentée ; autres bases à examiner selon les logs. | Journaux techniques et d'exécution, horodatages, identifiants ou données éventuellement présents dans les requêtes et erreurs ; `ops.pipeline_runs` et logs d'hébergement. | Durées distinctes à définir selon sécurité, diagnostic et incidents, avec accès restreint et purge des copies. | Personnel habilité à l'exploitation et à la sécurité ; hébergeur et fournisseurs de journalisation à identifier. |
| Construire les analyses juridiques et de marché ; personnes éventuellement mentionnées dans des sources ou résultats. | Intérêt légitime, art. 6.1.f, à confirmer après analyse des sources, de l'information des personnes et mise en balance ; bases et garanties spécifiques à examiner si données sensibles. | Articles, notions, termes de recherche, URL, domaines et résultats SERP, réponses et archives d'API ; BigQuery, GCS et graphe Neo4j. Textes ou résultats publics peuvent identifier une personne. | Durées par source et copie, actualisation, archivage et purge à définir ; ne pas supposer que la nature publique autorise une conservation illimitée. | Équipe données, utilisateurs des analyses et fournisseurs Google, DataForSEO, Gemini et Neo4j selon les flux effectivement utilisés. |
| Traiter les demandes de droits et les violations ; demandeurs et personnes affectées. | Obligation légale, art. 6.1.c, pour la gestion et la documentation requises ; autres besoins de preuve à qualifier séparément. | Identité minimale, contenu et suivi de la demande, décision, éléments de l'incident et notifications ; outil de suivi à déterminer. | Durée et accès à définir selon les obligations et besoins de preuve, sans conserver inutilement justificatifs ou copies. | Personnel habilité, DPO/conseil si applicable, autorité de contrôle et prestataires concernés selon le cas. |

Références techniques : [migrations Supabase](../../supabase/migrations/),
[architecture web](../02-architecture/web.md) et
[journal du pipeline](../../README.md#migrations-bigquery). Le MVP documente
Stripe en mode test ; confirmer séparément toute activation de paiement réel.

## Fournisseurs et régions

La colonne « région » indique ce qui est connu ou visé par l'architecture,
**pas une attestation de localisation**. Le stockage régional ne garantit pas
la localisation des accès de support, sous-traitants ultérieurs, métadonnées,
sauvegardes ou transferts. Vérifier les entités contractantes et leur rôle
(sous-traitant, responsable distinct ou autre), les contrats/DPA, régions,
transferts hors EEE et garanties applicables pour chaque service et
environnement ; ne pas présumer que des accords sont signés.

| Fournisseur / service | Usage et données possibles | Région d'hébergement ou de traitement |
|---|---|---|
| Supabase / Auth et PostgreSQL | Comptes, projets, analyses, abonnements et quotas ; éventuellement envoi d'e-mails Auth. | Région UE visée ; région du projet, sauvegardes et fournisseur d'e-mail **à vérifier**. |
| Stripe / Checkout, portail et webhooks | E-mail, identifiants, abonnement et données de paiement ; peut agir selon plusieurs rôles. | Région effective, flux internationaux et entité contractante **à vérifier** ; aucune région UE garantie par le dépôt. |
| Google Cloud / BigQuery et Cloud Storage | Corpus, données de marché, extractions, archives et journaux susceptibles de contenir des données personnelles. | BigQuery `europe-west9` et GCS en UE visés ; paramètres réels des datasets, buckets et sauvegardes **à vérifier**. |
| Google / Gemini API | Textes d'articles et prompts pour l'extraction ; les sources peuvent contenir des données personnelles. | Région de traitement, conditions et transferts de l'API effectivement utilisée **à vérifier** ; ne pas déduire sa région de celle de BigQuery. |
| Neo4j / Aura ou instance configurée | Graphe analytique issu des marts ; le modèle vise un graphe sans données utilisateur, mais les contenus sources doivent être examinés. | Aura en région UE envisagée, instance et région effectives **à vérifier**. |
| DataForSEO | Mots-clés et paramètres de recherche transmis, résultats et coûts. | Région de traitement et transferts **à vérifier**. |
| Hébergeur de l'application, logs et autres services opérationnels | Requêtes web, sessions, adresses réseau et erreurs possibles. | Fournisseurs, régions, sous-traitants ultérieurs et sauvegardes **à identifier**. |

## Exercice des droits

Procédure manuelle à organiser : le dépôt ne fournit pas de fonctionnalité
complète d'export ou de suppression de compte. Ne pas promettre un traitement
automatique. La suppression d'un projet entraîne celle de ses analyses ; la
suppression d'un utilisateur Auth entraîne les cascades prévues par les
migrations, mais ne supprime pas automatiquement les données Stripe, journaux,
copies ou sauvegardes.

1. Recevoir la demande par le canal publié ; consigner sa date de réception,
   son objet et un identifiant de suivi avec accès restreint. Transmettre au
   responsable désigné. La personne peut demander accès, rectification,
   effacement, limitation ou opposition, et portabilité lorsque applicable.
2. Vérifier l'identité de façon proportionnée, par exemple via une session
   authentifiée ; ne demander des informations supplémentaires qu'en cas de
   doute raisonnable et ne pas conserver de justificatif superflu. Si la
   personne n'a pas de compte, examiner les autres moyens de la retrouver.
3. Rechercher les données pertinentes dans Auth, profils, projets, analyses,
   quotas et abonnements, puis chez Stripe et dans les autres systèmes, sources,
   journaux ou sauvegardes susceptibles de les contenir. Préserver les droits
   des tiers et vérifier les exceptions et obligations légales applicables.
4. **Accès :** fournir une copie des données et les informations requises sur
   le traitement, notamment finalités, destinataires, conservation et droits.
   **Rectification :** corriger ou compléter les données inexactes dans chaque
   système concerné et informer les destinataires lorsque requis.
5. **Suppression :** vérifier les exceptions, informer des conséquences et
   coordonner, si nécessaire, la résiliation séparée de l'abonnement. Avant de
   supprimer les liens locaux, identifier les données à traiter chez Stripe ;
   empêcher les traitements ou webhooks de recréer les données supprimées.
   Faire supprimer les données éligibles dans les systèmes et chez les
   prestataires concernés, vérifier les cascades et les copies ; isoler les
   données à conserver légalement avec accès limité et échéance de purge.
   Planifier l'expiration des sauvegardes et empêcher toute restauration de
   réintroduire les données effacées. Ne pas affirmer l'effacement complet
   avant vérification.
6. **Export / portabilité :** examiner les conditions du droit à la
   portabilité ; fournir les données concernées dans un format structuré,
   couramment utilisé et lisible par machine, par un canal sécurisé. L'accès
   et la portabilité ont des périmètres différents ; exclure les secrets et
   protéger les données de tiers. Transmettre à un autre responsable si demandé
   et techniquement possible.
7. Répondre sans tarder et au plus tard **un mois après réception**. Une
   prolongation maximale de deux mois est possible selon la complexité ou le
   nombre de demandes ; informer la personne et motiver le report dans le
   premier mois. En cas de refus ou d'inaction, expliquer les motifs et les
   voies de réclamation et de recours dans ce même délai. Documenter les
   vérifications et l'issue sans stocker inutilement les données fournies.

Voir les [articles 12 à 21 du RGPD](https://www.cnil.fr/fr/reglement-europeen-protection-donnees/chapitre3).

## Violation de données personnelles

1. **Alerter immédiatement** le responsable désigné, la sécurité et le DPO
   s'il existe ; relever l'heure de découverte. Un sous-traitant informe le
   responsable sans délai après en avoir pris connaissance. Préserver les
   éléments utiles sans diffuser de données ou de secrets.
2. **Contenir et évaluer :** limiter l'accès, révoquer les accès compromis,
   isoler les composants concernés et préserver les preuves. Suivre le
   [runbook des secrets](../runbooks/secrets.md) si nécessaire. Déterminer
   nature, période, catégories et nombre approximatif de personnes et
   d'enregistrements, conséquences probables et mesures correctives.
3. **Documenter toute violation**, même sans notification : faits, effets,
   décisions et justification du niveau de risque, mesures et dates. Utiliser
   un registre d'incidents à accès restreint, distinct des journaux publics.
4. **Notifier l'autorité compétente** sauf si la violation n'est pas
   susceptible d'engendrer un risque pour les droits et libertés. Notifier
   dans les meilleurs délais et, si possible, dans les **72 heures après
   prise de connaissance** ; au-delà, expliquer le retard. Fournir les
   informations disponibles et les compléter ultérieurement si nécessaire.
   En France, utiliser le
   [téléservice CNIL](https://www.cnil.fr/fr/services-en-ligne/notifier-une-violation-de-donnees-personnelles)
   lorsque la CNIL est compétente ; en cas de traitement transfrontalier,
   identifier l'autorité chef de file.
5. **Informer les personnes concernées sans tarder** si le risque est élevé,
   sauf exception légale applicable : expliquer clairement la nature de la
   violation, ses conséquences probables, les mesures prises, les précautions
   recommandées et le contact. Documenter toute exception ou décision de ne
   pas notifier.
6. Corriger la cause, vérifier le retour à un fonctionnement sûr, suivre les
   notifications complémentaires et consigner le retour d'expérience.

Référence : [CNIL — règles sur les violations de données](https://www.cnil.fr/fr/violations-de-donnees-personnelles-les-regles-suivre).
