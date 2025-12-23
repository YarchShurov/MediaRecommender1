from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime


class UserBase(BaseModel):
    username: str
    email: EmailStr


class UserCreate(UserBase):
    password: str
    role_id: Optional[int] = 2  # По умолчанию роль "user"


class UserResponse(UserBase):
    user_id: int
    role_id: int
    created_at: datetime
    is_active: bool

    class Config:
        from_attributes = True


class ContentBase(BaseModel):
    title: str
    genre: Optional[str] = None
    year: Optional[int] = None
    description: Optional[str] = None
    tags: List[str] = []


class BookCreate(ContentBase):
    author: str


class MovieCreate(ContentBase):
    director: str


class GameCreate(ContentBase):
    developer: str


class BookResponse(BookCreate):
    book_id: int
    popularity_score: float
    created_at: datetime

    class Config:
        from_attributes = True


class MovieResponse(MovieCreate):
    movie_id: int
    popularity_score: float
    created_at: datetime

    class Config:
        from_attributes = True


class GameResponse(GameCreate):
    game_id: int
    popularity_score: float
    created_at: datetime

    class Config:
        from_attributes = True


class InteractionCreate(BaseModel):
    content_type: str
    content_id: int
    interaction_type: str
    rating: Optional[int] = None


class InteractionResponse(InteractionCreate):
    interaction_id: int
    user_id: int
    progress_percent: int
    start_date: datetime
    completion_date: Optional[datetime] = None
    simulation_duration: Optional[int] = None

    class Config:
        from_attributes = True


class SimulationStart(BaseModel):
    content_type: str
    content_id: int


class SimulationComplete(BaseModel):
    rating: int
    personal_tags: List[str] = []