"""
API Routers aggregation module.
"""

from fastapi import APIRouter
from app.api import races, models, predictions, backtest, simulation, data

api_router = APIRouter()

api_router.include_router(races.router)
api_router.include_router(models.router)
api_router.include_router(predictions.router)
api_router.include_router(backtest.router)
api_router.include_router(simulation.router)
api_router.include_router(data.router)
