from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc
from app.models import User, UserInteraction, Book, Movie, Game
from collections import Counter
import random


class RecommendationService:
    def __init__(self, db: Session):
        self.db = db

    def get_user_preferences(self, user_id: int) -> Dict[str, Any]:
        """Получение настроек пользователя"""
        user = self.db.query(User).filter(User.user_id == user_id).first()
        if not user or not user.preferences:
            return {"popularity": 50, "newness": 50}
        return user.preferences

    def get_user_last_interactions(self, user_id: int, limit: int = 5) -> List[UserInteraction]:
        """Получение последних взаимодействий пользователя"""
        return self.db.query(UserInteraction) \
            .filter(UserInteraction.user_id == user_id) \
            .filter(UserInteraction.rating.isnot(None)) \
            .order_by(desc(UserInteraction.completion_date)) \
            .limit(limit) \
            .all()

    def extract_preferred_tags(self, interactions: List[UserInteraction]) -> List[str]:
        """Извлечение предпочитаемых тегов на основе оценок"""
        tag_scores = Counter()

        for interaction in interactions:
            if interaction.rating and interaction.rating >= 7:  # Высокие оценки
                content = self.get_content_by_interaction(interaction)
                if content and content.tags:
                    for tag in content.tags:
                        # Вес тега зависит от оценки
                        weight = (interaction.rating - 6) * 0.5
                        tag_scores[tag] += weight

        # Возвращаем топ-10 тегов
        return [tag for tag, score in tag_scores.most_common(10)]

    def get_content_by_interaction(self, interaction: UserInteraction):
        """Получение контента по взаимодействию"""
        if interaction.content_type == "book":
            return self.db.query(Book).filter(Book.book_id == interaction.content_id).first()
        elif interaction.content_type == "movie":
            return self.db.query(Movie).filter(Movie.movie_id == interaction.content_id).first()
        elif interaction.content_type == "game":
            return self.db.query(Game).filter(Game.game_id == interaction.content_id).first()
        return None

    def get_recommendations(self, user_id: int, content_type: Optional[str] = None, limit: int = 10) -> List[Dict]:
        """Главный метод получения рекомендаций"""
        # Получаем настройки пользователя
        preferences = self.get_user_preferences(user_id)

        # Получаем последние взаимодействия
        interactions = self.get_user_last_interactions(user_id)

        # Извлекаем предпочитаемые теги
        preferred_tags = self.extract_preferred_tags(interactions)

        # Получаем ID уже оцененного контента
        rated_content = self.get_rated_content_ids(user_id)

        recommendations = []

        # Определяем типы контента для рекомендаций
        content_types = [content_type] if content_type else ["book", "movie", "game"]

        for ctype in content_types:
            content_recs = self.get_content_recommendations(
                ctype, preferred_tags, preferences, rated_content, limit // len(content_types)
            )
            recommendations.extend(content_recs)

        # Перемешиваем и ограничиваем
        random.shuffle(recommendations)
        return recommendations[:limit]

    def get_rated_content_ids(self, user_id: int) -> Dict[str, List[int]]:
        """Получение ID уже оцененного контента"""
        interactions = self.db.query(UserInteraction) \
            .filter(UserInteraction.user_id == user_id) \
            .filter(UserInteraction.rating.isnot(None)) \
            .all()

        rated = {"book": [], "movie": [], "game": []}
        for interaction in interactions:
            rated[interaction.content_type].append(interaction.content_id)

        return rated

    def get_content_recommendations(self, content_type: str, preferred_tags: List[str],
                                    preferences: Dict, rated_content: Dict, limit: int) -> List[Dict]:
        """Получение рекомендаций для конкретного типа контента"""
        # Выбираем модель
        if content_type == "book":
            model = Book
            id_field = "book_id"
        elif content_type == "movie":
            model = Movie
            id_field = "movie_id"
        else:
            model = Game
            id_field = "game_id"

        # Базовый запрос
        query = self.db.query(model)

        # Исключаем уже оцененный контент
        if rated_content[content_type]:
            query = query.filter(~getattr(model, id_field).in_(rated_content[content_type]))

        # Фильтр по популярности (0-100 -> 0.0-10.0)
        popularity_min = (preferences["popularity"] - 20) / 10
        popularity_max = (preferences["popularity"] + 20) / 10
        query = query.filter(
            and_(
                model.popularity_score >= max(0, popularity_min),
                model.popularity_score <= min(10, popularity_max)
            )
        )

        # Фильтр по новизне
        current_year = 2024
        if preferences["newness"] > 70:  # Новое
            year_threshold = current_year - 10
            query = query.filter(model.year >= year_threshold)
        elif preferences["newness"] < 30:  # Старое
            year_threshold = current_year - 20
            query = query.filter(model.year <= year_threshold)

        # Получаем все подходящие записи
        all_content = query.all()

        # Скоринг по тегам
        scored_content = []
        for content in all_content:
            score = self.calculate_tag_score(content.tags or [], preferred_tags)
            scored_content.append({
                "content": content,
                "score": score,
                "type": content_type
            })

        # Сортируем по скору и берем топ
        scored_content.sort(key=lambda x: x["score"], reverse=True)

        return scored_content[:limit]

    def calculate_tag_score(self, content_tags: List[str], preferred_tags: List[str]) -> float:
        """Расчет скора совпадения тегов"""
        if not preferred_tags:
            return random.random()  # Случайный скор если нет предпочтений

        matches = len(set(content_tags) & set(preferred_tags))
        return matches / len(preferred_tags) + random.random() * 0.1  # Добавляем немного случайности