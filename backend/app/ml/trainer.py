"""
Model Training and Evaluation Pipeline for Horse Racing Models.
"""

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, List
import numpy as np
import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session
from sklearn.metrics import roc_auc_score, log_loss, brier_score_loss

from app.models.schema import Race, RaceEntry
from app.ml.features import FeatureExtractor
from app.ml.history import add_history_features
from app.ml.model import HorseRacingModel


class ModelTrainer:
    """
    Handles data preparation from historical database races, time-series splitting,
    LightGBM model training with calibration, evaluation metric computation, and model persistence.
    """

    def __init__(
        self,
        feature_extractor: Optional[FeatureExtractor] = None,
        test_size: float = 0.2,
        random_state: int = 42,
        model_dir: str = "data/models",
        model_version: Optional[str] = None,
        calibration_method: str = "sigmoid",
        race_courses: Optional[List[str]] = None,
    ):
        self.feature_extractor = feature_extractor or FeatureExtractor()
        self.test_size = test_size
        self.random_state = random_state
        self.model_dir = model_dir
        self.model_version = model_version or f"v_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        self.calibration_method = calibration_method
        # Restrict training to these racecourses; None trains on everything.
        self.race_courses = race_courses

    def _extract_dataset_from_db(self, db: Session) -> pd.DataFrame:
        """
        Loads finished races joined with their entries as a single flat DataFrame.
        """
        stmt = (
            select(
                Race.id.label("race_id"),
                Race.date.label("race_date"),
                Race.race_course,
                Race.race_number,
                RaceEntry.horse_id,
                RaceEntry.horse_name,
                RaceEntry.post_position,
                RaceEntry.horse_number,
                RaceEntry.handicap_weight,
                RaceEntry.horse_weight,
                RaceEntry.horse_weight_diff,
                RaceEntry.sex,
                RaceEntry.age,
                Race.distance,
                Race.surface,
                Race.track_condition,
                RaceEntry.odds,
                RaceEntry.popularity,
                RaceEntry.jockey_name,
                RaceEntry.trainer_name,
                RaceEntry.finish_position,
                RaceEntry.finish_time,
                RaceEntry.margin,
            )
            .join(RaceEntry, RaceEntry.race_id == Race.id)
            .where(Race.status == "finished", RaceEntry.finish_position.isnot(None))
            .order_by(Race.date.asc(), Race.id.asc())
        )

        if self.race_courses:
            stmt = stmt.where(Race.race_course.in_(self.race_courses))

        df = pd.read_sql(stmt, db.connection())
        if df.empty:
            raise ValueError("No valid finished race entries found with finish positions.")
        return df

    def _safe_roc_auc(self, y_true: np.ndarray, y_pred: np.ndarray) -> float:
        """Computes ROC-AUC safely handling single-class edge cases."""
        unique_classes = np.unique(y_true)
        if len(unique_classes) < 2:
            return 0.5
        try:
            return float(roc_auc_score(y_true, y_pred))
        except Exception:
            return 0.5

    def _safe_log_loss(self, y_true: np.ndarray, y_pred: np.ndarray) -> float:
        """Computes LogLoss safely with clipping."""
        clipped_pred = np.clip(y_pred, 1e-7, 1.0 - 1e-7)
        try:
            return float(log_loss(y_true, clipped_pred, labels=[0, 1]))
        except Exception:
            return 0.0

    def _safe_brier_score(self, y_true: np.ndarray, y_pred: np.ndarray) -> float:
        """Computes Brier Score Loss safely."""
        try:
            return float(brier_score_loss(y_true, y_pred))
        except Exception:
            return 0.0

    def train(
        self,
        db: Session,
        test_size: Optional[float] = None,
        save_model: bool = True,
    ) -> Tuple[HorseRacingModel, Dict[str, Any]]:
        """
        Executes full training lifecycle:
        1. Query and build race entry DataFrame.
        2. Extract features and binary training targets.
        3. Split chronologically by race into train/test sets.
        4. Fit calibrated LightGBM model.
        5. Evaluate metrics on test set.
        6. Persist model to disk (if save_model=True).

        Returns
        -------
        model : HorseRacingModel
            The trained and calibrated model.
        metrics : dict
            Evaluation metrics including ROC-AUC, LogLoss, Brier score, and feature importances.
        """
        eff_test_size = test_size if test_size is not None else self.test_size
        raw_df = self._extract_dataset_from_db(db)
        raw_df, _ = add_history_features(raw_df)

        # Feature extraction with training targets
        features_df, feature_cols = self.feature_extractor.extract_features(
            raw_df,
            is_training=True,
        )

        # Race-level chronological split to prevent inter-race data leakage
        unique_races = raw_df["race_id"].drop_duplicates().tolist()
        n_races = len(unique_races)

        if eff_test_size > 0.0 and n_races >= 2:
            n_test_races = max(1, int(n_races * eff_test_size))
            n_train_races = n_races - n_test_races
            train_races = set(unique_races[:n_train_races])
            test_races = set(unique_races[n_train_races:])

            train_mask = features_df["race_id"].isin(train_races)
            test_mask = features_df["race_id"].isin(test_races)
        else:
            train_mask = np.ones(len(features_df), dtype=bool)
            test_mask = train_mask

        X_train = features_df.loc[train_mask, feature_cols]
        y_win_train = features_df.loc[train_mask, "target_win"].values
        y_place_train = features_df.loc[train_mask, "target_place"].values

        X_test = features_df.loc[test_mask, feature_cols]
        y_win_test = features_df.loc[test_mask, "target_win"].values
        y_place_test = features_df.loc[test_mask, "target_place"].values

        # Initialize and fit model
        model = HorseRacingModel(
            model_version=self.model_version,
            calibration_method=self.calibration_method,
            random_state=self.random_state,
        )
        model.fit(X_train, y_win_train, y_place_train, feature_names=feature_cols)

        # Evaluation
        win_probs_test = model.predict_win_proba(X_test)
        place_probs_test = model.predict_place_proba(X_test)

        roc_auc = self._safe_roc_auc(y_win_test, win_probs_test)
        ll = self._safe_log_loss(y_win_test, win_probs_test)
        brier = self._safe_brier_score(y_win_test, win_probs_test)

        place_roc_auc = self._safe_roc_auc(y_place_test, place_probs_test)
        place_ll = self._safe_log_loss(y_place_test, place_probs_test)
        place_brier = self._safe_brier_score(y_place_test, place_probs_test)

        feature_importances = model.get_feature_importances()

        metrics: Dict[str, Any] = {
            "model_version": self.model_version,
            "roc_auc": round(roc_auc, 4),
            "log_loss": round(ll, 4),
            "brier_score": round(brier, 4),
            "place_roc_auc": round(place_roc_auc, 4),
            "place_log_loss": round(place_ll, 4),
            "place_brier_score": round(place_brier, 4),
            "train_samples": int(len(X_train)),
            "test_samples": int(len(X_test)),
            "feature_importance": feature_importances,
        }

        # Model persistence
        if save_model:
            out_dir = Path(self.model_dir)
            out_dir.mkdir(parents=True, exist_ok=True)
            versioned_path = out_dir / f"model_{self.model_version}.joblib"
            latest_path = out_dir / "latest_model.joblib"
            model.save(versioned_path)
            model.save(latest_path)

        return model, metrics
