import sys
from contextlib import asynccontextmanager
from pathlib import Path

# Ensure backend root is in sys.path for direct imports
BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import init_db
from app.api import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifecycle management:
    Initializes database schema, creates default forward wallet session,
    and ensures model / cache storage directories exist.
    """
    Path(settings.MODEL_DIR).mkdir(parents=True, exist_ok=True)
    Path(settings.CACHE_DIR).mkdir(parents=True, exist_ok=True)
    init_db()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    description="競馬データ分析、LightGBM機械学習予想＆回収率バックテスト・シミュレーションシステム",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS for frontend communication (Vite / React)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register aggregated API router
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/api/health", tags=["system"])
@app.get("/health", tags=["system"])
def health_check():
    """
    System health check endpoint.
    """
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": "1.0.0",
    }


@app.get("/", tags=["system"])
def root():
    """
    API Root endpoint.
    """
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "docs_url": "/docs",
        "health_url": "/api/health",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
