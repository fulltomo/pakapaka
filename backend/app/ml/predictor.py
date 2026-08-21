"""
Inference and Expected Value Engine for Horse Racing Predictions.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from app.models.schema import Race, Prediction
from app.ml.features import FeatureExtractor
from app.ml.model import HorseRacingModel


@dataclass
class PredictionResult:
    """
    Structured prediction output for a single race entry.
    """
    horse_number: int
    win_prob: float
    place_prob: float
    expected_value: float
    recommendation_mark: str = "-"
    horse_name: Optional[str] = None
    odds: float = 1.0
    model_version: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "horse_number": self.horse_number,
            "horse_name": self.horse_name,
            "win_prob": self.win_prob,
            "place_prob": self.place_prob,
            "odds": self.odds,
            "expected_value": self.expected_value,
            "recommendation_mark": self.recommendation_mark,
            "model_version": self.model_version,
        }


class Predictor:
    """
    Executes model inference on race entries, calculates expected values (EV = p * odds),
    and assigns standard Japanese racing recommendation marks (◎, ◯, ▲, ☆, -).
    """

    def __init__(
        self,
        model: HorseRacingModel,
        feature_extractor: Optional[FeatureExtractor] = None,
    ):
        self.model = model
        self.feature_extractor = feature_extractor or FeatureExtractor()

    def predict_race(self, race: Race) -> List[PredictionResult]:
        """
        Generates calibrated win/place predictions, EV, and recommendation marks for all entries in a race.

        Parameters
        ----------
        race : Race
            SQLAlchemy Race entity with populated entries.

        Returns
        -------
        List[PredictionResult]
            List of prediction results ordered by horse_number.
        """
        if not race.entries:
            return []

        # Build DataFrame from race entries
        records = []
        for entry in race.entries:
            records.append({
                "race_id": race.id,
                "horse_id": entry.horse_id,
                "horse_name": entry.horse_name,
                "post_position": entry.post_position,
                "horse_number": entry.horse_number,
                "handicap_weight": entry.handicap_weight,
                "horse_weight": entry.horse_weight,
                "horse_weight_diff": entry.horse_weight_diff,
                "sex": entry.sex,
                "age": entry.age,
                "distance": race.distance,
                "surface": race.surface,
                "track_condition": race.track_condition,
                "odds": entry.odds,
                "popularity": entry.popularity,
                "jockey_name": entry.jockey_name,
                "trainer_name": entry.trainer_name,
            })

        df = pd.DataFrame(records)

        # Feature extraction
        features_df, feature_cols = self.feature_extractor.extract_features(
            df,
            is_training=False,
        )

        cols_to_use = self.model.feature_names if self.model.feature_names else feature_cols
        X = features_df[cols_to_use]

        # Raw model inference
        raw_win_probs = self.model.predict_win_proba(X)
        raw_place_probs = self.model.predict_place_proba(X)

        # Race-level win probability calibration (normalization: sum of win probabilities = 1.0)
        sum_win = float(np.sum(raw_win_probs))
        if sum_win > 0.0:
            norm_win_probs = raw_win_probs / sum_win
        else:
            norm_win_probs = np.ones_like(raw_win_probs) / len(raw_win_probs)

        # Ensure bounds
        norm_win_probs = np.clip(norm_win_probs, 0.0001, 0.9999)
        # Re-normalize to guarantee exact sum = 1.0
        norm_win_probs = norm_win_probs / np.sum(norm_win_probs)
        norm_place_probs = np.clip(raw_place_probs, 0.0, 1.0)

        # Calculate EV and build preliminary objects
        results_map: Dict[int, PredictionResult] = {}
        for idx, entry in enumerate(race.entries):
            w_prob = round(float(norm_win_probs[idx]), 4)
            p_prob = round(float(norm_place_probs[idx]), 4)
            odds = float(entry.odds)
            ev = round(w_prob * odds, 4)

            results_map[entry.horse_number] = PredictionResult(
                horse_number=entry.horse_number,
                horse_name=entry.horse_name,
                win_prob=w_prob,
                place_prob=p_prob,
                odds=odds,
                expected_value=ev,
                recommendation_mark="-",
                model_version=self.model.model_version,
            )

        # Assign recommendation marks based on win probability and EV ranking
        # 1. Sort entries by win probability descending
        sorted_by_prob = sorted(results_map.values(), key=lambda r: r.win_prob, reverse=True)

        if len(sorted_by_prob) >= 1:
            sorted_by_prob[0].recommendation_mark = "◎"  # 本命 (Favorite)

        if len(sorted_by_prob) >= 2:
            sorted_by_prob[1].recommendation_mark = "◯"  # 対抗 (Contender)

        if len(sorted_by_prob) >= 3:
            sorted_by_prob[2].recommendation_mark = "▲"  # 単穴 (Third Pick)

        if len(sorted_by_prob) >= 4:
            # For 4th and beyond, find the horse with the highest EV as the value pick (☆ / 穴馬)
            underdogs = sorted_by_prob[3:]
            best_value_horse = max(underdogs, key=lambda r: r.expected_value)
            best_value_horse.recommendation_mark = "☆"

        # Return in original horse_number order
        ordered_results = [results_map[entry.horse_number] for entry in race.entries]
        return ordered_results

    def save_predictions(
        self,
        db: Session,
        race: Race,
        predictions: List[PredictionResult],
    ) -> List[Prediction]:
        """
        Persists race predictions into the database, replacing previous predictions for the race.

        Parameters
        ----------
        db : Session
            SQLAlchemy database session.
        race : Race
            The target race entity.
        predictions : List[PredictionResult]
            Generated prediction results.

        Returns
        -------
        List[Prediction]
            List of saved SQLAlchemy Prediction records.
        """
        # Delete existing predictions for this race to avoid duplicates
        db.query(Prediction).filter(Prediction.race_id == race.id).delete()

        saved_records = []
        for pred in predictions:
            record = Prediction(
                race_id=race.id,
                horse_number=pred.horse_number,
                model_version=pred.model_version or self.model.model_version,
                win_prob=pred.win_prob,
                place_prob=pred.place_prob,
                expected_value=pred.expected_value,
                recommendation_mark=pred.recommendation_mark,
            )
            db.add(record)
            saved_records.append(record)

        db.commit()
        return saved_records
