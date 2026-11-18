"""Export the graph's source data from BigQuery marts in cursor-backed batches."""

from collections.abc import Iterator
from datetime import date
from typing import Literal

from google.cloud import bigquery
from pydantic import BaseModel, ConfigDict


class GraphRow(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Code(GraphRow):
    code_id: str
    legifrance_id: str
    libelle: str
    ordre: int


class Livre(GraphRow):
    livre_id: str
    code_id: str
    legifrance_id: str
    libelle: str | None
    ordre: int


class Titre(GraphRow):
    titre_id: str
    livre_id: str
    legifrance_id: str
    libelle: str | None
    ordre: int


class Chapitre(GraphRow):
    chapitre_id: str
    titre_id: str


class Article(GraphRow):
    article_id: str
    chapitre_id: str | None
    numero: str


class ArticleVersion(GraphRow):
    article_version_id: str
    article_id: str
    date_debut: date
    date_fin: date | None
    etat: Literal["VIGUEUR", "MODIFIE", "ABROGE"]
    texte_ref: str | None


class Notion(GraphRow):
    notion_id: str
    libelle: str
    definition_courte: str | None
    score_confiance: float


class SituationDeVie(GraphRow):
    situation_id: str
    libelle: str


class Requete(GraphRow):
    requete_id: str
    texte: str
    pays_langue_id: str
    intention_type: str | None


class Intention(GraphRow):
    type: Literal[
        "informationnelle", "transactionnelle", "navigationnelle", "commerciale"
    ]


class PaysLangue(GraphRow):
    pays_langue_id: str
    pays: str
    langue: str


class Extraction(GraphRow):
    extraction_id: str
    article_version_id: str
    notion_id: str


class NotionRequete(GraphRow):
    notion_id: str
    requete_id: str
    score_rattachement: float


class Metrique(GraphRow):
    requete_id: str
    pays_langue_id: str
    mois: date
    volume: int | None
    cpc: float | None
    concurrence: float | None


class ResultatSERP(GraphRow):
    requete_id: str
    pays_langue_id: str
    date_resultat: date
    position: int
    domaine: str | None
    url: str | None


class ArticleRenvoi(GraphRow):
    article_source_id: str
    type_relation: Literal["RENVOIE_A", "MODIFIE", "ABROGE"]
    article_cible_id: str


class NotionSituation(GraphRow):
    notion_id: str
    situation_id: str


type GraphSourceRow = (
    Code
    | Livre
    | Titre
    | Chapitre
    | Article
    | ArticleVersion
    | Notion
    | SituationDeVie
    | Requete
    | Intention
    | PaysLangue
    | Extraction
    | NotionRequete
    | Metrique
    | ResultatSERP
    | ArticleRenvoi
    | NotionSituation
)


TABLE_MODELS: dict[str, type[GraphSourceRow]] = {
    "dim_code": Code,
    "dim_livre": Livre,
    "dim_titre": Titre,
    "dim_chapitre": Chapitre,
    "dim_article": Article,
    "dim_article_version": ArticleVersion,
    "dim_notion": Notion,
    "dim_situation_vie": SituationDeVie,
    "dim_requete": Requete,
    "dim_intention": Intention,
    "dim_pays_langue": PaysLangue,
    "fait_extraction": Extraction,
    "fait_notion_requete": NotionRequete,
    "fait_metrique_mensuelle": Metrique,
    "fait_resultat_serp": ResultatSERP,
    "pont_article_renvoi": ArticleRenvoi,
    "pont_notion_situation": NotionSituation,
}


class ExportBatch(BaseModel):
    table: str
    rows: list[GraphSourceRow]
    next_page_token: str | None


def iter_table_batches(
    client: bigquery.Client,
    dataset: bigquery.DatasetReference,
    table_name: str,
    *,
    batch_size: int = 1000,
    page_token: str | None = None,
) -> Iterator[ExportBatch]:
    """Read one supported table; page_token resumes at a BigQuery page boundary."""
    if batch_size <= 0:
        raise ValueError("batch_size must be positive.")
    if page_token is not None and not page_token:
        raise ValueError("page_token must not be empty.")
    if table_name not in TABLE_MODELS:
        raise ValueError(f"Unsupported graph source table: {table_name}")
    model = TABLE_MODELS[table_name]
    table = client.get_table(dataset.table(table_name))
    fields = model.model_fields.keys()
    selected_fields = [field for field in table.schema if field.name in fields]
    missing = fields - {field.name for field in selected_fields}
    if missing:
        raise ValueError(
            f"Missing columns in {table_name}: {', '.join(sorted(missing))}"
        )

    iterator = client.list_rows(
        table,
        selected_fields=selected_fields,
        page_size=batch_size,
        page_token=page_token,
    )
    for page in iterator.pages:
        rows = [model.model_validate(dict(row.items())) for row in page]
        if rows:
            yield ExportBatch(
                table=table_name, rows=rows, next_page_token=iterator.next_page_token
            )


def iter_batches(
    client: bigquery.Client,
    dataset: bigquery.DatasetReference,
    *,
    batch_size: int = 1000,
) -> Iterator[ExportBatch]:
    """Read every source table, including rows not linked to another graph node."""
    for table_name in TABLE_MODELS:
        yield from iter_table_batches(
            client, dataset, table_name, batch_size=batch_size
        )
