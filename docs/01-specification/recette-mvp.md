# Recette du MVP

Critères issus du [périmètre MVP](mvp.md). Renseigner chaque ligne après
vérification : **OK** si tous les points du critère sont satisfaits, **KO**
sinon. Laisser vide si le critère n'a pas encore été vérifié. Indiquer une
capture ou un lien vers la preuve et la date de vérification (AAAA-MM-JJ).
Ne pas inclure de secrets ni de données personnelles dans les preuves.

- Environnement :
- Version ou commit :
- Personne chargée de la recette :

| ID | Critère d'acceptation | Résultat (OK/KO) | Preuve (capture ou lien) | Date |
|---|---|---|---|---|
| MVP-01 | Le parcours se limite au Livre I du Code du travail et au marché France/fr, sans autre code, pays ou langue. |  |  |  |
| MVP-02 | L'inscription et la connexion valides créent le compte et ouvrent l'espace authentifié ; les entrées invalides ou échecs affichent une erreur sans ouvrir de session. |  |  |  |
| MVP-03 | L'abonnement Stripe en mode test met à jour l'état dans Supabase via le webhook signé ; rejouer l'événement ne crée ni doublon ni transition supplémentaire. Aucun paiement réel. |  |  |  |
| MVP-04 | Avec au moins trois notions aux scores différents, la liste est triée par écart décroissant ; chaque score correspond aux données calculées et présente définition, version et date de calcul. |  |  |  |
| MVP-05 | Le détail d'une notion affiche les articles sources et leur version en vigueur, ainsi que les requêtes, métriques et résultats SERP disponibles ; le lien vers l'article source fonctionne. |  |  |  |
| MVP-06 | Avec une limite connue, l'action autorisée est enregistrée ; le dépassement est bloqué côté serveur avant tout appel coûteux ; les quotas et crédits affichés reflètent l'état serveur. |  |  |  |
| MVP-07 | Deux utilisateurs ne peuvent ni lire ni modifier les données de l'autre ; les tests RLS automatisés couvrent toutes les tables Supabase contenant des données utilisateur. |  |  |  |
| MVP-08 | La mention « Cet outil ne fournit aucun conseil juridique. » est visible sans action secondaire dans l'analyse et le détail, et figure dans les CGU. |  |  |  |
| MVP-09 | La liste et le détail présentent des états explicites de chargement, de données vides et d'erreur ; une erreur ou un refus de quota n'est pas présenté comme un résultat valide. |  |  |  |
