from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.models import User
from app.core.auth import get_current_user
from app.services.recommendation import RecommendationService

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])


@router.get("/")
async def get_recommendations(
        content_type: Optional[str] = Query(None, regex="^(book|movie|game)$"),
        limit: int = Query(10, ge=1, le=50),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Получение персональных рекомендаций"""
    rec_service = RecommendationService(db)
    recommendations = rec_service.get_recommendations(
        user_id=current_user.user_id,
        content_type=content_type,
        limit=limit
    )

    # Форматируем результат
    formatted_recs = []
    for rec in recommendations:
        content = rec["content"]
        formatted_recs.append({
            "type": rec["type"],
            "content": content,
            "match_score": rec["score"],
            "recommendation_reason": f"Совпадение по тегам: {rec['score']:.1%}"
        })

    return {
        "recommendations": formatted_recs,
        "user_preferences": rec_service.get_user_preferences(current_user.user_id)
    }


@router.get("/similar/{content_type}/{content_id}")
async def get_similar_content(
        content_type: str,
        content_id: int,
        limit: int = Query(5, ge=1, le=20),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Получение похожего контента"""
    rec_service = RecommendationService(db)

    # Получаем исходный контент
    original_content = rec_service.get_content_by_interaction_type(content_type, content_id)
    if not original_content:
        raise HTTPException(status_code=404, detail="Content not found")

    # Находим похожий контент по тегам
    similar = rec_service.find_similar_content(
        content_type=content_type,
        tags=original_content.tags or [],
        exclude_id=content_id,
        limit=limit
    )

    return {
        "original": original_content,
        "similar": similar
    }


@router.get("/trending")
async def get_trending_content(
        content_type: Optional[str] = Query(None, regex="^(book|movie|game)$"),
        period: str = Query("week", regex="^(day|week|month|year)$"),
        limit: int = Query(10, ge=1, le=50),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Получение трендового контента"""
    rec_service = RecommendationService(db)
    trending = rec_service.get_trending_content(
        content_type=content_type,
        period=period,
        limit=limit
    )

    return {
        "trending": trending,
        "period": period
    }


@router.post("/feedback")
async def provide_recommendation_feedback(
        content_type: str,
        content_id: int,
        helpful: bool,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Обратная связь по рекомендациям"""
    # Здесь можно сохранить фидбек для улучшения алгоритма
    return {
        "message": "Спасибо за обратную связь!",
        "content_type": content_type,
        "content_id": content_id,
        "helpful": helpful
    }