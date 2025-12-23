import asyncio
import random
from datetime import datetime, timedelta
from typing import Dict, List
from sqlalchemy.orm import Session
from app.models import UserInteraction, Book, Movie, Game


class SimulationService:
    # Времена симуляции в секундах
    SIMULATION_TIMES = {
        'book': {'min': 30, 'max': 180},
        'movie': {'min': 20, 'max': 60},
        'game': {'min': 45, 'max': 300}
    }

    # Случайные события во время симуляции
    SIMULATION_EVENTS = {
        'book': [
            "Вы погружаетесь в увлекательный сюжет...",
            "Неожиданный поворот событий!",
            "Главный герой принимает важное решение...",
            "Вы не можете оторваться от чтения!",
            "Эмоциональная сцена заставляет задуматься..."
        ],
        'movie': [
            "Захватывающая сцена экшена!",
            "Неожиданный сюжетный твист!",
            "Эмоциональный диалог между персонажами...",
            "Впечатляющие визуальные эффекты!",
            "Напряженный момент..."
        ],
        'game': [
            "Вы исследуете новую локацию!",
            "Эпическая битва с боссом!",
            "Найден редкий предмет!",
            "Разблокировано достижение!",
            "Сложная головоломка решена!",
            "Новый уровень пройден!"
        ]
    }

    def __init__(self, db: Session):
        self.db = db
        self.active_simulations: Dict[str, Dict] = {}

    async def start_simulation(self, user_id: int, content_type: str, content_id: int) -> Dict:
        """Запуск симуляции"""
        # Проверяем, что контент существует
        content = self.get_content(content_type, content_id)
        if not content:
            raise ValueError(f"Content not found: {content_type} {content_id}")

        # Создаем запись о начале взаимодействия
        interaction = UserInteraction(
            user_id=user_id,
            content_type=content_type,
            content_id=content_id,
            interaction_type="started",
            progress_percent=0,
            start_date=datetime.utcnow()
        )
        self.db.add(interaction)
        self.db.commit()
        self.db.refresh(interaction)

        # Определяем время симуляции
        time_range = self.SIMULATION_TIMES[content_type]
        simulation_time = random.randint(time_range['min'], time_range['max'])

        # Сохраняем информацию об активной симуляции
        simulation_key = f"{user_id}_{content_type}_{content_id}"
        self.active_simulations[simulation_key] = {
            "interaction_id": interaction.interaction_id,
            "user_id": user_id,
            "content_type": content_type,
            "content_id": content_id,
            "content_title": content.title,
            "start_time": datetime.utcnow(),
            "total_time": simulation_time,
            "events": []
        }

        return {
            "simulation_id": simulation_key,
            "interaction_id": interaction.interaction_id,
            "estimated_time": simulation_time,
            "content_title": content.title,
            "message": f"Начинаем {self.get_action_verb(content_type)} '{content.title}'!"
        }

    async def get_simulation_progress(self, simulation_id: str) -> Dict:
        """Получение прогресса симуляции"""
        if simulation_id not in self.active_simulations:
            raise ValueError("Simulation not found")

        sim = self.active_simulations[simulation_id]
        current_time = datetime.utcnow()
        elapsed = (current_time - sim["start_time"]).total_seconds()
        progress = min(100, int((elapsed / sim["total_time"]) * 100))

        # Обновляем прогресс в базе данных
        interaction = self.db.query(UserInteraction).filter(
            UserInteraction.interaction_id == sim["interaction_id"]
        ).first()
        if interaction:
            interaction.progress_percent = progress
            self.db.commit()

        # Генерируем случайное событие
        event = None
        if progress > 20 and len(sim["events"]) < 3 and random.random() < 0.3:
            event = random.choice(self.SIMULATION_EVENTS[sim["content_type"]])
            sim["events"].append(event)

        return {
            "progress": progress,
            "completed": progress >= 100,
            "event": event,
            "content_title": sim["content_title"],
            "elapsed_time": int(elapsed)
        }

    async def complete_simulation(self, simulation_id: str, rating: int, personal_tags: List[str] = None) -> Dict:
        """Завершение симуляции с оценкой"""
        if simulation_id not in self.active_simulations:
            raise ValueError("Simulation not found")

        sim = self.active_simulations[simulation_id]

        # Обновляем запись взаимодействия
        interaction = self.db.query(UserInteraction).filter(
            UserInteraction.interaction_id == sim["interaction_id"]
        ).first()

        if interaction:
            current_time = datetime.utcnow()
            actual_duration = int((current_time - sim["start_time"]).total_seconds())

            interaction.interaction_type = "completed"
            interaction.rating = rating
            interaction.progress_percent = 100
            interaction.completion_date = current_time
            interaction.simulation_duration = actual_duration

            # Добавляем персональные теги
            if personal_tags:
                existing_tags = interaction.tags_extracted or []
                interaction.tags_extracted = list(set(existing_tags + personal_tags))

            self.db.commit()

        # Удаляем из активных симуляций
        del self.active_simulations[simulation_id]

        # Обновляем популярность контента на основе оценки
        await self.update_content_popularity(sim["content_type"], sim["content_id"], rating)

        return {
            "message": f"Вы завершили {self.get_action_verb(sim['content_type'])} '{sim['content_title']}'!",
            "rating": rating,
            "duration": actual_duration,
            "experience_gained": self.calculate_experience(rating, actual_duration)
        }

    async def cancel_simulation(self, simulation_id: str) -> Dict:
        """Отмена симуляции"""
        if simulation_id not in self.active_simulations:
            raise ValueError("Simulation not found")

        sim = self.active_simulations[simulation_id]

        # Обновляем запись как "брошено"
        interaction = self.db.query(UserInteraction).filter(
            UserInteraction.interaction_id == sim["interaction_id"]
        ).first()

        if interaction:
            interaction.interaction_type = "dropped"
            interaction.completion_date = datetime.utcnow()
            self.db.commit()

        del self.active_simulations[simulation_id]

        return {
            "message": f"Вы прекратили {self.get_action_verb(sim['content_type'])} '{sim['content_title']}'"
        }

    def get_content(self, content_type: str, content_id: int):
        """Получение контента по типу и ID"""
        if content_type == "book":
            return self.db.query(Book).filter(Book.book_id == content_id).first()
        elif content_type == "movie":
            return self.db.query(Movie).filter(Movie.movie_id == content_id).first()
        elif content_type == "game":
            return self.db.query(Game).filter(Game.game_id == content_id).first()
        return None

    def get_action_verb(self, content_type: str) -> str:
        """Получение глагола действия для типа контента"""
        verbs = {
            "book": "чтение",
            "movie": "просмотр",
            "game": "игру"
        }
        return verbs.get(content_type, "взаимодействие")

    async def update_content_popularity(self, content_type: str, content_id: int, rating: int):
        """Обновление популярности контента на основе новой оценки"""
        content = self.get_content(content_type, content_id)
        if content:
            # Простая формула обновления популярности
            # Новая популярность = (старая * 0.9) + (новая_оценка * 0.1)
            new_score = (content.popularity_score * 0.9) + (rating * 0.1)
            content.popularity_score = round(new_score, 2)
            self.db.commit()

    def calculate_experience(self, rating: int, duration: int) -> int:
        """Расчет "опыта" за завершение контента"""
        base_exp = rating * 10
        time_bonus = min(duration // 30, 50)  # Бонус за время
        return base_exp + time_bonus