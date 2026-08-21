import os
import tempfile
import numpy as np
import pandas as pd
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.schema import Base, Race, RaceEntry, Prediction
from app.data.sample_generator import SampleDataGenerator
from app.ml.model import HorseRacingModel
from app.ml.trainer import ModelTrainer
from app.ml.predictor import Predictor, PredictionResult
from app.ml.features import FeatureExtractor


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_model_training_and_prediction(db_session):
    """Brief specification step 1 test: train model and predict on target race."""
    generator = SampleDataGenerator(seed=42)
    generator.generate_races(db_session, count=30)

    trainer = ModelTrainer(random_state=42)
    model, metrics = trainer.train(db_session)

    assert model is not None
    assert "roc_auc" in metrics
    assert "feature_importance" in metrics
    assert isinstance(metrics["feature_importance"], dict)
    assert len(metrics["feature_importance"]) > 0

    # 推論テスト
    predictor = Predictor(model)
    target_race = db_session.query(Race).first()
    predictions = predictor.predict_race(target_race)

    assert len(predictions) == len(target_race.entries)
    for p in predictions:
        assert 0.0 <= p.win_prob <= 1.0
        assert 0.0 <= p.place_prob <= 1.0
        assert p.expected_value > 0
        assert p.recommendation_mark in ["◎", "◯", "▲", "☆", "-"]


def test_horse_racing_model_direct():
    """Test HorseRacingModel direct fitting, prediction, and probability properties."""
    np.random.seed(42)
    n_samples = 200
    n_features = 5
    feature_names = [f"feat_{i}" for i in range(n_features)]

    X = pd.DataFrame(np.random.randn(n_samples, n_features), columns=feature_names)
    # Synthetic target: signal on feat_0
    y_win = (X["feat_0"] + np.random.randn(n_samples) * 0.5 > 1.0).astype(int)
    y_place = (X["feat_0"] + np.random.randn(n_samples) * 0.5 > 0.0).astype(int)

    model = HorseRacingModel(model_version="test_v1", calibration_method="sigmoid", random_state=42)
    model.fit(X, y_win, y_place, feature_names=feature_names)

    assert model.is_fitted
    assert model.model_version == "test_v1"
    assert model.feature_names == feature_names

    win_probs = model.predict_win_proba(X)
    place_probs = model.predict_place_proba(X)

    assert len(win_probs) == n_samples
    assert len(place_probs) == n_samples
    assert np.all((win_probs >= 0.0) & (win_probs <= 1.0))
    assert np.all((place_probs >= 0.0) & (place_probs <= 1.0))

    # Check feature importances
    importances = model.get_feature_importances()
    assert isinstance(importances, dict)
    assert set(importances.keys()) == set(feature_names)
    assert all(isinstance(v, float) for v in importances.values())


def test_model_save_and_load():
    """Test model persistence: saving to disk and loading back."""
    np.random.seed(42)
    X = pd.DataFrame({
        "feat_a": np.random.randn(100),
        "feat_b": np.random.randn(100),
    })
    y_win = (X["feat_a"] > 0.5).astype(int)
    y_place = (X["feat_a"] > -0.2).astype(int)

    model = HorseRacingModel(model_version="persist_v1", random_state=42)
    model.fit(X, y_win, y_place, feature_names=["feat_a", "feat_b"])

    orig_win_probs = model.predict_win_proba(X)
    orig_place_probs = model.predict_place_proba(X)

    with tempfile.TemporaryDirectory() as tmpdir:
        save_path = os.path.join(tmpdir, "test_model.joblib")
        model.save(save_path)
        assert os.path.exists(save_path)

        loaded_model = HorseRacingModel.load(save_path)
        assert loaded_model.is_fitted
        assert loaded_model.model_version == "persist_v1"
        assert loaded_model.feature_names == ["feat_a", "feat_b"]

        loaded_win_probs = loaded_model.predict_win_proba(X)
        loaded_place_probs = loaded_model.predict_place_proba(X)

        np.testing.assert_allclose(orig_win_probs, loaded_win_probs, rtol=1e-5)
        np.testing.assert_allclose(orig_place_probs, loaded_place_probs, rtol=1e-5)


def test_trainer_evaluation_metrics(db_session):
    """Test ModelTrainer metrics calculation (ROC-AUC, LogLoss, Brier score)."""
    generator = SampleDataGenerator(seed=123)
    generator.generate_races(db_session, count=25)

    trainer = ModelTrainer(test_size=0.2, random_state=42)
    model, metrics = trainer.train(db_session)

    assert "roc_auc" in metrics
    assert "log_loss" in metrics
    assert "brier_score" in metrics
    assert "place_roc_auc" in metrics
    assert "place_log_loss" in metrics
    assert "place_brier_score" in metrics
    assert "train_samples" in metrics
    assert "test_samples" in metrics
    assert metrics["train_samples"] > 0
    assert metrics["test_samples"] > 0
    assert 0.0 <= metrics["roc_auc"] <= 1.0
    assert metrics["log_loss"] >= 0.0
    assert 0.0 <= metrics["brier_score"] <= 1.0


def test_trainer_empty_db_raises_error(db_session):
    """Test trainer raises ValueError if no finished races exist."""
    trainer = ModelTrainer()
    with pytest.raises(ValueError, match="No finished races"):
        trainer.train(db_session)


def test_predictor_race_normalization_and_ev(db_session):
    """Test Predictor win probability normalization across runners and EV calculation."""
    generator = SampleDataGenerator(seed=777)
    generator.generate_races(db_session, count=20)

    trainer = ModelTrainer(random_state=42)
    model, _ = trainer.train(db_session)

    predictor = Predictor(model)
    target_race = db_session.query(Race).first()
    predictions = predictor.predict_race(target_race)

    # 1. Total win probability for all horses in a race should sum close to 1.0
    total_win_prob = sum(p.win_prob for p in predictions)
    assert np.isclose(total_win_prob, 1.0, atol=1e-2)

    # 2. EV must equal win_prob * odds for each runner
    for p, entry in zip(predictions, target_race.entries):
        assert p.horse_number == entry.horse_number
        assert np.isclose(p.expected_value, round(p.win_prob * entry.odds, 4), atol=1e-4)

    # 3. Marks should include ◎ and ◯ for top contenders
    marks = [p.recommendation_mark for p in predictions]
    assert "◎" in marks
    assert "◯" in marks


def test_predictor_save_predictions_to_db(db_session):
    """Test Predictor.save_predictions stores Prediction records in DB."""
    generator = SampleDataGenerator(seed=888)
    generator.generate_races(db_session, count=15)

    trainer = ModelTrainer(random_state=42)
    model, _ = trainer.train(db_session)

    predictor = Predictor(model)
    target_race = db_session.query(Race).first()
    predictions = predictor.predict_race(target_race)

    saved_preds = predictor.save_predictions(db_session, target_race, predictions)
    assert len(saved_preds) == len(target_race.entries)

    # Verify query from DB
    db_preds = db_session.query(Prediction).filter_by(race_id=target_race.id).all()
    assert len(db_preds) == len(target_race.entries)
    for p in db_preds:
        assert p.race_id == target_race.id
        assert 0.0 <= p.win_prob <= 1.0
        assert p.expected_value > 0

    # Overwrite / update test: running save_predictions again replaces existing
    predictor.save_predictions(db_session, target_race, predictions)
    db_preds_after = db_session.query(Prediction).filter_by(race_id=target_race.id).all()
    assert len(db_preds_after) == len(target_race.entries)


def test_predictor_empty_race_entries():
    """Test Predictor handles race with empty entries gracefully."""
    model = HorseRacingModel()
    predictor = Predictor(model)
    dummy_race = Race(
        id="empty_race",
        date="2024-05-01",
        race_course="東京",
        race_number=1,
        race_name="テストレース",
        distance=1800,
        surface="芝",
        entries=[]
    )
    predictions = predictor.predict_race(dummy_race)
    assert predictions == []
