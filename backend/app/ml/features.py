"""
Feature engineering pipeline with strict leak-prevention design for horse racing predictions.
"""

from typing import List, Tuple, Set
import numpy as np
import pandas as pd

from app.ml.history import HISTORY_FEATURES


SEX_MAP = {"牡": 0, "牝": 1, "セ": 2}
SURFACE_MAP = {"芝": 0, "ダート": 1, "障害": 2, "障": 2}
TRACK_CONDITION_MAP = {"良": 0, "稍重": 1, "重": 2, "不良": 3}

# Columns that MUST NEVER be present in feature_cols (post-race outcome leak prevention)
FORBIDDEN_FEATURE_COLS: Set[str] = {
    "finish_position",
    "finish_time",
    "margin",
    "payout",
    "target_win",
    "target_place",
    "race_id",
    "horse_id",
    "horse_name",
    "jockey_name",
    "trainer_name",
    "sex",
    "surface",
    "track_condition",
    "weather",
    "status",
    "id",
    "created_at",
}


class FeatureExtractor:
    """
    Extracts and transforms tabular horse racing features from raw entry & race data.
    Guarantees strict isolation of post-race outcome labels from feature vectors.
    """

    def extract_features(
        self,
        df_entries: pd.DataFrame,
        is_training: bool = False,
    ) -> Tuple[pd.DataFrame, List[str]]:
        """
        Extract numerical features and optional training targets from race entry DataFrame.

        Parameters
        ----------
        df_entries : pd.DataFrame
            DataFrame containing race entry and race condition columns.
        is_training : bool, default False
            If True, generates `target_win` and `target_place` columns in output DataFrame
            when `finish_position` is present in the input.

        Returns
        -------
        features_df : pd.DataFrame
            DataFrame with all transformed features, metadata, and optional targets.
        feature_cols : list of str
            List of column names to be fed to the ML model (excluding targets and leaks).
        """
        if df_entries.empty:
            return pd.DataFrame(), []

        df = df_entries.copy()

        # 1. Horse physical metrics & ratios
        handicap = pd.to_numeric(df.get("handicap_weight", 55.0), errors="coerce").fillna(55.0)
        horse_wt = pd.to_numeric(df.get("horse_weight", 480.0), errors="coerce").fillna(480.0)
        # Avoid division by zero or negative weights
        safe_horse_wt = horse_wt.apply(lambda w: float(w) if float(w) > 200.0 else 480.0)

        df["weight_ratio"] = (handicap / safe_horse_wt).astype(float)
        df["horse_weight"] = safe_horse_wt.astype(float)
        df["horse_weight_diff"] = pd.to_numeric(df.get("horse_weight_diff", 0.0), errors="coerce").fillna(0.0).astype(float)

        # 2. Categorical Encodings
        # Sex
        sex_raw = df.get("sex", "牡").fillna("牡").astype(str)
        df["sex_code"] = sex_raw.map(lambda s: SEX_MAP.get(s, 0)).astype(int)

        # Age
        age_col = "age" if "age" in df.columns else ("horse_age" if "horse_age" in df.columns else None)
        if age_col is not None:
            df["horse_age"] = pd.to_numeric(df[age_col], errors="coerce").fillna(4).astype(int)
        else:
            df["horse_age"] = 4

        # Post position and Horse number
        df["post_position"] = pd.to_numeric(df.get("post_position", 1), errors="coerce").fillna(1).astype(int)
        df["horse_number"] = pd.to_numeric(df.get("horse_number", 1), errors="coerce").fillna(1).astype(int)

        # Distance
        df["distance"] = pd.to_numeric(df.get("distance", 1800), errors="coerce").fillna(1800).astype(int)

        # Surface
        surface_raw = df.get("surface", "芝").fillna("芝").astype(str)
        df["surface_code"] = surface_raw.map(lambda s: SURFACE_MAP.get(s, 0)).astype(int)

        # Track condition
        track_cond_raw = df.get("track_condition", "良").fillna("良").astype(str)
        df["track_condition_code"] = track_cond_raw.map(lambda tc: TRACK_CONDITION_MAP.get(tc, 0)).astype(int)

        # 4. Market Odds & Popularity Features
        raw_odds = pd.to_numeric(df.get("odds", 10.0), errors="coerce").fillna(10.0)
        safe_odds = raw_odds.apply(lambda x: float(x) if float(x) >= 1.0 else 1.0)
        df["odds"] = safe_odds.astype(float)
        df["log_odds"] = np.log(safe_odds).astype(float)

        pop_col = pd.to_numeric(df.get("popularity", 1), errors="coerce").fillna(1).astype(int)
        df["popularity"] = pop_col

        # Define candidate feature columns in canonical order
        feature_cols = [
            "weight_ratio",
            "horse_weight",
            "horse_weight_diff",
            "sex_code",
            "horse_age",
            "post_position",
            "horse_number",
            "distance",
            "surface_code",
            "track_condition_code",
            "odds",
            "log_odds",
            "popularity",
        ]

        # As-of history features, when the caller has attached them (see app.ml.history).
        feature_cols += [c for c in HISTORY_FEATURES if c in df.columns]

        # 5. Target generation when training
        if is_training and "finish_position" in df.columns:
            finish_pos = pd.to_numeric(df["finish_position"], errors="coerce")
            df["target_win"] = (finish_pos == 1).astype(int)
            df["target_place"] = (finish_pos <= 3).astype(int)
        elif is_training:
            # When training is requested but finish_position is absent
            df["target_win"] = 0
            df["target_place"] = 0

        # Strict leak prevention verification
        leaked = set(feature_cols).intersection(FORBIDDEN_FEATURE_COLS)
        if leaked:
            raise ValueError(f"CRITICAL ERROR: Data leakage detected in feature columns: {leaked}")

        return df, feature_cols
