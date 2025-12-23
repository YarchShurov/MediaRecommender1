from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from app.api import auth, content, recommendations, simulation, interactions
from app.core.init_db import initialize_database
from app.api import auth, content, recommendations, simulation, interactions, admin

# Добавь строку выше в импорты, затем:

app = FastAPI(
    title="MediaRecommender API",
    description="Система рекомендаций медиаконтента с симуляцией взаимодействия",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение роутеров
app.include_router(auth.router)
app.include_router(content.router)
app.include_router(recommendations.router)
app.include_router(simulation.router)
app.include_router(interactions.router)
app.include_router(admin.router)

@app.get("/")
async def root():
    return {
        "message": "MediaRecommender API",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "auth": "/auth",
            "content": "/content",
            "recommendations": "/recommendations",
            "simulation": "/simulation",
            "interactions": "/interactions"
        }
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": "2024-01-01T00:00:00Z"}


# Обработчик ошибок
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)}"}
    )


if __name__ == "__main__":
    print("Инициализация базы данных...")
    initialize_database()

    print("Запуск сервера...")
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )