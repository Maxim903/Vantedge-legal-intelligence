Ce dossier documente les composants d’intelligence artificielle du projet.

## Jeu de référence pour l'extraction

Le fichier [golden-set.csv](golden-set.csv) contient 100 versions d'articles
du Livre I du Code du travail, en vigueur au 11 novembre 2026. La sélection est
stratifiée par identifiant de titre : chaque titre est représenté, puis les
places restantes sont réparties proportionnellement aux effectifs disponibles.
Le tirage utilise une graine fixe (`42`) et ne dépend pas de l'ordre des articles.

**Les 100 articles comportent une première annotation proposée par Copilot
(IA), le 11 novembre 2026. Elle n'a pas été validée par un expert humain** :
elle constitue un brouillon à relire indépendamment, pas une vérité terrain
fiable. Les libellés couvrent les notions principales identifiées dans chaque
texte ; ils peuvent omettre des notions ou nécessiter une harmonisation. Éviter
de considérer une évaluation contre ces propositions comme une mesure de
qualité indépendante de l'IA.

Pour la revue, indiquer les notions explicitement présentes dans chaque texte,
l'identifiant de la personne ayant annoté et la date de revue. Utiliser une liste
JSON de libellés dans `notions_attendues` : par exemple
`["Congé payé", "Employeur"]` ;
`[]` signifie qu'une revue a conclu à l'absence de notion, tandis qu'une cellule
vide signifie « non annoté ». Une relecture indépendante est recommandée avant
d'utiliser ce fichier pour calculer des métriques de qualité.
Le fichier [golden-set-titres.csv](golden-set-titres.csv) associe chaque article
à son titre d'origine et à l'empreinte de son texte ; il permet de calculer les
résultats par titre sans modifier les colonnes du jeu d'annotation.

### Source et reproduction

Le fichier a été généré à partir de l'instantané du Code du travail diffusé par
[SocialGouv/legi-data](https://github.com/SocialGouv/legi-data), lui-même issu
des données LEGI de la DILA. Révision :
`03b053fb72f57027242500a65602aa3fed4bd46f` ; SHA-256 du JSON source :
`4a9f2de6f0b11ef4cf581736bbd4c0c5cc534870320c34f1583797a8f53f3c54`.
Les données LEGI sont publiées sous
[Licence Ouverte](https://www.data.gouv.fr/datasets/legi-codes-lois-et-reglements-consolides).
Le JSON est un instantané : sa période de validité doit inclure la date demandée.

Depuis la racine du dépôt, après installation des dépendances du pipeline :

```sh
curl -fsSL \
  https://raw.githubusercontent.com/SocialGouv/legi-data/03b053fb72f57027242500a65602aa3fed4bd46f/data/LEGITEXT000006072050.json \
  -o /tmp/code-travail-snapshot.json
cd pipeline
uv run python ../scripts/make_golden_set.py \
  --source /tmp/code-travail-snapshot.json --livre I --as-of 2026-11-11 \
  --output /tmp/golden-set-reproduit.csv \
  --titles-output /tmp/golden-set-titres-reproduit.csv
```

La génération reproduit le tirage et les textes **sans les annotations**
ajoutées ultérieurement. Le script accepte aussi un dossier XML LEGI ou une
archive LEGI complète.
Il échoue si moins de 100 articles distincts sont éligibles, si les données sont
contradictoires ou si le fichier de sortie existe déjà : les annotations ne
sont jamais écrasées. Pour reproduire le même résultat, conserver la source,
le livre et la date ; le défaut de `--as-of` est la date du jour.

## Évaluation des extractions

Après annotation et extraction des mêmes versions d'articles, lancer depuis
`pipeline/` avec des identifiants BigQuery configurés :

```sh
uv run python -m vil_pipeline.cli evaluate-extraction \
  --model NOM_DU_MODELE --version-prompt HASH_DU_PROMPT
```

Le job lit les résultats `SUCCESS` dans `ops.extraction_results` pour le modèle
et le hash indiqués. Il exige un résultat unique pour chaque article annoté :
un résultat absent, dupliqué, invalide ou en quarantaine interrompt l'évaluation.
Les articles non annotés sont exclus et comptabilisés ; aucune évaluation n'est
produite si aucun article n'est annoté. Le rapport Markdown est créé dans
`docs/05-ia/evaluations/` sans écraser un rapport existant. Les options `--golden`,
`--titles` et `--output` permettent de changer les chemins.

Les notions sont comparées par article comme des ensembles : minuscules, accents
supprimés et espaces normalisés ; le pluriel simple retire le `s` final des mots
de plus de trois lettres sauf `ss`, `us`, `is`, ainsi que le `x` final de `eaux`.
Cette heuristique ne constitue pas une lemmatisation complète. Les doublons sont
ignorés. Précision, rappel et F1 sont calculés par agrégation micro des vrais
positifs, faux positifs et faux négatifs, globalement et par identifiant de titre.
Une métrique de dénominateur nul est affichée `N/D`. Le rapport indique les
empreintes des entrées, la couverture et la version du modèle et du prompt.