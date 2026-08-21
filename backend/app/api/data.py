"""
Data Generation and Management API endpoints.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.pydantic_models import SampleDataGenerateResponse
from app.data.sample_generator import SampleDataGenerator

router = APIRouter(prefix="/data", tags=["data"])


@router.post("/generate-sample", response_model=SampleDataGenerateResponse)
def generate_sample_data(
    count: int = Query(20, ge=1, le=200, description="Number of finished historical races to generate"),
    scheduled_count: int = Query(0, ge=0, le=50, description="Number of scheduled upcoming races to generate"),
    start_date: str = Query("2024-01-06", description="Starting date for simulated races"),
    db: Session = Depends(get_db),
):
    """
    Generates realistic Japanese horse racing sample dataset with entries and payouts.
    """
    generator = SampleDataGenerator()
    generated = generator.generate_races(
        db=db,
        count=count,
        scheduled_count=scheduled_count,
        start_date=start_date,
    )
    return SampleDataGenerateResponse(
        status="ok",
        generated_races=len(generated),
    )
