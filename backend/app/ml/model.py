"""
LightGBM Horse Racing ML Model with Probability Calibration and Persistence.
"""

import os
from pathlib import Path
from typing import List, Dict, Optional, Any, Union
import numpy as np
import pandas as pd
import joblib
from lightgbm import LGBMClassifier
from sklearn.calibration import CalibratedClassifierCV


class HorseRacingModel:
    """
    LightGBM binary classification model wrapper for horse racing win (1st place)
    and place (top 3) predictions with probability calibration.
    """

    def __init__(
        self,
        model_version: str = "v1.0.0",
        calibration_method: str = "sigmoid",
        n_estimators: int = 100,
        learning_rate: float = 0.05,
        num_leaves: int = 31,
        max_depth: int = 5,
        min_child_samples: int = 5,
        random_state: int = 42,
    ):
        self.model_version = model_version
        self.calibration_method = calibration_method
        self.n_estimators = n_estimators
        self.learning_rate = learning_rate
        self.num_leaves = num_leaves
        self.max_depth = max_depth
        self.min_child_samples = min_child_samples
        self.random_state = random_state

        self.feature_names: List[str] = []
        self.is_fitted: bool = False

        self.win_model: Optional[Union[CalibratedClassifierCV, LGBMClassifier]] = None
        self.place_model: Optional[Union[CalibratedClassifierCV, LGBMClassifier]] = None
        self._raw_feature_importances: Dict[str, float] = {}

    def _create_base_classifier(self) -> LGBMClassifier:
        return LGBMClassifier(
            n_estimators=self.n_estimators,
            learning_rate=self.learning_rate,
            num_leaves=self.num_leaves,
            max_depth=self.max_depth,
            min_child_samples=self.min_child_samples,
            random_state=self.random_state,
            verbose=-1,
        )

    def _fit_calibrated_model(
        self,
        X: np.ndarray,
        y: np.ndarray,
    ) -> Union[CalibratedClassifierCV, LGBMClassifier]:
        """
        Fits a classifier with probability calibration, handling sample size edge cases gracefully.
        """
        base_clf = self._create_base_classifier()
        counts = np.bincount(y)
        min_class_count = int(np.min(counts)) if len(counts) > 1 else 0

        # Calibration requires at least 2 samples per class for 2-fold CV, 3 for 3-fold CV
        if min_class_count >= 3:
            cv = 3
        elif min_class_count >= 2:
            cv = 2
        else:
            cv = None

        if cv is not None and self.calibration_method in ("sigmoid", "isotonic"):
            calibrated = CalibratedClassifierCV(
                estimator=base_clf,
                method=self.calibration_method,
                cv=cv,
            )
            calibrated.fit(X, y)
            return calibrated
        else:
            base_clf.fit(X, y)
            return base_clf

    def fit(
        self,
        X: Union[pd.DataFrame, np.ndarray],
        y_win: Union[pd.Series, np.ndarray],
        y_place: Union[pd.Series, np.ndarray],
        feature_names: Optional[List[str]] = None,
    ) -> "HorseRacingModel":
        """
        Fits win and place models on tabular feature matrix X and binary targets.
        """
        if isinstance(X, pd.DataFrame):
            self.feature_names = feature_names or list(X.columns)
            X_arr = X.to_numpy(dtype=np.float64)
        else:
            X_arr = np.asarray(X, dtype=np.float64)
            self.feature_names = feature_names or [f"feature_{i}" for i in range(X_arr.shape[1])]

        y_win_arr = np.asarray(y_win, dtype=np.int32)
        y_place_arr = np.asarray(y_place, dtype=np.int32)

        # Fit win & place models
        self.win_model = self._fit_calibrated_model(X_arr, y_win_arr)
        self.place_model = self._fit_calibrated_model(X_arr, y_place_arr)

        self._compute_feature_importances()
        self.is_fitted = True
        return self

    def _compute_feature_importances(self) -> None:
        """
        Extracts and averages feature importances from fitted base estimators.
        """
        importances_list = []

        if isinstance(self.win_model, CalibratedClassifierCV) and hasattr(self.win_model, "calibrated_classifiers_"):
            for calibrated_classifier in self.win_model.calibrated_classifiers_:
                estimator = getattr(calibrated_classifier, "estimator", None)
                if estimator is not None and hasattr(estimator, "feature_importances_"):
                    importances_list.append(estimator.feature_importances_)
        elif hasattr(self.win_model, "feature_importances_"):
            importances_list.append(self.win_model.feature_importances_)

        if importances_list:
            avg_importances = np.mean(importances_list, axis=0)
            total = float(np.sum(avg_importances))
            if total > 0:
                normalized = avg_importances / total
            else:
                normalized = np.zeros_like(avg_importances)

            self._raw_feature_importances = {
                name: float(imp) for name, imp in zip(self.feature_names, normalized)
            }
        else:
            self._raw_feature_importances = {name: 0.0 for name in self.feature_names}

    def _extract_proba(
        self,
        model: Union[CalibratedClassifierCV, LGBMClassifier, None],
        X: Union[pd.DataFrame, np.ndarray],
    ) -> np.ndarray:
        if model is None or not self.is_fitted:
            raise RuntimeError("Model is not fitted yet. Call fit() before predicting.")

        if isinstance(X, pd.DataFrame):
            if self.feature_names:
                X_mat = X[self.feature_names].to_numpy(dtype=np.float64)
            else:
                X_mat = X.to_numpy(dtype=np.float64)
        else:
            X_mat = np.asarray(X, dtype=np.float64)

        proba = model.predict_proba(X_mat)
        if proba.ndim == 2 and proba.shape[1] >= 2:
            return proba[:, 1]
        elif proba.ndim == 2 and proba.shape[1] == 1:
            return proba[:, 0]
        return proba

    def predict_win_proba(self, X: Union[pd.DataFrame, np.ndarray]) -> np.ndarray:
        """
        Predicts calibrated probability of finishing 1st (Win / 単勝勝率) for each entry.
        """
        raw_probs = self._extract_proba(self.win_model, X)
        return np.clip(raw_probs, 0.0, 1.0)

    def predict_place_proba(self, X: Union[pd.DataFrame, np.ndarray]) -> np.ndarray:
        """
        Predicts calibrated probability of finishing in top 3 (Place / 複勝圏確率) for each entry.
        """
        raw_probs = self._extract_proba(self.place_model, X)
        return np.clip(raw_probs, 0.0, 1.0)

    def get_feature_importances(self) -> Dict[str, float]:
        """
        Returns normalized feature importances as a dictionary mapping feature name to float score.
        """
        return dict(self._raw_feature_importances)

    def save(self, filepath: Union[str, Path]) -> None:
        """
        Serializes and saves the model artifact to disk.
        """
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, path)

    @classmethod
    def load(cls, filepath: Union[str, Path]) -> "HorseRacingModel":
        """
        Loads a serialized HorseRacingModel instance from disk.
        """
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"Model file not found at: {path}")
        model = joblib.load(path)
        if not isinstance(model, cls):
            raise TypeError(f"Loaded object is of type {type(model)}, expected {cls}")
        return model
