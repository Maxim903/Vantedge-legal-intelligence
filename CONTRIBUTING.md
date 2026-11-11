# Contribuer

## Commits

Les messages de commit suivent la convention Conventional Commits avec l'un des
types suivants :

- `feat` : nouvelle fonctionnalité
- `fix` : correction de bug
- `docs` : documentation
- `refactor` : réorganisation du code sans changement fonctionnel attendu
- `test` : ajout ou modification de tests
- `chore` : maintenance et tâches diverses

Format recommandé : `type(portée): description courte`, par exemple
`feat(pipeline): ajouter le chargement des articles`.

## Pull requests

- Une PR correspond à une seule étape du guide du projet. Ne mélangez pas des
  étapes ou sujets indépendants.
- Gardez les PR petites et ciblées pour faciliter la revue.
- Ouvrez une branche dédiée et passez par une Pull Request ; ne poussez jamais
  directement sur `main`.
- Attendez que les vérifications CI requises soient vertes avant la fusion.
- Décrivez l'objectif, les changements, les tests effectués, l'impact
  documentaire et les points de sécurité à l'aide du
  [modèle de Pull Request](.github/PULL_REQUEST_TEMPLATE.md).
