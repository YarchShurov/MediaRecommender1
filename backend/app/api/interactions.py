from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
from app.database import get_db
from app.models import User, UserInteraction
from app.schemas import InteractionResponse
from app.core.auth import get_current_user

router = APIRouter(prefix="/interactions", tags=["User Interactions"])


@router.get("/", response_model=List[InteractionResponse])
async def get_user_interactions(
        content_type: Optional[str] = Query(None, regex="^(book|movie|game)$"),
        interaction_type: Optional[str] = Query(None, regex="^(started|completed|rated|dropped)$"),
        limit: int = Query(20, ge=1, le=100),
        skip: int = Query(0, ge=0),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Получение истории взаимодействий пользователя"""
    query = db.query(UserInteraction).filter(UserInteraction.user_id == current_user.user_id)

    if content_type:
        query = query.filter(UserInteraction.content_type == content_type)

    if interaction_type:
        query = query.filter(UserInteraction.interaction_type == interaction_type)

    interactions = query.order_by(UserInteraction.start_date.desc()) \
        .offset(skip) \
        .limit(limit) \
        .all()

    return interactions


@router.get("/stats")
async def get_user_stats(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Получение статистики пользователя"""
    interactions = db.query(UserInteraction) \
        .filter(UserInteraction.user_id == current_user.user_id) \
        .all()

    stats = {
        "total_interactions": len(interactions),
        "completed": len([i for i in interactions if i.interaction_type == "completed"]),
        "dropped": len([i for i in interactions if i.interaction_type == "dropped"]),
        "average_rating": 0,
        "total_time_spent": 0,
        "by_content_type": {"book": 0, "movie": 0, "game": 0},
        "recent_activity": []
    }

    completed_interactions = [i for i in interactions if i.interaction_type == "completed"]

    if completed_interactions:
        ratings = [i.rating for i in completed_interactions if i.rating]
        if ratings:
            stats["average_rating"] = round(sum(ratings) / len(ratings), 2)

        durations = [i.simulation_duration for i in completed_interactions if i.simulation_duration]
        if durations:
            stats["total_time_spent"] = sum(durations)

    # Статистика по типам контента
    for interaction in completed_interactions:
        stats["by_content_type"][interaction.content_type] += 1

    # Недавняя активность (последние 7 дней)
    week_ago = datetime.utcnow() - timedelta(days=7)
    recent = [i for i in interactions if i.start_date >= week_ago]
    stats["recent_activity"] = len(recent)

    return stats


@router.get("/library")
async def get_user_library(
        status: str = Query("all", regex="^(all|reading|completed|dropped|planned)$"),
        content_type: Optional[str] = Query(None, regex="^(book|movie|game)$"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Получение личной библиотеки пользователя"""
    query = db.query(UserInteraction).filter(UserInteraction.user_id == current_user.user_id)

    if content_type:
        query = query.filter(UserInteraction.content_type == content_type)

    if status != "all":
        status_mapping = {
            "reading": "started",
            "completed": "completed",
            "dropped": "dropped",
            "planned": "planned"
        }
        query = query.filter(UserInteraction.interaction_type == status_mapping[status])

    interactions = query.order_by(UserInteraction.start_date.desc()).all()

    # Группируем по статусу
    library = {
        "reading": [],
        "completed": [],
        "dropped": [],
        "planned": []
    }

    status_reverse_mapping = {
        "started": "reading",
        "completed": "completed",
        "dropped": "dropped",
        "planned": "planned"
    }

    for interaction in interactions:
        status_key = status_reverse_mapping.get(interaction.interaction_type, "reading")
        library[status_key].append(interaction)

    return library


@router.delete("/{interaction_id}")
async def delete_interaction(
        interaction_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Удаление взаимодействия из истории"""
    interaction = db.query(UserInteraction) \
        .filter(UserInteraction.interaction_id == interaction_id) \
        .filter(UserInteraction.user_id == current_user.user_id) \
        .first()

    if not interaction:
        raise HTTPException(status_code=404, detail="Interaction not found")

    db.delete(interaction)
    db.commit()

    return {"message": "Interaction deleted successfully"}