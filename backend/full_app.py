from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, OAuth2PasswordRequestForm
from sqlalchemy import create_engine, Column, Integer, String, Float, JSON, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from sqlalchemy.sql import func
from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict, Union
from datetime import datetime, timedelta
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import random
import hashlib

# Настройка базы данных (SQLite для простоты)
DATABASE_URL = "sqlite:///./mediarecommender_full.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# === МОДЕЛИ БАЗЫ ДАННЫХ ===

class User(Base):
    __tablename__ = "users"
    user_id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role_id = Column(Integer, default=2)  # 1=admin, 2=user
    created_at = Column(DateTime, server_default=func.now())
    preferences = Column(JSON, default='{"popularity": 50, "newness": 50}')
    is_active = Column(Boolean, default=True)

    interactions = relationship("UserInteraction", back_populates="user")


class Book(Base):
    __tablename__ = "books"
    book_id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    author = Column(String(255), nullable=False)
    genres = Column(JSON, default='[]')  # Изменено с genre на genres (массив)
    year = Column(Integer)
    popularity_score = Column(Float, default=5.0)
    description = Column(Text)
    tags = Column(JSON, default='[]')
    created_at = Column(DateTime, server_default=func.now())

class Movie(Base):
    __tablename__ = "movies"
    movie_id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    director = Column(String(255), nullable=False)
    genres = Column(JSON, default='[]')  # Изменено с genre на genres (массив)
    year = Column(Integer)
    popularity_score = Column(Float, default=5.0)
    description = Column(Text)
    tags = Column(JSON, default='[]')
    created_at = Column(DateTime, server_default=func.now())

class Game(Base):
    __tablename__ = "games"
    game_id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    developer = Column(String(255), nullable=False)
    genres = Column(JSON, default='[]')  # Изменено с genre на genres (массив)
    year = Column(Integer)
    popularity_score = Column(Float, default=5.0)
    description = Column(Text)
    tags = Column(JSON, default='[]')
    created_at = Column(DateTime, server_default=func.now())

class UserInteraction(Base):
    __tablename__ = "user_interactions"
    interaction_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"))
    content_type = Column(String(20), nullable=False)  # 'book', 'movie', 'game'
    content_id = Column(Integer, nullable=False)
    interaction_type = Column(String(20), nullable=False)  # 'started', 'completed', 'dropped'
    rating = Column(Integer)  # 1-10
    progress_percent = Column(Integer, default=0)
    start_date = Column(DateTime, server_default=func.now())
    completion_date = Column(DateTime)
    simulation_duration = Column(Integer)  # в секундах

    user = relationship("User", back_populates="interactions")


# === PYDANTIC СХЕМЫ ===

class UserCreate(BaseModel):
    username: str
    email: str
    password: str


class UserResponse(BaseModel):
    user_id: int
    username: str
    email: str
    role_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class ContentResponse(BaseModel):
    id: int
    title: str
    creator: str  # author/director/developer
    genre: Optional[str] = None
    year: Optional[int] = None
    popularity_score: float
    description: Optional[str] = None
    tags: List[str] = []
    content_type: str

    class Config:
        from_attributes = True


class SimulationStart(BaseModel):
    content_type: str
    content_id: int


class SimulationComplete(BaseModel):
    rating: int


# Создание таблиц
Base.metadata.create_all(bind=engine)


# === СЕРВИСЫ ===

class AuthService:
    @staticmethod
    def hash_password(password: str) -> str:
        return hashlib.sha256(password.encode()).hexdigest()

    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        return hashlib.sha256(password.encode()).hexdigest() == hashed

    @staticmethod
    def create_token(user_id: int) -> str:
        return f"token_{user_id}_{datetime.now().timestamp()}"


class SimulationService:
    def __init__(self):
        self.active_simulations = {}
        self.simulation_times = {
            'book': {'min': 10, 'max': 30},  # 10-30 секунд для демо
            'movie': {'min': 5, 'max': 15},  # 5-15 секунд
            'game': {'min': 15, 'max': 45}  # 15-45 секунд
        }

    async def start_simulation(self, user_id: int, content_type: str, content_id: int, db: Session):
        # Создаем запись о начале
        interaction = UserInteraction(
            user_id=user_id,
            content_type=content_type,
            content_id=content_id,
            interaction_type="started",
            progress_percent=0
        )
        db.add(interaction)
        db.commit()
        db.refresh(interaction)

        # Определяем время симуляции
        time_range = self.simulation_times[content_type]
        simulation_time = random.randint(time_range['min'], time_range['max'])

        # Получаем название контента
        content = self.get_content(content_type, content_id, db)
        content_title = content.title if content else "Unknown"

        sim_id = f"{user_id}_{content_type}_{content_id}"
        self.active_simulations[sim_id] = {
            "interaction_id": interaction.interaction_id,
            "user_id": user_id,
            "content_type": content_type,
            "content_id": content_id,
            "content_title": content_title,
            "start_time": datetime.now(),
            "total_time": simulation_time,
            "progress": 0
        }

        return {
            "simulation_id": sim_id,
            "estimated_time": simulation_time,
            "content_title": content_title,
            "message": f"Начинаем {self.get_action_verb(content_type)} '{content_title}'!"
        }

    def get_progress(self, simulation_id: str):
        if simulation_id not in self.active_simulations:
            raise ValueError("Simulation not found")

        sim = self.active_simulations[simulation_id]
        elapsed = (datetime.now() - sim["start_time"]).total_seconds()
        progress = min(100, int((elapsed / sim["total_time"]) * 100))
        sim["progress"] = progress

        return {
            "progress": progress,
            "completed": progress >= 100,
            "content_title": sim["content_title"],
            "elapsed_time": int(elapsed)
        }

    def complete_simulation(self, simulation_id: str, rating: int, db: Session):
        if simulation_id not in self.active_simulations:
            raise ValueError("Simulation not found")

        sim = self.active_simulations[simulation_id]

        # Обновляем взаимодействие
        interaction = db.query(UserInteraction).filter(
            UserInteraction.interaction_id == sim["interaction_id"]
        ).first()

        if interaction:
            interaction.interaction_type = "completed"
            interaction.rating = rating
            interaction.progress_percent = 100
            interaction.completion_date = datetime.now()
            interaction.simulation_duration = int((datetime.now() - sim["start_time"]).total_seconds())
            db.commit()

        # Удаляем из активных
        del self.active_simulations[simulation_id]

        return {
            "message": f"Вы завершили {self.get_action_verb(sim['content_type'])} '{sim['content_title']}'!",
            "rating": rating,
            "experience": rating * 10
        }

    def get_content(self, content_type: str, content_id: int, db: Session):
        if content_type == "book":
            return db.query(Book).filter(Book.book_id == content_id).first()
        elif content_type == "movie":
            return db.query(Movie).filter(Movie.movie_id == content_id).first()
        elif content_type == "game":
            return db.query(Game).filter(Game.game_id == content_id).first()
        return None

    def get_action_verb(self, content_type: str) -> str:
        verbs = {"book": "чтение", "movie": "просмотр", "game": "игру"}
        return verbs.get(content_type, "взаимодействие")


# === FASTAPI ПРИЛОЖЕНИЕ ===

app = FastAPI(title="MediaRecommender Full", version="2.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене укажите конкретные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
security = HTTPBearer()
auth_service = AuthService()
simulation_service = SimulationService()


# Зависимости
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    token = credentials.credentials
    if not token.startswith("token_"):
        raise HTTPException(status_code=401, detail="Invalid token")

    try:
        user_id = int(token.split("_")[1])
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except:
        raise HTTPException(status_code=401, detail="Invalid token")

def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role_id != 1:  # 1 = admin
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user

# === API ЭНДПОИНТЫ ===

@app.get("/")
def root():
    return {
        "message": "MediaRecommender Full API",
        "version": "2.0.0",
        "features": ["auth", "simulation", "recommendations"],
        "endpoints": {
            "auth": "/auth/register, /auth/login",
            "content": "/content/books, /content/movies, /content/games",
            "simulation": "/simulation/start, /simulation/progress, /simulation/complete"
        }
    }


# Авторизация
@app.post("/auth/register", response_model=UserResponse)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    # Проверяем существование пользователя
    existing = db.query(User).filter(
        (User.username == user_data.username) | (User.email == user_data.email)
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="User already exists")

    # Создаем пользователя
    user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=auth_service.hash_password(user_data.password)
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.post("/auth/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not auth_service.verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = auth_service.create_token(user.user_id)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "user_id": user.user_id,
            "username": user.username,
            "role_id": user.role_id
        }
    }

@app.get("/auth/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@app.post("/auth/create-admin")
async def create_admin(username: str, password: str, db: Session = Depends(get_db)):
    """Создание администратора (только для первого запуска)"""
    # Проверяем, есть ли уже администраторы
    existing_admin = db.query(User).filter(User.role_id == 1).first()
    if existing_admin:
        raise HTTPException(status_code=400, detail="Admin already exists")

    admin = User(
        username=username,
        email=f"{username}@admin.com",
        password_hash=auth_service.hash_password(password),
        role_id=1  # Роль администратора
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)

    return {"message": f"Admin '{username}' created successfully"}

# Контент
# Контент
@app.get("/content/books")
def get_books(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        books = db.query(Book).all()
        result = []
        for book in books:
            # Обрабатываем жанры (поддержка старого и нового формата)
            genres = []
            if hasattr(book, 'genres') and book.genres:
                if isinstance(book.genres, list):
                    genres = book.genres
                elif isinstance(book.genres, str):
                    try:
                        import json
                        genres = json.loads(book.genres)
                    except:
                        genres = [book.genres]
            elif hasattr(book, 'genre') and book.genre:
                genres = [book.genre]

            result.append({
                "id": book.book_id,
                "title": book.title,
                "creator": book.author,
                "genres": genres,
                "genre": genres[0] if genres else None,  # Для обратной совместимости
                "year": book.year,
                "popularity_score": book.popularity_score,
                "description": book.description,
                "tags": book.tags if isinstance(book.tags, list) else [],
                "content_type": "book"
            })
        return result
    except Exception as e:
        print(f"Ошибка загрузки книг: {e}")
        raise HTTPException(status_code=500, detail=f"Error loading books: {str(e)}")


@app.get("/content/movies")
def get_movies(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        movies = db.query(Movie).all()
        result = []
        for movie in movies:
            # Обрабатываем жанры
            genres = []
            if hasattr(movie, 'genres') and movie.genres:
                if isinstance(movie.genres, list):
                    genres = movie.genres
                elif isinstance(movie.genres, str):
                    try:
                        import json
                        genres = json.loads(movie.genres)
                    except:
                        genres = [movie.genres]
            elif hasattr(movie, 'genre') and movie.genre:
                genres = [movie.genre]

            result.append({
                "id": movie.movie_id,
                "title": movie.title,
                "creator": movie.director,
                "genres": genres,
                "genre": genres[0] if genres else None,
                "year": movie.year,
                "popularity_score": movie.popularity_score,
                "description": movie.description,
                "tags": movie.tags if isinstance(movie.tags, list) else [],
                "content_type": "movie"
            })
        return result
    except Exception as e:
        print(f"Ошибка загрузки фильмов: {e}")
        raise HTTPException(status_code=500, detail=f"Error loading movies: {str(e)}")


@app.get("/content/games")
def get_games(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        games = db.query(Game).all()
        result = []
        for game in games:
            # Обрабатываем жанры
            genres = []
            if hasattr(game, 'genres') and game.genres:
                if isinstance(game.genres, list):
                    genres = game.genres
                elif isinstance(game.genres, str):
                    try:
                        import json
                        genres = json.loads(game.genres)
                    except:
                        genres = [game.genres]
            elif hasattr(game, 'genre') and game.genre:
                genres = [game.genre]

            result.append({
                "id": game.game_id,
                "title": game.title,
                "creator": game.developer,
                "genres": genres,
                "genre": genres[0] if genres else None,
                "year": game.year,
                "popularity_score": game.popularity_score,
                "description": game.description,
                "tags": game.tags if isinstance(game.tags, list) else [],
                "content_type": "game"
            })
        return result
    except Exception as e:
        print(f"Ошибка загрузки игр: {e}")
        raise HTTPException(status_code=500, detail=f"Error loading games: {str(e)}")

# Симуляция
@app.post("/simulation/start")
async def start_simulation(
        sim_data: SimulationStart,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    try:
        result = await simulation_service.start_simulation(
            user_id=current_user.user_id,
            content_type=sim_data.content_type,
            content_id=sim_data.content_id,
            db=db
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/simulation/progress/{simulation_id}")
def get_simulation_progress(simulation_id: str):
    try:
        return simulation_service.get_progress(simulation_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/simulation/complete/{simulation_id}")
def complete_simulation(
        simulation_id: str,
        completion: SimulationComplete,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    try:
        return simulation_service.complete_simulation(simulation_id, completion.rating, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# Статистика пользователя
@app.get("/user/stats")
def get_user_stats(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    interactions = db.query(UserInteraction).filter(UserInteraction.user_id == current_user.user_id).all()

    completed = [i for i in interactions if i.interaction_type == "completed"]
    ratings = [i.rating for i in completed if i.rating]

    return {
        "total_interactions": len(interactions),
        "completed": len(completed),
        "average_rating": round(sum(ratings) / len(ratings), 2) if ratings else 0,
        "by_content_type": {
            "books": len([i for i in completed if i.content_type == "book"]),
            "movies": len([i for i in completed if i.content_type == "movie"]),
            "games": len([i for i in completed if i.content_type == "game"])
        }
    }


# Инициализация данных
@app.get("/init-data")
def init_data(db: Session = Depends(get_db)):
    try:
        # Создаем администратора
        admin_exists = db.query(User).filter(User.username == "admin").first()
        if not admin_exists:
            admin = User(
                username="admin",
                email="admin@example.com",
                password_hash=auth_service.hash_password("admin123"),
                role_id=1  # Роль администратора
            )
            db.add(admin)
            print("✅ Создан администратор: admin / admin123")

        # Создаем тестового пользователя
        user_exists = db.query(User).filter(User.username == "testuser").first()
        if not user_exists:
            user = User(
                username="testuser",
                email="test@example.com",
                password_hash=auth_service.hash_password("test123"),
                role_id=2  # Роль пользователя
            )
            db.add(user)
            print("✅ Создан пользователь: testuser / test123")

        # Добавляем контент с множественными жанрами
        books_count = db.query(Book).count()
        if books_count == 0:
            books = [
                Book(title="Война и мир", author="Лев Толстой", genres=["Классика", "История", "Драма"], year=1869,
                     popularity_score=9.2, description="Великий роман о войне и мире",
                     tags='["классика", "история", "драма"]'),
                Book(title="1984", author="Джордж Оруэлл", genres=["Антиутопия", "Политика", "Фантастика"], year=1949,
                     popularity_score=8.8, description="Роман-предупреждение о тоталитаризме",
                     tags='["антиутопия", "политика"]'),
                Book(title="Гарри Поттер", author="Дж.К. Роулинг",
                     genres=["Фэнтези", "Приключения", "Детская литература"], year=1997, popularity_score=9.5,
                     description="Магическая история о мальчике-волшебнике", tags='["фэнтези", "магия"]'),
                Book(title="Дюна", author="Фрэнк Герберт", genres=["Научная фантастика", "Приключения", "Политика"],
                     year=1965, popularity_score=8.9, description="Эпическая космическая сага",
                     tags='["фантастика", "космос"]'),
                Book(title="Властелин колец", author="Дж.Р.Р. Толкин", genres=["Фэнтези", "Приключения", "Классика"],
                     year=1954, popularity_score=9.4, description="Эпическое фэнтези о борьбе добра и зла",
                     tags='["фэнтези", "эпик"]')
            ]
            for book in books:
                db.add(book)
            print(f"✅ Создано {len(books)} книг")

        movies_count = db.query(Movie).count()
        if movies_count == 0:
            movies = [
                Movie(title="Матрица", director="Братья Вачовски", genres=["Научная фантастика", "Экшен", "Философия"],
                      year=1999, popularity_score=9.0, description="Фильм о виртуальной реальности",
                      tags='["фантастика", "экшен"]'),
                Movie(title="Побег из Шоушенка", director="Фрэнк Дарабонт", genres=["Драма", "Криминал"], year=1994,
                      popularity_score=9.3, description="История о надежде и дружбе", tags='["драма", "надежда"]'),
                Movie(title="Интерстеллар", director="Кристофер Нолан",
                      genres=["Научная фантастика", "Драма", "Приключения"], year=2014, popularity_score=8.9,
                      description="Космическая одиссея о спасении человечества", tags='["космос", "время"]'),
                Movie(title="Крестный отец", director="Фрэнсис Форд Коппола", genres=["Драма", "Криминал", "Классика"],
                      year=1972, popularity_score=9.2, description="Сага о семье мафиози", tags='["мафия", "семья"]'),
                Movie(title="Темный рыцарь", director="Кристофер Нолан", genres=["Экшен", "Криминал", "Супергерои"],
                      year=2008, popularity_score=9.0, description="Бэтмен против Джокера", tags='["бэтмен", "джокер"]')
            ]
            for movie in movies:
                db.add(movie)
            print(f"✅ Создано {len(movies)} фильмов")

        games_count = db.query(Game).count()
        if games_count == 0:
            games = [
                Game(title="The Witcher 3", developer="CD Projekt RED", genres=["RPG", "Фэнтези", "Открытый мир"],
                     year=2015, popularity_score=9.4, description="Приключения ведьмака Геральта",
                     tags='["RPG", "фэнтези"]'),
                Game(title="Portal 2", developer="Valve", genres=["Головоломка", "Научная фантастика", "Платформер"],
                     year=2011, popularity_score=9.2, description="Головоломки с порталами",
                     tags='["головоломка", "юмор"]'),
                Game(title="Minecraft", developer="Mojang", genres=["Песочница", "Выживание", "Творчество"], year=2011,
                     popularity_score=9.0, description="Строительство и выживание в кубическом мире",
                     tags='["строительство", "творчество"]'),
                Game(title="The Last of Us", developer="Naughty Dog", genres=["Экшен", "Выживание", "Драма"], year=2013,
                     popularity_score=9.3, description="Выживание в мире зомби-апокалипсиса",
                     tags='["зомби", "выживание"]'),
                Game(title="Civilization VI", developer="Firaxis Games", genres=["Стратегия", "Пошаговая", "История"],
                     year=2016, popularity_score=8.5, description="Стратегия развития цивилизации",
                     tags='["стратегия", "история"]')
            ]
            for game in games:
                db.add(game)
            print(f"✅ Создано {len(games)} игр")

        # Сохраняем все изменения
        db.commit()

        return {
            "message": "Данные успешно инициализированы с множественными жанрами!",
            "users": {
                "admin": "admin / admin123",
                "user": "testuser / test123"
            },
            "content": {
                "books": db.query(Book).count(),
                "movies": db.query(Movie).count(),
                "games": db.query(Game).count()
            }
        }

    except Exception as e:
        print(f"❌ Ошибка инициализации: {e}")
        return {"error": str(e), "message": "Ошибка при инициализации данных"}

# Добавьте после других эндпоинтов, перед if __name__ == "__main__":

@app.get("/recommendations")
async def get_recommendations(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Получение персональных рекомендаций с детальным объяснением алгоритма"""

    try:
        # Получаем ВСЕ взаимодействия пользователя для анализа
        all_interactions = db.query(UserInteraction).filter(
            UserInteraction.user_id == current_user.user_id
        ).all()

        # Получаем взаимодействия с высокими оценками (7+)
        high_rated = [i for i in all_interactions if i.rating and i.rating >= 7]
        medium_rated = [i for i in all_interactions if i.rating and 4 <= i.rating < 7]
        low_rated = [i for i in all_interactions if i.rating and i.rating < 4]

        # Анализируем предпочтения по жанрам
        genre_analysis = {}
        content_analysis = {"books": [], "movies": [], "games": []}

        for interaction in all_interactions:
            if not interaction.rating:
                continue

            content = None
            content_type_key = None

            if interaction.content_type == "book":
                content = db.query(Book).filter(Book.book_id == interaction.content_id).first()
                content_type_key = "books"
            elif interaction.content_type == "movie":
                content = db.query(Movie).filter(Movie.movie_id == interaction.content_id).first()
                content_type_key = "movies"
            elif interaction.content_type == "game":
                content = db.query(Game).filter(Game.game_id == interaction.content_id).first()
                content_type_key = "games"

            if content and content_type_key:
                # Получаем жанры контента
                genres = []
                if hasattr(content, 'genres') and content.genres:
                    if isinstance(content.genres, list):
                        genres = content.genres
                elif hasattr(content, 'genre') and content.genre:
                    genres = [content.genre]

                # Анализируем каждый жанр
                for genre in genres:
                    if genre not in genre_analysis:
                        genre_analysis[genre] = {
                            "total_ratings": 0,
                            "sum_ratings": 0,
                            "high_rated_count": 0,
                            "content_items": []
                        }

                    genre_analysis[genre]["total_ratings"] += 1
                    genre_analysis[genre]["sum_ratings"] += interaction.rating

                    if interaction.rating >= 7:
                        genre_analysis[genre]["high_rated_count"] += 1

                    genre_analysis[genre]["content_items"].append({
                        "title": content.title,
                        "rating": interaction.rating,
                        "type": interaction.content_type
                    })

                # Сохраняем информацию о контенте
                content_analysis[content_type_key].append({
                    "title": content.title,
                    "rating": interaction.rating,
                    "genres": genres,
                    "popularity": content.popularity_score
                })

        # Вычисляем средние оценки и предпочтения по жанрам
        genre_preferences = {}
        for genre, data in genre_analysis.items():
            avg_rating = data["sum_ratings"] / data["total_ratings"]
            preference_score = (avg_rating * 0.7) + (data["high_rated_count"] / data["total_ratings"] * 10 * 0.3)

            genre_preferences[genre] = {
                "average_rating": round(avg_rating, 2),
                "preference_score": round(preference_score, 2),
                "total_items": data["total_ratings"],
                "high_rated_items": data["high_rated_count"],
                "sample_items": data["content_items"][:3]  # Примеры контента
            }

        # Сортируем жанры по предпочтениям
        sorted_genres = sorted(genre_preferences.items(), key=lambda x: x[1]["preference_score"], reverse=True)

        # Получаем ID уже оцененного контента
        rated_content_ids = {
            'book': [i.content_id for i in all_interactions if i.content_type == 'book'],
            'movie': [i.content_id for i in all_interactions if i.content_type == 'movie'],
            'game': [i.content_id for i in all_interactions if i.content_type == 'game']
        }

        recommendations = []
        recommendation_logic = []

        # Генерируем рекомендации на основе предпочтений
        if sorted_genres:
            for genre, pref_data in sorted_genres[:3]:  # Топ-3 жанра
                if pref_data["preference_score"] < 5:  # Пропускаем плохо оцененные жанры
                    continue

                # Ищем контент в этом жанре
                all_books = db.query(Book).filter(~Book.book_id.in_(rated_content_ids['book'])).order_by(
                    Book.popularity_score.desc()).all()
                all_movies = db.query(Movie).filter(~Movie.movie_id.in_(rated_content_ids['movie'])).order_by(
                    Movie.popularity_score.desc()).all()
                all_games = db.query(Game).filter(~Game.game_id.in_(rated_content_ids['game'])).order_by(
                    Game.popularity_score.desc()).all()

                genre_recommendations = []

                # Книги
                for book in all_books:
                    book_genres = book.genres if isinstance(book.genres, list) else []
                    if genre in book_genres and len(genre_recommendations) < 2:
                        confidence = min(95, 60 + (pref_data["preference_score"] * 5) + (book.popularity_score * 2))

                        recommendation = {
                            "id": book.book_id,
                            "title": book.title,
                            "creator": book.author,
                            "genres": book_genres,
                            "year": book.year,
                            "popularity_score": book.popularity_score,
                            "content_type": "book",
                            "recommendation_reason": f"Жанр '{genre}' (ваша средняя оценка: {pref_data['average_rating']})",
                            "confidence": round(confidence, 1),
                            "explanation": {
                                "primary_reason": f"Вы высоко оцениваете жанр '{genre}'",
                                "supporting_data": f"Из {pref_data['total_items']} произведений этого жанра вы поставили высокие оценки {pref_data['high_rated_items']} раз",
                                "algorithm": f"Коэффициент предпочтения: {pref_data['preference_score']} (средняя оценка × 0.7 + процент высоких оценок × 10 × 0.3)",
                                "examples": [item["title"] for item in pref_data["sample_items"]]
                            }
                        }

                        recommendations.append(recommendation)
                        genre_recommendations.append(recommendation)

                # Фильмы
                for movie in all_movies:
                    movie_genres = movie.genres if isinstance(movie.genres, list) else []
                    if genre in movie_genres and len(genre_recommendations) < 4:
                        confidence = min(95, 60 + (pref_data["preference_score"] * 5) + (movie.popularity_score * 2))

                        recommendation = {
                            "id": movie.movie_id,
                            "title": movie.title,
                            "creator": movie.director,
                            "genres": movie_genres,
                            "year": movie.year,
                            "popularity_score": movie.popularity_score,
                            "content_type": "movie",
                            "recommendation_reason": f"Жанр '{genre}' (ваша средняя оценка: {pref_data['average_rating']})",
                            "confidence": round(confidence, 1),
                            "explanation": {
                                "primary_reason": f"Вы высоко оцениваете жанр '{genre}'",
                                "supporting_data": f"Из {pref_data['total_items']} произведений этого жанра вы поставили высокие оценки {pref_data['high_rated_items']} раз",
                                "algorithm": f"Коэффициент предпочтения: {pref_data['preference_score']}",
                                "examples": [item["title"] for item in pref_data["sample_items"]]
                            }
                        }

                        recommendations.append(recommendation)
                        genre_recommendations.append(recommendation)

                # Игры
                for game in all_games:
                    game_genres = game.genres if isinstance(game.genres, list) else []
                    if genre in game_genres and len(genre_recommendations) < 6:
                        confidence = min(95, 60 + (pref_data["preference_score"] * 5) + (game.popularity_score * 2))

                        recommendation = {
                            "id": game.game_id,
                            "title": game.title,
                            "creator": game.developer,
                            "genres": game_genres,
                            "year": game.year,
                            "popularity_score": game.popularity_score,
                            "content_type": "game",
                            "recommendation_reason": f"Жанр '{genre}' (ваша средняя оценка: {pref_data['average_rating']})",
                            "confidence": round(confidence, 1),
                            "explanation": {
                                "primary_reason": f"Вы высоко оцениваете жанр '{genre}'",
                                "supporting_data": f"Из {pref_data['total_items']} произведений этого жанра вы поставили высокие оценки {pref_data['high_rated_items']} раз",
                                "algorithm": f"Коэффициент предпочтения: {pref_data['preference_score']}",
                                "examples": [item["title"] for item in pref_data["sample_items"]]
                            }
                        }

                        recommendations.append(recommendation)
                        genre_recommendations.append(recommendation)

                # Добавляем логику рекомендаций для этого жанра
                if genre_recommendations:
                    recommendation_logic.append({
                        "genre": genre,
                        "preference_score": pref_data["preference_score"],
                        "average_rating": pref_data["average_rating"],
                        "total_items": pref_data["total_items"],
                        "high_rated_items": pref_data["high_rated_items"],
                        "recommendations_count": len(genre_recommendations),
                        "explanation": f"Жанр '{genre}' выбран потому что ваша средняя оценка {pref_data['average_rating']}/10, из {pref_data['total_items']} произведений {pref_data['high_rated_items']} получили высокие оценки (7+)"
                    })

        # Если нет персональных рекомендаций, показываем популярное
        if not recommendations:
            popular_books = db.query(Book).filter(~Book.book_id.in_(rated_content_ids['book'])).order_by(
                Book.popularity_score.desc()).limit(3).all()
            popular_movies = db.query(Movie).filter(~Movie.movie_id.in_(rated_content_ids['movie'])).order_by(
                Movie.popularity_score.desc()).limit(3).all()
            popular_games = db.query(Game).filter(~Game.game_id.in_(rated_content_ids['game'])).order_by(
                Game.popularity_score.desc()).limit(3).all()

            for book in popular_books:
                book_genres = book.genres if isinstance(book.genres, list) else []
                recommendations.append({
                    "id": book.book_id,
                    "title": book.title,
                    "creator": book.author,
                    "genres": book_genres,
                    "year": book.year,
                    "popularity_score": book.popularity_score,
                    "content_type": "book",
                    "recommendation_reason": "Популярное среди всех пользователей",
                    "confidence": 70.0,
                    "explanation": {
                        "primary_reason": "У вас пока нет оценок для персональных рекомендаций",
                        "supporting_data": f"Популярность среди пользователей: {book.popularity_score}/10",
                        "algorithm": "Сортировка по общей популярности",
                        "examples": []
                    }
                })

            for movie in popular_movies:
                movie_genres = movie.genres if isinstance(movie.genres, list) else []
                recommendations.append({
                    "id": movie.movie_id,
                    "title": movie.title,
                    "creator": movie.director,
                    "genres": movie_genres,
                    "year": movie.year,
                    "popularity_score": movie.popularity_score,
                    "content_type": "movie",
                    "recommendation_reason": "Популярное среди всех пользователей",
                    "confidence": 70.0,
                    "explanation": {
                        "primary_reason": "У вас пока нет оценок для персональных рекомендаций",
                        "supporting_data": f"Популярность среди пользователей: {movie.popularity_score}/10",
                        "algorithm": "Сортировка по общей популярности",
                        "examples": []
                    }
                })

            for game in popular_games:
                game_genres = game.genres if isinstance(game.genres, list) else []
                recommendations.append({
                    "id": game.game_id,
                    "title": game.title,
                    "creator": game.developer,
                    "genres": game_genres,
                    "year": game.year,
                    "popularity_score": game.popularity_score,
                    "content_type": "game",
                    "recommendation_reason": "Популярное среди всех пользователей",
                    "confidence": 70.0,
                    "explanation": {
                        "primary_reason": "У вас пока нет оценок для персональных рекомендаций",
                        "supporting_data": f"Популярность среди пользователей: {game.popularity_score}/10",
                        "algorithm": "Сортировка по общей популярности",
                        "examples": []
                    }
                })

            recommendation_logic.append({
                "genre": "Популярное",
                "explanation": "Показываем популярный контент, так как у вас пока нет оценок для персональных рекомендаций"
            })

        # Сортируем рекомендации по уверенности
        recommendations.sort(key=lambda x: x.get("confidence", 0), reverse=True)

        return {
            "recommendations": recommendations[:12],  # Топ-12 рекомендаций
            "algorithm_explanation": {
                "total_interactions": len(all_interactions),
                "high_rated_count": len(high_rated),
                "medium_rated_count": len(medium_rated),
                "low_rated_count": len(low_rated),
                "genre_preferences": dict(sorted_genres[:5]),  # Топ-5 жанров
                "recommendation_logic": recommendation_logic,
                "algorithm_description": "Рекомендации основаны на анализе ваших оценок по жанрам. Для каждого жанра вычисляется коэффициент предпочтения: (средняя_оценка × 0.7) + (процент_высоких_оценок × 10 × 0.3). Контент рекомендуется из жанров с высоким коэффициентом предпочтения."
            },
            "user_profile": {
                "favorite_genres": [genre for genre, _ in sorted_genres[:3]],
                "total_ratings": len(all_interactions),
                "average_rating": round(sum(i.rating for i in all_interactions if i.rating) / len(
                    [i for i in all_interactions if i.rating]), 2) if [i for i in all_interactions if i.rating] else 0,
                "content_distribution": {
                    "books": len(content_analysis["books"]),
                    "movies": len(content_analysis["movies"]),
                    "games": len(content_analysis["games"])
                }
            }
        }

    except Exception as e:
        print(f"Ошибка рекомендаций: {e}")
        return {
            "recommendations": [],
            "algorithm_explanation": {
                "error": str(e),
                "message": "Произошла ошибка при генерации рекомендаций"
            },
            "user_profile": {}
        }

@app.post("/admin/add-content")
async def add_content(
        content_type: str,
        title: str,
        creator: str,
        genres: str = "",  # Жанры через запятую
        year: int = None,
        description: str = None,
        popularity_score: float = 5.0,  # Теперь можно задать оценку
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Добавление контента"""

    # Обрабатываем жанры
    genres_list = [g.strip() for g in genres.split(',') if g.strip()] if genres else []

    if content_type == "book":
        content = Book(
            title=title,
            author=creator,
            genres=genres_list,
            year=year,
            description=description,
            popularity_score=max(0.0, min(10.0, popularity_score)),  # Ограничиваем 0-10
            tags='[]'
        )
    elif content_type == "movie":
        content = Movie(
            title=title,
            director=creator,
            genres=genres_list,
            year=year,
            description=description,
            popularity_score=max(0.0, min(10.0, popularity_score)),
            tags='[]'
        )
    elif content_type == "game":
        content = Game(
            title=title,
            developer=creator,
            genres=genres_list,
            year=year,
            description=description,
            popularity_score=max(0.0, min(10.0, popularity_score)),
            tags='[]'
        )
    else:
        raise HTTPException(status_code=400, detail="Invalid content type")

    db.add(content)
    db.commit()
    db.refresh(content)

    return {
        "message": f"{content_type.title()} '{title}' успешно добавлен!",
        "content": {
            "id": getattr(content, f"{content_type}_id"),
            "title": content.title,
            "creator": creator,
            "genres": genres_list,
            "popularity_score": popularity_score
        }
    }


@app.put("/admin/edit-content/{content_type}/{content_id}")
async def edit_content(
        content_type: str,
        content_id: int,
        title: str = None,
        creator: str = None,
        genres: str = None,
        year: int = None,
        description: str = None,
        popularity_score: float = None,
        db: Session = Depends(get_db),
        admin_user: User = Depends(require_admin)
):
    """Редактирование контента (только для администраторов)"""

    # Получаем контент
    if content_type == "book":
        content = db.query(Book).filter(Book.book_id == content_id).first()
        creator_field = "author"
    elif content_type == "movie":
        content = db.query(Movie).filter(Movie.movie_id == content_id).first()
        creator_field = "director"
    elif content_type == "game":
        content = db.query(Game).filter(Game.game_id == content_id).first()
        creator_field = "developer"
    else:
        raise HTTPException(status_code=400, detail="Invalid content type")

    if not content:
        raise HTTPException(status_code=404, detail="Content not found")

    # Обновляем поля
    if title is not None:
        content.title = title
    if creator is not None:
        setattr(content, creator_field, creator)
    if genres is not None:
        genres_list = [g.strip() for g in genres.split(',') if g.strip()]
        content.genres = genres_list
    if year is not None:
        content.year = year
    if description is not None:
        content.description = description
    if popularity_score is not None:
        content.popularity_score = max(0.0, min(10.0, popularity_score))

    db.commit()
    db.refresh(content)

    return {
        "message": f"{content_type.title()} '{content.title}' успешно обновлен!",
        "content": {
            "id": content_id,
            "title": content.title,
            "creator": getattr(content, creator_field),
            "genres": content.genres,
            "popularity_score": content.popularity_score
        }
    }


# Новый эндпоинт для удаления контента (только админы)
@app.delete("/admin/delete-content/{content_type}/{content_id}")
async def delete_content(
        content_type: str,
        content_id: int,
        db: Session = Depends(get_db),
        admin_user: User = Depends(require_admin)
):
    """Удаление контента (только для администраторов)"""

    if content_type == "book":
        content = db.query(Book).filter(Book.book_id == content_id).first()
    elif content_type == "movie":
        content = db.query(Movie).filter(Movie.movie_id == content_id).first()
    elif content_type == "game":
        content = db.query(Game).filter(Game.game_id == content_id).first()
    else:
        raise HTTPException(status_code=400, detail="Invalid content type")

    if not content:
        raise HTTPException(status_code=404, detail="Content not found")

    title = content.title
    db.delete(content)
    db.commit()

    return {"message": f"{content_type.title()} '{title}' успешно удален!"}


# Новый эндпоинт для ручной оценки контента
@app.post("/rate-content")
async def rate_content(
        content_type: str,
        content_id: int,
        rating: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Ручная оценка контента без симуляции"""

    if not (1 <= rating <= 10):
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 10")

    # Проверяем, что контент существует
    if content_type == "book":
        content = db.query(Book).filter(Book.book_id == content_id).first()
    elif content_type == "movie":
        content = db.query(Movie).filter(Movie.movie_id == content_id).first()
    elif content_type == "game":
        content = db.query(Game).filter(Game.game_id == content_id).first()
    else:
        raise HTTPException(status_code=400, detail="Invalid content type")

    if not content:
        raise HTTPException(status_code=404, detail="Content not found")

    # Проверяем, есть ли уже оценка
    existing = db.query(UserInteraction).filter(
        UserInteraction.user_id == current_user.user_id,
        UserInteraction.content_type == content_type,
        UserInteraction.content_id == content_id
    ).first()

    if existing:
        # Обновляем существующую оценку
        existing.rating = rating
        existing.interaction_type = "completed"
        existing.completion_date = datetime.now()
        db.commit()
        message = f"Оценка обновлена на {rating}/10"
    else:
        # Создаем новую оценку
        interaction = UserInteraction(
            user_id=current_user.user_id,
            content_type=content_type,
            content_id=content_id,
            interaction_type="completed",
            rating=rating,
            progress_percent=100,
            start_date=datetime.now(),
            completion_date=datetime.now(),
            simulation_duration=0
        )
        db.add(interaction)
        db.commit()
        message = f"Контент оценен на {rating}/10"

    # Обновляем популярность контента
    current_avg = content.popularity_score
    # Простая формула обновления: новая популярность = (старая * 0.9) + (новая_оценка * 0.1)
    new_popularity = (current_avg * 0.9) + (rating * 0.1)
    content.popularity_score = round(new_popularity, 2)
    db.commit()

    return {
        "message": message,
        "content_title": content.title,
        "rating": rating,
        "new_popularity": content.popularity_score
    }


# Обновите функцию инициализации данных
@app.get("/init-data")
def init_data(db: Session = Depends(get_db)):
    # Создаем администратора
    if not db.query(User).filter(User.username == "admin").first():
        admin = User(
            username="admin",
            email="admin@example.com",
            password_hash=auth_service.hash_password("admin123"),
            role_id=1  # Роль администратора
        )
        db.add(admin)

    # Создаем тестового пользователя
    if not db.query(User).filter(User.username == "testuser").first():
        user = User(
            username="testuser",
            email="test@example.com",
            password_hash=auth_service.hash_password("test123"),
            role_id=2  # Роль пользователя
        )
        db.add(user)

    # Добавляем контент с множественными жанрами
    if db.query(Book).count() == 0:
        books = [
            Book(title="Война и мир", author="Лев Толстой", genres=["Классика", "История", "Драма"], year=1869,
                 popularity_score=9.2, tags='["классика", "история", "драма"]'),
            Book(title="1984", author="Джордж Оруэлл", genres=["Антиутопия", "Политика", "Фантастика"], year=1949,
                 popularity_score=8.8, tags='["антиутопия", "политика"]'),
            Book(title="Гарри Поттер", author="Дж.К. Роулинг", genres=["Фэнтези", "Приключения", "Детская литература"],
                 year=1997, popularity_score=9.5, tags='["фэнтези", "магия"]'),
            Book(title="Дюна", author="Фрэнк Герберт", genres=["Научная фантастика", "Приключения", "Политика"],
                 year=1965, popularity_score=8.9, tags='["фантастика", "космос"]'),
            Book(title="Властелин колец", author="Дж.Р.Р. Толкин", genres=["Фэнтези", "Приключения", "Классика"],
                 year=1954, popularity_score=9.4, tags='["фэнтези", "эпик"]')
        ]
        for book in books:
            db.add(book)

    if db.query(Movie).count() == 0:
        movies = [
            Movie(title="Матрица", director="Братья Вачовски", genres=["Научная фантастика", "Экшен", "Философия"],
                  year=1999, popularity_score=9.0, tags='["фантастика", "экшен"]'),
            Movie(title="Побег из Шоушенка", director="Фрэнк Дарабонт", genres=["Драма", "Криминал"], year=1994,
                  popularity_score=9.3, tags='["драма", "надежда"]'),
            Movie(title="Интерстеллар", director="Кристофер Нолан",
                  genres=["Научная фантастика", "Драма", "Приключения"], year=2014, popularity_score=8.9,
                  tags='["космос", "время"]'),
            Movie(title="Крестный отец", director="Фрэнсис Форд Коппола", genres=["Драма", "Криминал", "Классика"],
                  year=1972, popularity_score=9.2, tags='["мафия", "семья"]'),
            Movie(title="Темный рыцарь", director="Кристофер Нолан", genres=["Экшен", "Криминал", "Супергерои"],
                  year=2008, popularity_score=9.0, tags='["бэтмен", "джокер"]')
        ]
        for movie in movies:
            db.add(movie)

    if db.query(Game).count() == 0:
        games = [
            Game(title="The Witcher 3", developer="CD Projekt RED", genres=["RPG", "Фэнтези", "Открытый мир"],
                 year=2015, popularity_score=9.4, tags='["RPG", "фэнтези"]'),
            Game(title="Portal 2", developer="Valve", genres=["Головоломка", "Научная фантастика", "Платформер"],
                 year=2011, popularity_score=9.2, tags='["головоломка", "юмор"]'),
            Game(title="Minecraft", developer="Mojang", genres=["Песочница", "Выживание", "Творчество"], year=2011,
                 popularity_score=9.0, tags='["строительство", "творчество"]'),
            Game(title="The Last of Us", developer="Naughty Dog", genres=["Экшен", "Выживание", "Драма"], year=2013,
                 popularity_score=9.3, tags='["зомби", "выживание"]'),
            Game(title="Civilization VI", developer="Firaxis Games", genres=["Стратегия", "Пошаговая", "История"],
                 year=2016, popularity_score=8.5, tags='["стратегия", "история"]')
        ]
        for game in games:
            db.add(game)

    db.commit()
    return {
        "message": "Данные инициализированы с множественными жанрами!",
        "users": {
            "admin": "admin / admin123",
            "user": "testuser / test123"
        }
    }

if __name__ == "__main__":
    import uvicorn

    print("🚀 Запуск MediaRecommender Full API...")
    print("📖 Документация: http://localhost:8001/docs")
    print("🔧 Инициализация: http://localhost:8001/init-data")
    print("👤 Тестовый пользователь: testuser / test123")
    uvicorn.run(app, host="127.0.0.1", port=8001)