from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.models import Book, Movie, Game, User
from app.schemas import (
    BookCreate, BookResponse, MovieCreate, MovieResponse,
    GameCreate, GameResponse
)
from app.core.auth import get_current_user, require_admin

router = APIRouter(prefix="/content", tags=["Content"])


# Книги
@router.get("/books", response_model=List[BookResponse])
async def get_books(
        skip: int = Query(0, ge=0),
        limit: int = Query(10, ge=1, le=100),
        genre: Optional[str] = None,
        year: Optional[int] = None,
        search: Optional[str] = None,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Получение списка книг с фильтрацией"""
    query = db.query(Book)

    if genre:
        query = query.filter(Book.genre.ilike(f"%{genre}%"))

    if year:
        query = query.filter(Book.year == year)

    if search:
        query = query.filter(
            (Book.title.ilike(f"%{search}%")) |
            (Book.author.ilike(f"%{search}%"))
        )

    books = query.offset(skip).limit(limit).all()
    return books


@router.get("/books/{book_id}", response_model=BookResponse)
async def get_book(
        book_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Получение книги по ID"""
    book = db.query(Book).filter(Book.book_id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book


@router.post("/books", response_model=BookResponse)
async def create_book(
        book_data: BookCreate,
        db: Session = Depends(get_db),
        admin_user: User = Depends(require_admin)
):
    """Создание новой книги (только для администраторов)"""
    book = Book(**book_data.dict())
    db.add(book)
    db.commit()
    db.refresh(book)
    return book


@router.put("/books/{book_id}", response_model=BookResponse)
async def update_book(
        book_id: int,
        book_data: BookCreate,
        db: Session = Depends(get_db),
        admin_user: User = Depends(require_admin)
):
    """Обновление книги (только для администраторов)"""
    book = db.query(Book).filter(Book.book_id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    for field, value in book_data.dict().items():
        setattr(book, field, value)

    db.commit()
    db.refresh(book)
    return book


@router.delete("/books/{book_id}")
async def delete_book(
        book_id: int,
        db: Session = Depends(get_db),
        admin_user: User = Depends(require_admin)
):
    """Удаление книги (только для администраторов)"""
    book = db.query(Book).filter(Book.book_id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    db.delete(book)
    db.commit()
    return {"message": "Book deleted successfully"}


# Фильмы
@router.get("/movies", response_model=List[MovieResponse])
async def get_movies(
        skip: int = Query(0, ge=0),
        limit: int = Query(10, ge=1, le=100),
        genre: Optional[str] = None,
        year: Optional[int] = None,
        search: Optional[str] = None,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Получение списка фильмов с фильтрацией"""
    query = db.query(Movie)

    if genre:
        query = query.filter(Movie.genre.ilike(f"%{genre}%"))

    if year:
        query = query.filter(Movie.year == year)

    if search:
        query = query.filter(
            (Movie.title.ilike(f"%{search}%")) |
            (Movie.director.ilike(f"%{search}%"))
        )

    movies = query.offset(skip).limit(limit).all()
    return movies


@router.get("/movies/{movie_id}", response_model=MovieResponse)
async def get_movie(
        movie_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Получение фильма по ID"""
    movie = db.query(Movie).filter(Movie.movie_id == movie_id).first()
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")
    return movie


@router.post("/movies", response_model=MovieResponse)
async def create_movie(
        movie_data: MovieCreate,
        db: Session = Depends(get_db),
        admin_user: User = Depends(require_admin)
):
    """Создание нового фильма (только для администраторов)"""
    movie = Movie(**movie_data.dict())
    db.add(movie)
    db.commit()
    db.refresh(movie)
    return movie


@router.put("/movies/{movie_id}", response_model=MovieResponse)
async def update_movie(
        movie_id: int,
        movie_data: MovieCreate,
        db: Session = Depends(get_db),
        admin_user: User = Depends(require_admin)
):
    """Обновление фильма (только для администраторов)"""
    movie = db.query(Movie).filter(Movie.movie_id == movie_id).first()
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")

    for field, value in movie_data.dict().items():
        setattr(movie, field, value)

    db.commit()
    db.refresh(movie)
    return movie


@router.delete("/movies/{movie_id}")
async def delete_movie(
        movie_id: int,
        db: Session = Depends(get_db),
        admin_user: User = Depends(require_admin)
):
    """Удаление фильма (только для администраторов)"""
    movie = db.query(Movie).filter(Movie.movie_id == movie_id).first()
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")

    db.delete(movie)
    db.commit()
    return {"message": "Movie deleted successfully"}


# Игры
@router.get("/games", response_model=List[GameResponse])
async def get_games(
        skip: int = Query(0, ge=0),
        limit: int = Query(10, ge=1, le=100),
        genre: Optional[str] = None,
        year: Optional[int] = None,
        search: Optional[str] = None,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Получение списка игр с фильтрацией"""
    query = db.query(Game)

    if genre:
        query = query.filter(Game.genre.ilike(f"%{genre}%"))

    if year:
        query = query.filter(Game.year == year)

    if search:
        query = query.filter(
            (Game.title.ilike(f"%{search}%")) |
            (Game.developer.ilike(f"%{search}%"))
        )

    games = query.offset(skip).limit(limit).all()
    return games


@router.get("/games/{game_id}", response_model=GameResponse)
async def get_game(
        game_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Получение игры по ID"""
    game = db.query(Game).filter(Game.game_id == game_id).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    return game


@router.post("/games", response_model=GameResponse)
async def create_game(
        game_data: GameCreate,
        db: Session = Depends(get_db),
        admin_user: User = Depends(require_admin)
):
    """Создание новой игры (только для администраторов)"""
    game = Game(**game_data.dict())
    db.add(game)
    db.commit()
    db.refresh(game)
    return game


@router.put("/games/{game_id}", response_model=GameResponse)
async def update_game(
        game_id: int,
        game_data: GameCreate,
        db: Session = Depends(get_db),
        admin_user: User = Depends(require_admin)
):
    """Обновление игры (только для администраторов)"""
    game = db.query(Game).filter(Game.game_id == game_id).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    for field, value in game_data.dict().items():
        setattr(game, field, value)

    db.commit()
    db.refresh(game)
    return game


@router.delete("/games/{game_id}")
async def delete_game(
        game_id: int,
        db: Session = Depends(get_db),
        admin_user: User = Depends(require_admin)
):
    """Удаление игры (только для администраторов)"""
    game = db.query(Game).filter(Game.game_id == game_id).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    db.delete(game)
    db.commit()
    return {"message": "Game deleted successfully"}


# Общие эндпоинты
@router.get("/search")
async def search_all_content(
        query: str = Query(..., min_length=2),
        content_type: Optional[str] = Query(None, regex="^(book|movie|game)$"),
        limit: int = Query(20, ge=1, le=100),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Поиск по всем типам контента"""
    results = {"books": [], "movies": [], "games": []}

    if not content_type or content_type == "book":
        books = db.query(Book).filter(
            (Book.title.ilike(f"%{query}%")) |
            (Book.author.ilike(f"%{query}%"))
        ).limit(limit // 3 if not content_type else limit).all()
        results["books"] = books

    if not content_type or content_type == "movie":
        movies = db.query(Movie).filter(
            (Movie.title.ilike(f"%{query}%")) |
            (Movie.director.ilike(f"%{query}%"))
        ).limit(limit // 3 if not content_type else limit).all()
        results["movies"] = movies

    if not content_type or content_type == "game":
        games = db.query(Game).filter(
            (Game.title.ilike(f"%{query}%")) |
            (Game.developer.ilike(f"%{query}%"))
        ).limit(limit // 3 if not content_type else limit).all()
        results["games"] = games

    return results