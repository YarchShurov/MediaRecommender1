from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import User
from app.core.auth import get_current_user
from app.services.simulation import SimulationService
from app.schemas import SimulationStart, SimulationComplete

router = APIRouter(prefix="/simulation", tags=["Simulation"])

# Глобальный экземпляр сервиса симуляции
simulation_service = None


def get_simulation_service(db: Session = Depends(get_db)) -> SimulationService:
    global simulation_service
    if simulation_service is None:
        simulation_service = SimulationService(db)
    simulation_service.db = db  # Обновляем сессию БД
    return simulation_service


@router.post("/start")
async def start_simulation(
        simulation_data: SimulationStart,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
        sim_service: SimulationService = Depends(get_simulation_service)
):
    """Начать симуляцию чтения/просмотра/игры"""
    try:
        result = await sim_service.start_simulation(
            user_id=current_user.user_id,
            content_type=simulation_data.content_type,
            content_id=simulation_data.content_id
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/progress/{simulation_id}")
async def get_simulation_progress(
        simulation_id: str,
        sim_service: SimulationService = Depends(get_simulation_service)
):
    """Получить прогресс симуляции"""
    try:
        progress = await sim_service.get_simulation_progress(simulation_id)
        return progress
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/complete/{simulation_id}")
async def complete_simulation(
        simulation_id: str,
        completion_data: SimulationComplete,
        background_tasks: BackgroundTasks,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
        sim_service: SimulationService = Depends(get_simulation_service)
):
    """Завершить симуляцию с оценкой"""
    try:
        result = await sim_service.complete_simulation(
            simulation_id=simulation_id,
            rating=completion_data.rating,
            personal_tags=completion_data.personal_tags
        )

        # В фоне обновляем рекомендации пользователя
        background_tasks.add_task(update_user_recommendations, current_user.user_id, db)

        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/cancel/{simulation_id}")
async def cancel_simulation(
        simulation_id: str,
        current_user: User = Depends(get_current_user),
        sim_service: SimulationService = Depends(get_simulation_service)
):
    """Отменить симуляцию"""
    try:
        result = await sim_service.cancel_simulation(simulation_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/active")
async def get_active_simulations(
        current_user: User = Depends(get_current_user),
        sim_service: SimulationService = Depends(get_simulation_service)
):
    """Получить активные симуляции пользователя"""
    user_simulations = []
    for sim_id, sim_data in sim_service.active_simulations.items():
        if sim_data["user_id"] == current_user.user_id:
            progress = await sim_service.get_simulation_progress(sim_id)
            user_simulations.append({
                "simulation_id": sim_id,
                "content_title": sim_data["content_title"],
                "content_type": sim_data["content_type"],
                "progress": progress["progress"],
                "start_time": sim_data["start_time"]
            })

    return {"active_simulations": user_simulations}


async def update_user_recommendations(user_id: int, db: Session):
    """Фоновая задача для обновления рекомендаций после завершения симуляции"""
    from app.services.recommendation import RecommendationService
    rec_service = RecommendationService(db)
    # Здесь можно добавить логику предварительного расчета рекомендаций
    pass