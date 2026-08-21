import os
from pydantic import BaseModel, Field


class Settings(BaseModel):
    APP_NAME: str = "PakaPaka - 競馬予想＆疑似運用シミュレーション"
    API_V1_STR: str = "/api"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./pakapaka.db")
    MODEL_DIR: str = os.getenv("MODEL_DIR", "backend/data/models")
    CACHE_DIR: str = os.getenv("CACHE_DIR", "backend/data/cache")
    DEFAULT_WALLET_INITIAL_POINTS: int = 100000
    DEFAULT_FORWARD_SESSION_ID: str = "forward_live"
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "*",
    ]


settings = Settings()
