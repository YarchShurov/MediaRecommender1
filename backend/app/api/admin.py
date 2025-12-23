from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import User
from app.schemas import UserResponse
from app.core.auth import require_admin

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/users", response_model=List[UserResponse])
async def get_all_users(
        db: Session = Depends(get_db),
        admin_user: User = Depends(require_admin)
):
    """Получение списка всех пользователей (только для администраторов)"""
    users = db.query(User).all()
    return users


@router.post("/users/{user_id}/block")
async def block_user(
        user_id: int,
        db: Session = Depends(get_db),
        admin_user: User = Depends(require_admin)
):
    """Блокировка пользователя (только для администраторов)"""
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.user_id == admin_user.user_id:
        raise HTTPException(status_code=400, detail="Cannot block yourself")

    user.is_active = False
    db.commit()
    return {"message": f"User {user.username} has been blocked"}


@router.post("/users/{user_id}/unblock")
async def unblock_user(
        user_id: int,
        db: Session = Depends(get_db),
        admin_user: User = Depends(require_admin)
):
    """Разблокировка пользователя (только для администраторов)"""
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = True
    db.commit()
    return {"message": f"User {user.username} has been unblocked"}


@router.put("/users/{user_id}/preferences")
async def update_user_preferences(
        user_id: int,
        preferences: dict,
        db: Session = Depends(get_db),
        admin_user: User = Depends(require_admin)
):
    """Обновление предпочтений пользователя (только для администраторов)"""
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.preferences = preferences
    db.commit()
    return {"message": "User preferences updated successfully"}