# ADR-0004 : Choix du fournisseur LLM

## Contexte

Le produit utilise un modèle de langage pour l'extraction de notions juridiques. Un fournisseur doit être choisi afin d'intégrer cette capacité et de tracer les modèles et versions de prompts utilisés.

## Décision

Choisir Gemini comme fournisseur de modèle de langage pour les traitements d'extraction.

## Alternatives

- Choisir un autre fournisseur de modèle de langage.
- Héberger et exploiter un modèle en propre.

Ces alternatives ne sont pas retenues.

## Conséquences

- Les traitements d'extraction s'appuient sur Gemini.
- Les versions du modèle et des prompts doivent être tracées pour assurer la reproductibilité des résultats.
- Le produit dépend du fournisseur pour la disponibilité, les conditions d'utilisation et les coûts du service.
- Les exigences de protection des données et de conformité, notamment les accords de traitement et les éventuels transferts hors UE, doivent être vérifiées.

## Statut

Accepté
