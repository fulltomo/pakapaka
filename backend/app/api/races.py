"""
Race Data Management, Retrieval, Sample Generation, and Scraping REST API.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.schema import Race
from app.schemas.pydantic_models import (
    RaceSchema,
    RaceDetailSchema,
    SampleDataGenerateResponse,
    SampleDataGenerateRequest,
)
from app.data.sample_generator import SampleDataGenerator
from app.data.scraper import NetkeibaScraper

router = APIRouter(prefix="/races", tags=["races"])


@router.get("", response_model=List[RaceSchema])
def list_races(
    date: Optional[str] = Query(None, description="Filter by race date (YYYY-MM-DD)"),
    race_course: Optional[str] = Query(None, description="Filter by race course (e.g. 東京)"),
    status: Optional[str] = Query(None, description="Filter by status (scheduled, finished)"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """
    Retrieves a paginated list of races filtered by date, race course, or status.
    """
    query = db.query(Race)

    if date:
        query = query.filter(Race.date == date)
    if race_course:
        query = query.filter(Race.race_course == race_course)
    if status:
        query = query.filter(Race.status == status)

    races = query.order_by(Race.date.asc(), Race.id.asc()).offset(offset).limit(limit).all()
    return [RaceSchema.model_validate(r) for r in races]


@router.get("/{race_id}", response_model=RaceDetailSchema)
def get_race_detail(
    race_id: str,
    db: Session = Depends(get_db),
):
    """
    Retrieves full race details including entries, payouts, and model predictions.
    """
    race = db.query(Race).filter(Race.id == race_id).first()
    if race is None:
        raise HTTPException(status_code=404, detail=f"Race with id '{race_id}' not found.")
    return RaceDetailSchema.model_validate(race)


@router.post("/sample", response_model=SampleDataGenerateResponse)
def generate_sample_races(
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


@router.post("/scrape", response_model=RaceDetailSchema)
def scrape_netkeiba_race(
    race_id: str = Query(..., description="Netkeiba race ID (e.g., 202405010101)"),
    use_cache: bool = Query(True, description="Use cached HTML if available"),
    db: Session = Depends(get_db),
):
    """
    Scrapes race results, entries, and payout data from netkeiba and persists them to the database.
    """
    scraper = NetkeibaScraper()
    race = scraper.scrape_race_and_save(race_id=race_id, db=db, use_cache=use_cache)
    if race is None:
        raise HTTPException(
            status_code=400,
            detail=f"Could not scrape or parse race data for ID '{race_id}'.",
        )
    return RaceDetailSchema.model_validate(race)
