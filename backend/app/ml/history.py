"""
As-of rolling history features.

Every column here is computed from rows strictly BEFORE the row it belongs to.
The current race never contributes to its own features, so these are safe to use
as model inputs. `add_history_features` is the single implementation used by both
training and inference — the caller only has to supply the prior rows.
"""

from typing import List, Tuple
import numpy as np
import pandas as pd

# Rolling windows. Bounded so inference only has to load a slice of history.
JOCKEY_WINDOW = 500
TRAINER_WINDOW = 300
MIN_RIDES = 20  # below this a rate is too noisy to be worth a number; stays NaN

HISTORY_FEATURES: List[str] = [
    "horse_starts",
    "horse_win_rate",
    "horse_place_rate",
    "horse_last_finish",
    "horse_avg_finish3",
    "horse_avg_odds3",
    "horse_days_since_last",
    "jockey_win_rate",
    "jockey_place_rate",
    "trainer_win_rate",
]


def _prior_mean(df: pd.DataFrame, key: str, col: str, window: int, min_periods: int) -> pd.Series:
    """Mean of `col` over the previous `window` rows of each `key` group."""
    prior = df.groupby(key, sort=False)[col].shift(1)
    return (
        prior.groupby(df[key], sort=False)
        .rolling(window, min_periods=min_periods)
        .mean()
        .reset_index(level=0, drop=True)
    )


def _expanding_rate(df: pd.DataFrame, key: str, flag: str) -> pd.Series:
    """Share of prior rows in the group where `flag` is 1. NaN on the first row."""
    prior_sum = df.groupby(key, sort=False)[flag].cumsum() - df[flag]
    prior_n = df.groupby(key, sort=False).cumcount()
    return prior_sum / prior_n.replace(0, np.nan)


def add_history_features(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
    """
    Appends `HISTORY_FEATURES` to `df`.

    `df` must hold the full history the caller wants considered, one row per
    (race, horse). Rows whose `finish_position` is NaN (an upcoming race) get
    features from their history but contribute nothing to anyone else's.
    Horses/jockeys with no usable history keep NaN, which LightGBM splits on natively.
    """
    df = df.sort_values(["race_date", "race_id"], kind="mergesort").copy()

    finish = pd.to_numeric(df["finish_position"], errors="coerce")
    df["_won"] = (finish == 1).astype(float)
    df["_placed"] = (finish <= 3).astype(float)
    df["_finish"] = finish
    df["_odds"] = pd.to_numeric(df.get("odds"), errors="coerce")

    # --- horse ---
    df["horse_starts"] = df.groupby("horse_id", sort=False).cumcount()
    df["horse_win_rate"] = _expanding_rate(df, "horse_id", "_won")
    df["horse_place_rate"] = _expanding_rate(df, "horse_id", "_placed")
    df["horse_last_finish"] = df.groupby("horse_id", sort=False)["_finish"].shift(1)
    df["horse_avg_finish3"] = _prior_mean(df, "horse_id", "_finish", 3, 1)
    df["horse_avg_odds3"] = _prior_mean(df, "horse_id", "_odds", 3, 1)

    dates = pd.to_datetime(df["race_date"], errors="coerce")
    prev_date = dates.groupby(df["horse_id"], sort=False).shift(1)
    df["horse_days_since_last"] = (dates - prev_date).dt.days

    # --- jockey & trainer: recent form, not career average ---
    df["jockey_win_rate"] = _prior_mean(df, "jockey_name", "_won", JOCKEY_WINDOW, MIN_RIDES)
    df["jockey_place_rate"] = _prior_mean(df, "jockey_name", "_placed", JOCKEY_WINDOW, MIN_RIDES)
    df["trainer_win_rate"] = _prior_mean(df, "trainer_name", "_won", TRAINER_WINDOW, MIN_RIDES)

    return df.drop(columns=["_won", "_placed", "_finish", "_odds"]), list(HISTORY_FEATURES)
