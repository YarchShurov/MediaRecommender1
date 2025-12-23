from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Float, Boolean, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Role(Base):
    __tablename__ = "roles"

    role_id = Column(Integer, primary_key=True, index=True)
    role_name = Column(String(50), unique=True, nullable=False)
    permissions = Column(JSON)

    users = relationship("User", back_populates="role")


class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role_id = Column(Integer, ForeignKey("roles.role_id"))
    created_at = Column(DateTime, server_default=func.now())
    preferences = Column(JSON, default={})
    is_active = Column(Boolean, default=True)

    role = relationship("Role", back_populates="users")
    interactions = relationship("UserInteraction", back_populates="user")


class Book(Base):
    __tablename__ = "books"

    book_id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    author = Column(String(255), nullable=False)
    genre = Column(String(100))
    year = Column(Integer)
    popularity_score = Column(Float, default=0.0)
    description = Column(Text)
    tags = Column(JSON, default=[])
    created_at = Column(DateTime, server_default=func.now())


class Movie(Base):
    __tablename__ = "movies"

    movie_id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    director = Column(String(255), nullable=False)
    genre = Column(String(100))
    year = Column(Integer)
    popularity_score = Column(Float, default=0.0)
    description = Column(Text)
    tags = Column(JSON, default=[])
    created_at = Column(DateTime, server_default=func.now())


class Game(Base):
    __tablename__ = "games"

    game_id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    developer = Column(String(255), nullable=False)
    genre = Column(String(100))
    year = Column(Integer)
    popularity_score = Column(Float, default=0.0)
    description = Column(Text)
    tags = Column(JSON, default=[])
    created_at = Column(DateTime, server_default=func.now())


class UserInteraction(Base):
    __tablename__ = "user_interactions"

    interaction_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"))
    content_type = Column(String(20), nullable=False)  # 'book', 'movie', 'game'
    content_id = Column(Integer, nullable=False)
    interaction_type = Column(String(20), nullable=False)  # 'started', 'completed', 'rated', 'dropped'
    rating = Column(Integer)  # 1-10
    progress_percent = Column(Integer, default=0)
    start_date = Column(DateTime, server_default=func.now())
    completion_date = Column(DateTime)
    simulation_duration = Column(Integer)  # в секундах
    tags_extracted = Column(JSON, default=[])

    user = relationship("User", back_populates="interactions")


class AdminAction(Base):
    __tablename__ = "admin_actions"

    action_id = Column(Integer, primary_key=True, index=True)
    admin_user_id = Column(Integer, ForeignKey("users.user_id"))
    action_type = Column(String(20), nullable=False)
    target_table = Column(String(50), nullable=False)
    target_id = Column(Integer)
    old_values = Column(JSON)
    new_values = Column(JSON)
    timestamp = Column(DateTime, server_default=func.now())