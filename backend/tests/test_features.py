import numpy as np
import pandas as pd
import pytest

from app.ml.features import FeatureExtractor
from app.data.sample_generator import SampleDataGenerator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.schema import Base, RaceEntry, Race


@pytest.fixture
def sample_race_df():
    data = [
        {
            "race_id": "202405010101",
            "horse_id": "h1001",
            "horse_name": "イクイノックス",
            "post_position": 1,
            "horse_number": 1,
            "handicap_weight": 58.0,
            "horse_weight": 500,
            "horse_weight_diff": 2,
            "sex": "牡",
            "age": 4,
            "distance": 2000,
            "surface": "芝",
            "track_condition": "良",
            "odds": 1.5,
            "popularity": 1,
            "jockey_name": "ルメール",
            "trainer_name": "木村哲也",
            "finish_position": 1,
            "finish_time": "1:58.2",
            "margin": "",
        },
        {
            "race_id": "202405010101",
            "horse_id": "h1002",
            "horse_name": "リバティアイランド",
            "post_position": 2,
            "horse_number": 2,
            "handicap_weight": 55.0,
            "horse_weight": 468,
            "horse_weight_diff": -4,
            "sex": "牝",
            "age": 3,
            "distance": 2000,
            "surface": "芝",
            "track_condition": "良",
            "odds": 3.2,
            "popularity": 2,
            "jockey_name": "川田将雅",
            "trainer_name": "中内田充",
            "finish_position": 2,
            "finish_time": "1:58.5",
            "margin": "1 3/4",
        },
        {
            "race_id": "202405010101",
            "horse_id": "h1003",
            "horse_name": "テストセンバ",
            "post_position": 3,
            "horse_number": 3,
            "handicap_weight": 57.0,
            "horse_weight": 480,
            "horse_weight_diff": 0,
            "sex": "セ",
            "age": 5,
            "distance": 2000,
            "surface": "芝",
            "track_condition": "良",
            "odds": 15.0,
            "popularity": 4,
            "jockey_name": "一般騎手",
            "trainer_name": "一般調教師",
            "finish_position": 3,
            "finish_time": "1:59.0",
            "margin": "3",
        },
        {
            "race_id": "202405010101",
            "horse_id": "h1004",
            "horse_name": "アナザーホース",
            "post_position": 4,
            "horse_number": 4,
            "handicap_weight": 56.0,
            "horse_weight": 490,
            "horse_weight_diff": 4,
            "sex": "牡",
            "age": 6,
            "distance": 2000,
            "surface": "芝",
            "track_condition": "良",
            "odds": 45.0,
            "popularity": 8,
            "jockey_name": "一般騎手2",
            "trainer_name": "一般調教師2",
            "finish_position": 4,
            "finish_time": "1:59.5",
            "margin": "2 1/2",
        },
    ]
    return pd.DataFrame(data)


def test_feature_extraction_basic():
    """Step 1 & Brief specification basic test."""
    data = [
        {
            "race_id": "r1", "horse_id": "h1", "post_position": 1, "horse_number": 1,
            "handicap_weight": 57.0, "horse_weight": 500, "horse_weight_diff": 2,
            "sex": "牡", "age": 4, "distance": 2000, "surface": "芝", "track_condition": "良",
            "odds": 3.0, "popularity": 1, "jockey_name": "ルメール", "trainer_name": "矢作芳人",
            "finish_position": 1
        },
        {
            "race_id": "r1", "horse_id": "h2", "post_position": 2, "horse_number": 2,
            "handicap_weight": 55.0, "horse_weight": 480, "horse_weight_diff": -4,
            "sex": "牝", "age": 3, "distance": 2000, "surface": "芝", "track_condition": "良",
            "odds": 12.0, "popularity": 5, "jockey_name": "川田将雅", "trainer_name": "中内田充",
            "finish_position": 4
        }
    ]
    df = pd.DataFrame(data)
    extractor = FeatureExtractor()
    features_df, feature_cols = extractor.extract_features(df, is_training=True)

    assert "weight_ratio" in feature_cols
    assert "sex_code" in feature_cols
    assert "is_top_jockey" in feature_cols
    assert "is_top_trainer" in feature_cols
    assert "finish_position" not in feature_cols  # Leak prevention
    assert len(features_df) == 2


def test_categorical_encodings(sample_race_df):
    """Test sex, surface, and track_condition numerical mappings."""
    extractor = FeatureExtractor()
    features_df, feature_cols = extractor.extract_features(sample_race_df, is_training=False)

    # sex_code: 牡=0, 牝=1, セ=2
    assert features_df.loc[0, "sex_code"] == 0
    assert features_df.loc[1, "sex_code"] == 1
    assert features_df.loc[2, "sex_code"] == 2

    # surface_code: 芝=0, ダート=1
    assert features_df.loc[0, "surface_code"] == 0

    # track_condition_code: 良=0
    assert features_df.loc[0, "track_condition_code"] == 0

    # horse_age
    assert features_df.loc[0, "horse_age"] == 4
    assert features_df.loc[1, "horse_age"] == 3


def test_top_jockey_and_trainer(sample_race_df):
    """Test top jockey and trainer binary flags."""
    extractor = FeatureExtractor()
    features_df, feature_cols = extractor.extract_features(sample_race_df, is_training=False)

    # ルメール & 川田将雅 should be 1, 一般騎手 should be 0
    assert features_df.loc[0, "is_top_jockey"] == 1
    assert features_df.loc[1, "is_top_jockey"] == 1
    assert features_df.loc[2, "is_top_jockey"] == 0

    # 木村哲也 & 中内田充 should be 1, 一般調教師 should be 0
    assert features_df.loc[0, "is_top_trainer"] == 1
    assert features_df.loc[1, "is_top_trainer"] == 1
    assert features_df.loc[2, "is_top_trainer"] == 0


def test_weight_ratio_calculation(sample_race_df):
    """Test weight_ratio = handicap_weight / horse_weight."""
    extractor = FeatureExtractor()
    features_df, _ = extractor.extract_features(sample_race_df, is_training=False)

    expected_ratio = 58.0 / 500.0
    assert np.isclose(features_df.loc[0, "weight_ratio"], expected_ratio)


def test_odds_features(sample_race_df):
    """Test odds, log_odds, and popularity."""
    extractor = FeatureExtractor()
    features_df, feature_cols = extractor.extract_features(sample_race_df, is_training=False)

    assert "odds" in feature_cols
    assert "log_odds" in feature_cols
    assert "popularity" in feature_cols

    assert np.isclose(features_df.loc[0, "log_odds"], np.log(1.5))
    assert np.isclose(features_df.loc[1, "log_odds"], np.log(3.2))


def test_training_target_generation(sample_race_df):
    """Test target_win and target_place creation during training mode."""
    extractor = FeatureExtractor()
    features_df, feature_cols = extractor.extract_features(sample_race_df, is_training=True)

    assert "target_win" in features_df.columns
    assert "target_place" in features_df.columns

    # Check labels
    # Horse 1: finish_position 1 -> win=1, place=1
    assert features_df.loc[0, "target_win"] == 1
    assert features_df.loc[0, "target_place"] == 1

    # Horse 2: finish_position 2 -> win=0, place=1
    assert features_df.loc[1, "target_win"] == 0
    assert features_df.loc[1, "target_place"] == 1

    # Horse 3: finish_position 3 -> win=0, place=1
    assert features_df.loc[2, "target_win"] == 0
    assert features_df.loc[2, "target_place"] == 1

    # Horse 4: finish_position 4 -> win=0, place=0
    assert features_df.loc[3, "target_win"] == 0
    assert features_df.loc[3, "target_place"] == 0


def test_strict_leak_prevention(sample_race_df):
    """Ensure no post-race or target column is present in feature_cols."""
    extractor = FeatureExtractor()
    features_df, feature_cols = extractor.extract_features(sample_race_df, is_training=True)

    forbidden_cols = {
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
    }

    leaked = set(feature_cols).intersection(forbidden_cols)
    assert len(leaked) == 0, f"Data leakage detected in feature_cols: {leaked}"

    # Verify all feature columns in feature_cols exist in features_df and are numeric
    for col in feature_cols:
        assert col in features_df.columns
        assert pd.api.types.is_numeric_dtype(features_df[col]), f"Non-numeric column in feature_cols: {col}"


def test_missing_values_and_edge_cases():
    """Test robustness with missing or zero weights, missing popularity, etc."""
    df_missing = pd.DataFrame([
        {
            "race_id": "r99",
            "horse_id": "h99",
            "post_position": None,
            "horse_number": 5,
            "handicap_weight": 54.0,
            "horse_weight": 0,  # 0 weight edge case
            "horse_weight_diff": None,
            "sex": "未知",
            "age": None,
            "distance": 1800,
            "surface": "ダート",
            "track_condition": "不良",
            "odds": None,
            "popularity": None,
            "jockey_name": None,
            "trainer_name": None,
        }
    ])

    extractor = FeatureExtractor()
    features_df, feature_cols = extractor.extract_features(df_missing, is_training=False)

    assert len(features_df) == 1
    # Check weight ratio doesn't fail with division by zero or inf
    assert not np.isinf(features_df.loc[0, "weight_ratio"])
    assert not np.isnan(features_df.loc[0, "weight_ratio"])
    # Check sex code fallback
    assert features_df.loc[0, "sex_code"] == 0
    # Check surface code
    assert features_df.loc[0, "surface_code"] == 1
    # Check track condition code (不良 = 3)
    assert features_df.loc[0, "track_condition_code"] == 3


def test_integration_with_sample_generator_and_db():
    """Test feature extraction on real objects produced by SampleDataGenerator."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    generator = SampleDataGenerator(seed=42)
    generator.generate_races(db=db, count=5, scheduled_count=2)

    # Query all race entries joined with race
    query = (
        db.query(RaceEntry, Race)
        .join(Race, RaceEntry.race_id == Race.id)
        .all()
    )

    records = []
    for entry, race in query:
        records.append({
            "race_id": entry.race_id,
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
            "finish_position": entry.finish_position,
            "finish_time": entry.finish_time,
            "margin": entry.margin,
        })

    df = pd.DataFrame(records)
    assert len(df) > 0

    extractor = FeatureExtractor()
    features_df, feature_cols = extractor.extract_features(df, is_training=True)

    assert len(features_df) == len(df)
    assert "target_win" in features_df.columns
    assert "target_place" in features_df.columns
    assert "finish_position" not in feature_cols
    assert "finish_time" not in feature_cols
    assert "margin" not in feature_cols

    # Ensure no NaN in feature columns
    for col in feature_cols:
        assert not features_df[col].isna().any(), f"NaN found in feature column {col}"
