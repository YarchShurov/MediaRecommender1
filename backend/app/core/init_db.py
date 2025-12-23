from sqlalchemy.orm import Session
from app.database import engine, SessionLocal
from app.models import Role, User, Book, Movie, Game
from app.core.auth import get_password_hash
import json


def create_tables():
    """Создание всех таблиц"""
    from app.models import Base
    Base.metadata.create_all(bind=engine)


def init_roles(db: Session):
    """Инициализация ролей"""
    admin_permissions = {
        "content": ["create", "read", "update", "delete"],
        "users": ["read", "update", "block"],
        "tags": ["create", "read", "update", "delete"],
        "analytics": ["read"],
        "system": ["configure"]
    }

    user_permissions = {
        "content": ["read"],
        "interactions": ["create", "read", "update"],
        "profile": ["read", "update"]
    }

    # Создаем роль администратора
    admin_role = db.query(Role).filter(Role.role_name == "admin").first()
    if not admin_role:
        admin_role = Role(
            role_name="admin",
            permissions=admin_permissions
        )
        db.add(admin_role)

    # Создаем роль пользователя
    user_role = db.query(Role).filter(Role.role_name == "user").first()
    if not user_role:
        user_role = Role(
            role_name="user",
            permissions=user_permissions
        )
        db.add(user_role)

    db.commit()


def init_users(db: Session):
    """Создание тестовых пользователей"""
    # Администратор
    admin = db.query(User).filter(User.username == "admin").first()
    if not admin:
        admin = User(
            username="admin",
            email="admin@mediarecommender.com",
            password_hash=get_password_hash("admin123"),
            role_id=1,
            preferences={"popularity": 50, "newness": 50}
        )
        db.add(admin)

    # Тестовый пользователь
    test_user = db.query(User).filter(User.username == "testuser").first()
    if not test_user:
        test_user = User(
            username="testuser",
            email="test@example.com",
            password_hash=get_password_hash("test123"),
            role_id=2,
            preferences={"popularity": 70, "newness": 30}
        )
        db.add(test_user)

    db.commit()


def init_sample_content(db: Session):
    """Создание примерного контента"""

    # Книги
    sample_books = [
        {
            "title": "Война и мир",
            "author": "Лев Толстой",
            "genre": "Классическая литература",
            "year": 1869,
            "popularity_score": 9.2,
            "description": "Эпический роман о русском обществе в эпоху наполеоновских войн",
            "tags": ["классика", "история", "драма", "философия", "русская литература"]
        },
        {
            "title": "1984",
            "author": "Джордж Оруэлл",
            "genre": "Антиутопия",
            "year": 1949,
            "popularity_score": 8.8,
            "description": "Роман-предупреждение о тоталитарном обществе",
            "tags": ["антиутопия", "политика", "философия", "контроль", "свобода"]
        },
        {
            "title": "Гарри Поттер и философский камень",
            "author": "Дж.К. Роулинг",
            "genre": "Фэнтези",
            "year": 1997,
            "popularity_score": 9.5,
            "description": "Первая книга о юном волшебнике",
            "tags": ["фэнтези", "магия", "приключения", "дружба", "школа"]
        },
        {
            "title": "Дюна",
            "author": "Фрэнк Герберт",
            "genre": "Научная фантастика",
            "year": 1965,
            "popularity_score": 8.9,
            "description": "Эпическая сага о далеком будущем",
            "tags": ["научная фантастика", "космос", "политика", "экология", "эпик"]
        },
        {
            "title": "Мастер и Маргарита",
            "author": "Михаил Булгаков",
            "genre": "Мистика",
            "year": 1967,
            "popularity_score": 9.1,
            "description": "Роман о добре и зле, любви и предательстве",
            "tags": ["мистика", "философия", "сатира", "любовь", "русская литература"]
        }
    ]

    for book_data in sample_books:
        existing = db.query(Book).filter(Book.title == book_data["title"]).first()
        if not existing:
            book = Book(**book_data)
            db.add(book)

    # Фильмы
    sample_movies = [
        {
            "title": "Матрица",
            "director": "Братья Вачовски",
            "genre": "Научная фантастика",
            "year": 1999,
            "popularity_score": 9.0,
            "description": "Программист обнаруживает, что реальность - симуляция",
            "tags": ["научная фантастика", "экшен", "философия", "киберпанк", "реальность"]
        },
        {
            "title": "Побег из Шоушенка",
            "director": "Фрэнк Дарабонт",
            "genre": "Драма",
            "year": 1994,
            "popularity_score": 9.3,
            "description": "История о надежде и дружбе в тюрьме",
            "tags": ["драма", "надежда", "дружба", "тюрьма", "классика"]
        },
        {
            "title": "Властелин колец: Братство кольца",
            "director": "Питер Джексон",
            "genre": "Фэнтези",
            "year": 2001,
            "popularity_score": 9.1,
            "description": "Эпическое путешествие хоббита",
            "tags": ["фэнтези", "приключения", "эпик", "магия", "дружба"]
        },
        {
            "title": "Криминальное чтиво",
            "director": "Квентин Тарантино",
            "genre": "Криминал",
            "year": 1994,
            "popularity_score": 8.7,
            "description": "Переплетающиеся истории преступного мира",
            "tags": ["криминал", "нуар", "диалоги", "насилие", "культовое"]
        },
        {
            "title": "Интерстеллар",
            "director": "Кристофер Нолан",
            "genre": "Научная фантастика",
            "year": 2014,
            "popularity_score": 8.9,
            "description": "Путешествие через пространство и время",
            "tags": ["научная фантастика", "космос", "время", "семья", "наука"]
        }
    ]

    for movie_data in sample_movies:
        existing = db.query(Movie).filter(Movie.title == movie_data["title"]).first()
        if not existing:
            movie = Movie(**movie_data)
            db.add(movie)

    # Игры
    sample_games = [
        {
            "title": "The Witcher 3: Wild Hunt",
            "developer": "CD Projekt RED",
            "genre": "RPG",
            "year": 2015,
            "popularity_score": 9.4,
            "description": "Эпическое фэнтези RPG о ведьмаке Геральте",
            "tags": ["RPG", "фэнтези", "открытый мир", "квесты", "выбор"]
        },
        {
            "title": "Portal 2",
            "developer": "Valve",
            "genre": "Головоломка",
            "year": 2011,
            "popularity_score": 9.2,
            "description": "Инновационная игра-головоломка с порталами",
            "tags": ["головоломка", "научная фантастика", "юмор", "физика", "кооператив"]
        },
        {
            "title": "Minecraft",
            "developer": "Mojang",
            "genre": "Песочница",
            "year": 2011,
            "popularity_score": 9.0,
            "description": "Игра о строительстве и выживании в блочном мире",
            "tags": ["песочница", "строительство", "выживание", "творчество", "мультиплеер"]
        },
        {
            "title": "Half-Life 2",
            "developer": "Valve",
            "genre": "Шутер",
            "year": 2004,
            "popularity_score": 9.1,
            "description": "Революционный шутер от первого лица",
            "tags": ["шутер", "научная фантастика", "физика", "сюжет", "классика"]
        },
        {
            "title": "Civilization VI",
            "developer": "Firaxis Games",
            "genre": "Стратегия",
            "year": 2016,
            "popularity_score": 8.5,
            "description": "Пошаговая стратегия о развитии цивилизации",
            "tags": ["стратегия", "пошаговая", "история", "дипломатия", "развитие"]
        }
    ]

    for game_data in sample_games:
        existing = db.query(Game).filter(Game.title == game_data["title"]).first()
        if not existing:
            game = Game(**game_data)
            db.add(game)

    db.commit()


def initialize_database():
    """Полная инициализация базы данных"""
    print("Создание таблиц...")
    create_tables()

    print("Инициализация данных...")
    db = SessionLocal()
    try:
        init_roles(db)
        print("✅ Роли созданы")

        init_users(db)
        print("✅ Пользователи созданы")

        init_sample_content(db)
        print("✅ Примерный контент добавлен")

        print("🎉 База данных успешно инициализирована!")
        print("\nТестовые аккаунты:")
        print("Администратор - username: admin, password: admin123")
        print("Пользователь - username: testuser, password: test123")

    finally:
        db.close()


if __name__ == "__main__":
    initialize_database()