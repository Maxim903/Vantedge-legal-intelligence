"""Models for the versioned legal corpus."""

from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, Field, model_validator

LegifranceArticleId = Annotated[str, Field(pattern=r"^LEGIARTI[0-9]{12}$")]


class Article(BaseModel):
	"""A legal article independent of its versions."""

	article_id: LegifranceArticleId
	numero: str
	code_id: str
	livre: str
	titre: str
	chapitre: str
	livre_id: str | None = None
	titre_id: str | None = None
	chapitre_id: str | None = None


class ArticleVersion(BaseModel):
	"""A version of a legal article with its validity period."""

	article_version_id: LegifranceArticleId
	article_id: LegifranceArticleId
	texte: str
	etat: Literal["VIGUEUR", "MODIFIE", "ABROGE"]
	date_debut: date
	date_fin: date | None = None

	@model_validator(mode="after")
	def validate_date_range(self) -> "ArticleVersion":
		if self.date_fin is not None and self.date_fin < self.date_debut:
			raise ValueError("date_fin must be greater than or equal to date_debut")
		return self
