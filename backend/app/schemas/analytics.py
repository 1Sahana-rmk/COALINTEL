from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict


class WordCloudTopicItem(BaseModel):
    word: str
    weight: int
    category: str
    occurrence_count: Optional[int] = None
    document_count: Optional[int] = None
    score: Optional[float] = None


class WordCloudResponse(BaseModel):
    topics: List[WordCloudTopicItem]
    status: str = "OK"
    corpus_items: int = 0
    method: str = "persisted_content_frequency"

    model_config = ConfigDict(from_attributes=True)


class TopicResponse(BaseModel):
    topics: List[Dict[str, Any]]
    status: str = "OK"
    method: str = "deterministic_cooccurrence"
    corpus_items: int = 0


class TrendResponse(BaseModel):
    status: str
    metric: Optional[str] = None
    points: List[Dict[str, Any]] = []
    count: int = 0
    all_years_not_summed: bool = True
    reason: Optional[str] = None


class HistoricalResponse(BaseModel):
    status: str
    observations: List[Dict[str, Any]] = []
    provenance_fact_ids: List[int] = []
    all_years_not_summed: bool = True
    reason: Optional[str] = None
