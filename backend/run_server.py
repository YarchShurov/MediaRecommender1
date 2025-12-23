
import os
import sys
from pathlib import Path

# Добавляем корневую директорию в PYTHONPATH
root_dir = Path(__file__).parent
sys.path.insert(0, str(root_dir))

if __name__ == "__main__":
    # Проверяем наличие .env файла
    env_file = root_dir / ".env"
    if not env_file.exists():
        print("⚠️  Файл .env не найден!")
        print("Создайте файл .env со следующим содержимым:")
        print("""
DATABASE_URL=postgresql://username:password@localhost/mediarecommender
SECRET_KEY=your-very-secret-key-here
REDIS_URL=redis://localhost:6379
        """)
        sys.exit(1)

    # Запускаем сервер
    from app.main import app
    from app.core.init_db import initialize_database
    import uvicorn

    print("🚀 Запуск MediaRecommender API...")
    print("📊 Инициализация базы данных...")

    try:
        initialize_database()
        print("✅ База данных готова!")
    except Exception as e:
        print(f"❌ Ошибка инициализации БД: {e}")
        print("Убедитесь, что PostgreSQL запущен и настройки в .env корректны")
        sys.exit(1)

    print("🌐 Запуск веб-сервера...")
    print("📖 API документация: http://localhost:8000/docs")
    print("🎯 API эндпоинт: http://localhost:8000")

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )