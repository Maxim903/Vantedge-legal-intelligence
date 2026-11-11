---
name: "Revue de code"
description: "Examiner un diff ou des fichiers pour relever les défauts, risques et lacunes de tests sans modifier le code."
argument-hint: "Précise le diff, les fichiers ou le périmètre à examiner."
agent: "agent"
---

Effectue une revue du diff ou du code indiqué, sans modifier les fichiers.

1. Lis les instructions du dépôt et le contexte proche du code examiné.
2. Cherche en priorité les bogues, régressions, problèmes de sécurité ou de données, et tests manquants. Vérifie chaque constat dans le contexte avant de le rapporter.
3. Pour le domaine juridique, utilise le [glossaire du projet](../../docs/glossaire.md) afin de distinguer correctement une Notion juridique, une Situation de vie, une Requête et une Intention de recherche.
4. Présente les constats en premier, par gravité décroissante, avec le fichier et la ligne concernés, l'impact et une explication concise.
5. Si aucun problème n'est trouvé, indique-le clairement et mentionne les lacunes de test ou risques résiduels pertinents.

Ne propose pas de résumé général avant les constats et n'applique pas de correctif dans le cadre de cette revue.