# Périmètre et critères d'acceptation du MVP

## Périmètre

- Corpus : Livre I du Code du travail.
- Marché : France, langue française (`fr`).
- Parcours : inscription, abonnement Stripe en mode test, consultation de la liste des notions triée par score d'écart et consultation du détail d'une notion.
- Données utilisateur : comptes et projets isolés par utilisateur via Supabase RLS.
- Les quotas sont contrôlés côté serveur avant tout appel coûteux.
- Le produit fournit une analyse de marché et de données, pas une consultation juridique.

## Critères d'acceptation vérifiables

| ID | Critère | Vérification et résultat attendu |
|---|---|---|
| MVP-01 | Périmètre juridique et marché | Charger le corpus du Livre I du Code du travail et des données France/fr. Vérifier qu'aucun contenu d'un autre code, pays ou langue n'est proposé dans le parcours MVP. |
| MVP-02 | Inscription | Créer un compte avec des données valides, puis se connecter. Vérifier que le compte est créé dans Supabase et que l'utilisateur accède à son espace authentifié. Une entrée invalide ou un échec d'authentification n'ouvre pas de session et affiche une erreur exploitable. |
| MVP-03 | Abonnement en mode test | Effectuer le parcours d'abonnement Stripe avec des moyens de paiement de test. Vérifier que l'événement webhook signé met à jour l'état d'abonnement correspondant dans Supabase, sans paiement réel. Rejouer le même webhook et vérifier qu'il ne crée pas de doublon ni de transition supplémentaire. |
| MVP-04 | Liste des notions triée par écart | Charger un jeu de données de test avec au moins trois notions ayant des scores d'écart différents. Vérifier que la liste est triée par score décroissant et que le score affiché correspond aux données calculées. Chaque score présente sa définition, sa version et sa date de calcul. |
| MVP-05 | Détail d'une notion | Ouvrir une notion depuis la liste. Vérifier que sa page affiche les articles sources et leur version en vigueur, ainsi que les requêtes, métriques et résultats SERP disponibles. Un lien depuis la notion mène à l'article source correspondant. |
| MVP-06 | Quotas | Configurer une limite de test connue pour un plan. Vérifier qu'un utilisateur sous la limite peut lancer l'action autorisée, que son utilisation est enregistrée, et qu'une action dépassant la limite est bloquée côté serveur avant tout appel coûteux. Vérifier que les quotas et crédits affichés reflètent l'état serveur. |
| MVP-07 | Isolation RLS | Créer deux utilisateurs avec profils, projets et historique distincts. Avec les identifiants de chaque utilisateur, vérifier qu'il ne peut ni lire ni modifier les données de l'autre. Exécuter ces vérifications par des tests automatisés sur toutes les tables Supabase contenant des données utilisateur. |
| MVP-08 | Mention d'absence de conseil juridique | Vérifier que la phrase « Cet outil ne fournit aucun conseil juridique. » est visible dans l'interface d'analyse et de détail, et figure dans les CGU. Elle ne doit pas être masquée derrière une action secondaire. |
| MVP-09 | États d'interface essentiels | Pour la liste et le détail, vérifier l'affichage d'états explicites de chargement, de données vides et d'erreur. Une erreur ou une action refusée pour quota ne doit pas être présentée comme un résultat valide. |

## Hors MVP

- Le Code civil et tout code autre que le Livre I du Code du travail.
- Les pays autres que la France et les langues autres que le français (`fr`).
- Les recommandations de contenu générées automatiquement.
- Une API publique.
- L'export massif.
- La marque blanche.
- La facturation réelle en production ; le parcours d'abonnement du MVP utilise le mode test Stripe.

## Hypothèses et paramètres à confirmer

- Le dossier ne fixe pas les plafonds, crédits, période de renouvellement ni coût de chaque action ; les tests de quota utilisent une limite configurée et connue, sans imposer de valeur métier.
- Le tri par défaut est décroissant sur le score d'écart. En cas d'égalité, un ordre secondaire stable (par exemple le libellé de la notion) doit être choisi avant la recette.
- Le parcours d'inscription, les moyens d'authentification et l'éventuelle vérification de l'adresse électronique restent à confirmer.
- La liste et le détail affichent les données effectivement disponibles ; l'absence de métriques ou de résultats SERP ne bloque pas l'accès aux autres informations de la notion.