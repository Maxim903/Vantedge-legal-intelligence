# Spécification des écrans

Ce document décline l'interface du chapitre 10 en six écrans. Les quotas exacts, les plans et les règles de consommation ne sont pas définis dans le dossier ; les comportements qui les précisent sont signalés dans les hypothèses à valider.

## 1. Inscription

### Objectif

Créer un compte utilisateur afin d'accéder à l'application.

### Données affichées

- Formulaire de création de compte et résultat de la validation.
- Liens vers les CGU et la politique de confidentialité.
- Mention visible que le produit fournit une analyse de marché et de données, pas un conseil juridique.

### États

| État | Comportement |
|---|---|
| Vide | Formulaire prêt à être rempli. |
| Chargement | Envoi en cours ; désactiver la soumission répétée et afficher une progression. |
| Succès | Confirmer la création du compte et, si nécessaire, indiquer la prochaine étape de vérification. |
| Erreur | Signaler les champs invalides ou l'échec de création sans exposer de détails techniques ; permettre la correction ou une nouvelle tentative. |

### Règles de quota

- La création de compte ne consomme pas de quota d'analyse ni de crédit.
- L'inscription ne doit pas déclencher d'appel payant à DataForSEO ou au fournisseur LLM.
- L'abonnement et les limites associées sont déterminés côté serveur après création du compte.

## 2. Connexion

### Objectif

Authentifier l'utilisateur et ouvrir sa session Supabase Auth.

### Données affichées

- Champs d'identification et résultat de la tentative de connexion.
- Liens vers l'inscription et les pages légales applicables.

### États

| État | Comportement |
|---|---|
| Vide | Formulaire de connexion prêt. |
| Chargement | Authentification en cours ; éviter les soumissions multiples. |
| Succès | Ouvrir la session et rediriger vers Mon compte et projets ou vers la destination demandée. |
| Erreur | Afficher un message générique d'échec d'authentification ; permettre une nouvelle tentative sans révéler si un compte existe. |
| Session expirée | Demander une nouvelle authentification avant de reprendre l'accès aux données privées. |

### Règles de quota

- La connexion et le renouvellement de session ne consomment pas de quota d'analyse ni de crédit.
- La session identifie l'utilisateur ; l'autorisation et la vérification des quotas restent côté serveur.

## 3. Mon compte et projets

### Objectif

Permettre à l'utilisateur de consulter son profil, son abonnement, ses quotas, ses projets et l'historique de ses recherches et analyses.

### Données affichées

- Profil utilisateur.
- Abonnement, avec accès à la gestion de facturation via Stripe.
- Quotas d'analyses et crédits : plafond, consommation et disponibilité, selon le plan.
- Projets sauvegardés.
- Historique des recherches et analyses.

### États

| État | Comportement |
|---|---|
| Vide | Afficher l'absence de projets ou d'historique et proposer la première action correspondante. |
| Chargement | Charger séparément profil, abonnement, projets, quotas et historique ; indiquer les sections encore indisponibles. |
| Erreur | Identifier la section en erreur, conserver les autres données disponibles et proposer une nouvelle tentative. Ne pas afficher un quota supposé en cas d'échec de lecture. |
| Données disponibles | Afficher les informations de compte et l'état d'abonnement synchronisé depuis Supabase. |

### Règles de quota

- Afficher le plan, les quotas et les crédits disponibles issus de l'état serveur ; ne pas calculer l'autorisation uniquement dans le navigateur.
- Vérifier le quota côté serveur avant tout appel coûteux déclenché depuis un projet ou une analyse.
- Un dépassement de quota bloque l'action concernée et indique l'état du quota ainsi que la voie de gestion de l'abonnement disponible via Stripe.
- Les plafonds, périodes de renouvellement, reports de crédits et règles de facturation restent à définir.

## 4. Analyse loi vs marché

### Objectif

Présenter l'analyse d'écart entre la norme juridique et la demande du marché pour le périmètre du MVP.

### Données affichées

- Groupes de notions et leur criticité sémantique.
- Scores d'écart entre norme et demande du marché.
- Synthèse des intentions de recherche.
- Indicateurs disponibles pour les notions : demande, saturation et importance normative.
- Définition de chaque score et date de calcul, notamment via une infobulle.
- Périmètre appliqué : Code du travail, livre retenu, France et langue française (fr).

### États

| État | Comportement |
|---|---|
| Vide | Expliquer qu'aucune analyse n'est disponible pour le périmètre sélectionné et proposer de lancer une analyse si le quota le permet. |
| Chargement | Signaler le calcul ou le chargement des résultats ; empêcher les déclenchements répétés du même traitement. |
| Erreur | Afficher une erreur compréhensible et permettre une nouvelle tentative ; distinguer un dépassement de quota d'une indisponibilité technique. |
| Résultats disponibles | Afficher les scores avec leur définition, leur version et leur date de calcul. |

### Règles de quota

- Toute action qui déclenche un appel coûteux doit être autorisée côté serveur avant son exécution.
- Si le quota est épuisé, les résultats déjà disponibles restent consultables ; aucun nouveau traitement payant n'est lancé.
- Afficher le coût en quota/crédits avant confirmation uniquement lorsque le tarif de l'action est défini.
- Le nombre de crédits consommés par une analyse, le traitement des reprises et l'effet d'un résultat mis en cache restent à valider.

## 5. Détail d'une notion

### Objectif

Permettre de comprendre une notion et ses liens entre norme juridique et expression du marché.

### Données affichées

- Libellé de la notion et définition courte lorsqu'elle est disponible.
- Articles sources et version de chaque article en vigueur.
- Situations de vie associées.
- Requêtes rattachées et leur score de rattachement.
- Métriques de marché : volume, CPC, concurrence et période, par pays et langue.
- Résultats SERP disponibles.
- Indices D, S, I, score d'écart et criticité sémantique ; définition, `version_score` et date de calcul pour chaque score.
- Mention « Cet outil ne fournit aucun conseil juridique. »

### États

| État | Comportement |
|---|---|
| Vide | Si la notion ne possède pas une catégorie de données, signaler spécifiquement l'absence d'article, de requête, de métrique ou de résultat SERP sans masquer les autres catégories. |
| Chargement | Charger les catégories de données et indiquer celles qui restent en cours de récupération. |
| Erreur | Signaler la catégorie indisponible et permettre une nouvelle tentative ; conserver les autres catégories chargées. |
| Données disponibles | Relier la notion à l'article source et à sa version en vigueur ; rendre les scores explicables et datés. |

### Règles de quota

- La consultation de données déjà calculées est en lecture seule et ne déclenche pas d'appel payant.
- Toute actualisation ou recalcul doit être contrôlé côté serveur avant l'appel coûteux.
- Si le quota ne permet pas l'actualisation, conserver l'accès aux données déjà disponibles et indiquer que le recalcul est indisponible.
- Le coût d'une actualisation par notion et la consommation des crédits sont à valider.

## 6. Pages légales

### Objectif

Présenter les conditions d'utilisation, les informations de confidentialité et les limites du service afin que l'utilisateur puisse les consulter avant ou pendant l'utilisation.

### Données affichées

- CGU, dont l'exclusion explicite du conseil juridique, la limitation de responsabilité et les conditions d'usage des données.
- Politique de confidentialité : traitements, données concernées et durées de conservation.
- Droits des personnes : accès, rectification, suppression et export.
- Informations sur les sous-traitants et les transferts éventuels hors UE.
- Source des contenus juridiques et date de mise à jour, conformément à la Licence Ouverte.
- Mention claire : « Cet outil ne fournit aucun conseil juridique. »

### États

| État | Comportement |
|---|---|
| Vide | Ne pas publier une page légale vide ; si le contenu requis n'est pas configuré, signaler l'indisponibilité et bloquer le parcours qui exige son acceptation. |
| Chargement | Afficher un état de chargement si les contenus sont servis dynamiquement. |
| Erreur | Indiquer l'indisponibilité du document et proposer une nouvelle tentative ; ne pas enregistrer une acceptation impossible à consulter. |
| Contenu disponible | Afficher le texte en vigueur, sa date ou version et les liens entre documents. |

### Règles de quota

- La consultation des pages légales ne consomme aucun quota d'analyse ni crédit.
- Le chargement de ces pages ne déclenche aucun appel à DataForSEO ou au fournisseur LLM.

## Principes transverses

- Les états vides, chargements et erreurs sont explicites ; l'interface est responsive.
- Les scores affichent leur définition et leur date de calcul.
- Les accès aux données utilisateur sont isolés par RLS ; les identifiants Neo4j et BigQuery ne sont jamais exposés au navigateur.
- Les quotas sont contrôlés côté serveur avant tout appel coûteux, jamais uniquement côté client.
- L'accessibilité WCAG 2.1 AA est visée : contrastes, navigation clavier et libellés.

## Hypothèses à valider

- Les modalités d'inscription, la vérification d'adresse électronique et les moyens d'authentification ne sont pas précisés dans le dossier.
- Les écrans d'analyse et de détail peuvent proposer un recalcul explicite ; le dossier ne fixe pas le parcours de lancement de ces traitements.
- Les plans, plafonds, unités de consommation, périodes de renouvellement, règles de cache et traitement des échecs/reprises ne sont pas définis ; aucune valeur chiffrée n'est présumée ici.
- Le contenu légal, sa date de version et le parcours de consentement éventuel doivent être fournis et validés avant production.