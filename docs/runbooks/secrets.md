# Gestion des secrets

## Règles obligatoires

- Aucun secret, jeton, mot de passe ou identifiant privé ne doit être ajouté à Git,
  même dans une branche temporaire ou un commit qui serait ensuite amendé.
- Le fichier `.env.example` ne contient que les noms des variables et des
  indications de provenance. Il ne doit jamais contenir de valeurs réelles.
- Les fichiers `.env` locaux et les fichiers de credentials doivent rester hors
  du contrôle de version. En cas de doute, vérifier `git status` avant tout commit.
- Les secrets ne doivent jamais être transmis au navigateur, inclus dans un bundle
  client, retournés par une API ou écrits dans les journaux.
- Exception de nommage : seules les variables `NEXT_PUBLIC_*` sont destinées au
  navigateur. Elles doivent contenir exclusivement des valeurs publiques, jamais
  de secret. La clé Supabase anon/publishable est conçue pour être publique et
  doit être protégée par les politiques RLS appropriées.
- `SUPABASE_SERVICE_ROLE_KEY`, les clés Stripe, les identifiants DataForSEO,
  Neo4j, Google Cloud et LLM sont strictement réservés aux processus serveur.

## Où obtenir les valeurs

Les sources de chaque variable sont indiquées en commentaire dans
[`../../.env.example`](../../.env.example). Pour les environnements partagés ou
de production, stocker les valeurs privées dans un gestionnaire de secrets
(par exemple Google Cloud Secret Manager ou les secrets de l'environnement
d'exécution) et les injecter au démarrage. Ne pas les inscrire dans la
configuration versionnée du dépôt.

## Si un secret est exposé

Révoquer ou faire tourner immédiatement le secret auprès de son fournisseur,
mettre à jour le gestionnaire de secrets et les environnements concernés, puis
signaler l'incident à l'équipe. Supprimer la valeur du fichier ou du commit ne
suffit pas : une valeur ajoutée à Git doit être considérée comme compromise.
