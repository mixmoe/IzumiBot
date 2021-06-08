from typing import List, Optional

from pydantic import AnyHttpUrl, BaseModel, Field, Extra


class InfoModel(BaseModel):
    class Config:
        extra = Extra.allow


class AniListTitle(InfoModel):
    native: str
    romaji: Optional[str] = None
    english: Optional[str] = None


class AniListInfo(InfoModel):
    id: int
    idMal: Optional[int] = None
    title: AniListTitle
    synonyms: List[str]
    isAdult: bool


class AnimeResultItem(InfoModel):
    anilist: AniListInfo
    episode: Optional[int] = None
    filename: str
    from_: float = Field(alias="from")
    to: float
    image: AnyHttpUrl
    video: AnyHttpUrl
    similarity: float


class AnimeResult(InfoModel):
    error: str
    frameCount: Optional[int] = None
    result: List[AnimeResultItem] = []
