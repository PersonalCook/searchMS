from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    detail: str


class RecipeSource(BaseModel):
    recipe_id: Optional[int] = None
    recipe_name: Optional[str] = None
    user_id: Optional[int] = None
    visibility: Optional[str] = None
    category: Optional[str] = None
    total_time: Optional[int] = None

    class Config:
        extra = "allow"


class RecipeHit(BaseModel):
    id: str
    score: Optional[float] = None
    recipe: RecipeSource


class SearchResults(BaseModel):
    results: List[RecipeHit]


class UserSummary(BaseModel):
    user_id: int
    username: str

    class Config:
        extra = "allow"


class RootResponse(BaseModel):
    msg: str


class HealthResponse(BaseModel):
    status: str
