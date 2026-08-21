"""
Race Predictions and Expected Value (EV) REST API.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.schema import Race
from app.schemas.pydantic_models import PredictionSchema
from app.ml.predictor import Predictor
from app.api.models import get_active_model

router = APIRouter(prefix="/predictions", tags=["predictions"])


@router.get("/{race_id}", response_model=List[PredictionSchema])
def get_or_generate_predictions(
    race_id: str,
    db: Session = Depends(get_db),
):
    """
    Generates and persists calibrated win/place probabilities, expected values (EV),
    and recommendation marks (◎, ◯, ▲, ☆, -) for all entries in a race using the active ML model.
    """
    race = db.query(Race).filter(Race.id == race_id).first()
    if race is None:
        raise HTTPException(status_code=404, detail=f"Race with id '{race_id}' not found.")

    model = get_active_model()
    if model is None:
        raise HTTPException(
            status_code=400,
            detail="No active trained model found. Please train a model first via POST /api/models/train.",
        )

    predictor = Predictor(model=model)
    preds = predictor.predict_race(race)
    saved_records = predictor.save_predictions(db=db, race=race, predictions=preds)

    return [PredictionSchema.model_validate(p) for p in saved_records]
