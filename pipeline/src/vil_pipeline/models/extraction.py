"""Models for AI-extracted legal notions."""

from typing import Annotated

from pydantic import BaseModel, Field

from vil_pipeline.models.corpus import LegifranceArticleId


class NotionExtraite(BaseModel):
	"""A legal notion extracted from an article version."""

	libelle: str = Field(min_length=1)
	definition_courte: str = Field(min_length=1)
	situations_de_vie: list[str]
	confiance: Annotated[float, Field(ge=0, le=1)]
	citation_article: str = Field(min_length=1)


class ResultatExtraction(BaseModel):
	"""All extracted notions associated with an article version."""

	article_version_id: LegifranceArticleId
	notions: list[NotionExtraite]
