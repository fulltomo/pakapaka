"""
Model Training, Active Model Status, and Evaluation REST API.
"""

from typing import Optional, Dict, Any
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.ml.model import HorseRacingModel
from app.ml.trainer import ModelTrainer
from app.schemas.pydantic_models import ModelTrainRequest, ModelTrainResponse

router = APIRouter(prefix="/models", tags=["models"])

# In-memory cache for the loaded active model and its latest training metrics
_active_model: Optional[HorseRacingModel] = None
_latest_metrics: Optional[Dict[str, Any]] = None


def get_active_model() -> Optional[HorseRacingModel]:
    """
    Returns the currently active in-memory model or attempts to load the latest
    persisted model from disk.
    """
    global _active_model
    if _active_model is not None:
        return _active_model

    latest_path = Path(settings.MODEL_DIR) / "latest_model.joblib"
    if latest_path.exists():
        try:
            _active_model = HorseRacingModel.load(latest_path)
            return _active_model
        except Exception:
            return None
    return None


def set_active_model(model: HorseRacingModel, metrics: Optional[Dict[str, Any]] = None) -> None:
    """Sets the in-memory active model and its associated metrics."""
    global _active_model, _latest_metrics
    _active_model = model
    _latest_metrics = metrics


@router.post("/train", response_model=ModelTrainResponse)
def train_model(
    req: Optional[ModelTrainRequest] = None,
    db: Session = Depends(get_db),
):
    """
    Triggers model training from historical finished races in the database.
    Evaluates ROC-AUC, LogLoss, and feature importances, persisting the model to disk.
    """
    request_data = req or ModelTrainRequest()
    trainer = ModelTrainer(
        model_dir=settings.MODEL_DIR,
        test_size=request_data.test_size,
        random_state=request_data.random_state,
    )

    try:
        model, metrics = trainer.train(db=db, save_model=True)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Training failed: {str(e)}")

    set_active_model(model, metrics)

    return ModelTrainResponse(
        status="ok",
        model_version=metrics["model_version"],
        roc_auc=metrics["roc_auc"],
        log_loss=metrics["log_loss"],
        feature_importance=metrics["feature_importance"],
        trained_samples=metrics["train_samples"] + metrics["test_samples"],
    )


@router.get("/active")
def get_active_model_status():
    """
    Returns metadata, status, feature importances, and latest evaluation metrics
    for the active model.
    """
    model = get_active_model()
    if model is None:
        return {
            "status": "not_trained",
            "model_version": None,
            "feature_importance": {},
            "metrics": None,
            "roc_auc": None,
            "log_loss": None,
        }

    return {
        "status": "active",
        "model_version": model.model_version,
        "feature_importance": model.get_feature_importances(),
        "metrics": _latest_metrics or {},
        "roc_auc": _latest_metrics.get("roc_auc") if _latest_metrics else None,
        "log_loss": _latest_metrics.get("log_loss") if _latest_metrics else None,
    }
