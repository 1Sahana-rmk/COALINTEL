from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database import get_db
from app.models.user import User
from app.core.rbac import get_current_user
from app.schemas.analytics import HistoricalResponse, TopicResponse, TrendResponse, WordCloudResponse
from app.services.corpus_intelligence_service import historical_comparison, topics, trend_series, word_cloud

router = APIRouter(tags=["Analytics & Topic Intelligence"])


@router.get("/analytics/wordcloud", response_model=WordCloudResponse)
def get_wordcloud_analytics(
    subsidiary_filter: Optional[str] = None,
    document_id: Optional[int] = None,
    period: Optional[str] = None,
    top_n: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return word_cloud(db, subsidiary=subsidiary_filter, document_id=document_id, period=period, top_n=top_n)


@router.get("/analytics/topics", response_model=TopicResponse)
def get_topics(
    subsidiary_filter: Optional[str] = None,
    document_id: Optional[int] = None,
    period: Optional[str] = None,
    top_n: int = Query(12, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return topics(db, subsidiary=subsidiary_filter, document_id=document_id, period=period, top_n=top_n)


@router.get("/analytics/trends", response_model=TrendResponse)
def get_trends(
    metric: str,
    entity: Optional[str] = None,
    subsidiary: Optional[str] = None,
    period: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return trend_series(db, metric=metric, entity=entity, subsidiary=subsidiary, period=period)


@router.get("/analytics/historical", response_model=HistoricalResponse)
def get_historical_comparison(
    metric: str,
    entity: Optional[str] = None,
    comparison_entity: Optional[str] = None,
    period: Optional[str] = None,
    subsidiary: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return historical_comparison(db, metric=metric, entity=entity, comparison_entity=comparison_entity,
                                 period=period, subsidiary=subsidiary)
