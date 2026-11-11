---
name: "Écrire des tests"
description: "Ajouter des tests de comportement en suivant les conventions et outils déjà présents dans le dépôt."
argument-hint: "Indique le comportement, le fichier ou le changement à tester."
agent: "agent"
---

Écris des tests pour le comportement ou le changement décrit dans la demande.

1. Repère le code concerné, le framework de test et les conventions des tests voisins avant d'écrire.
2. Couvre le résultat nominal, les cas limites et les erreurs pertinentes. Pour une régression, ajoute un test qui échoue sans le correctif et réussit avec celui-ci.
3. Respecte les définitions du [glossaire du projet](../../docs/glossaire.md) lorsque les tests portent sur une Notion juridique, une Situation de vie, une Requête ou une Intention de recherche.
4. N'altère pas le code de production pour faire passer les tests, sauf si la demande inclut explicitement sa correction ; dans ce cas, explique le changement.
5. Lance les tests ciblés et rapporte leur résultat. N'affirme pas qu'une vérification a réussi si elle n'a pas été exécutée.