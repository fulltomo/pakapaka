"""
Comprehensive Tests for FastAPI REST API endpoints and server integration.
"""

from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.database import get_db, Base, init_db
from app.models.schema import Race, RaceEntry, Payout, WalletSession
from app.api.models import set_active_model
from main import app


# Test database setup (in-memory SQLite)
TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="module", autouse=True)
def setup_test_db(tmp_path_factory):
    model_dir = tmp_path_factory.mktemp("models")
    settings.MODEL_DIR = str(model_dir)

    app.dependency_overrides[get_db] = override_get_db
    init_db(bind_engine=test_engine)
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client():
    return TestClient(app)


def test_root_and_health_check(client):
    """Test root and health check endpoints."""
    res_root = client.get("/")
    assert res_root.status_code == 200
    assert "docs_url" in res_root.json()

    res_h1 = client.get("/api/health")
    assert res_h1.status_code == 200
    assert res_h1.json()["status"] == "ok"

    res_h2 = client.get("/health")
    assert res_h2.status_code == 200
    assert res_h2.json()["status"] == "ok"


def test_sample_generation_and_races_list(client):
    """Test sample data generation and race listing with filters."""
    # Generate 15 finished races and 5 scheduled races
    gen_res = client.post("/api/races/sample?count=15&scheduled_count=5")
    assert gen_res.status_code == 200
    gen_data = gen_res.json()
    assert gen_data["status"] == "ok"
    assert gen_data["generated_races"] == 20

    # Also test brief endpoint compatibility: /api/data/generate-sample
    gen_res2 = client.post("/api/data/generate-sample?count=5")
    assert gen_res2.status_code == 200
    assert gen_res2.json()["generated_races"] == 5

    # List races
    races_res = client.get("/api/races")
    assert races_res.status_code == 200
    races = races_res.json()
    assert len(races) >= 25

    # List scheduled races filter
    sched_res = client.get("/api/races?status=scheduled")
    assert sched_res.status_code == 200
    sched_races = sched_res.json()
    assert len(sched_races) >= 5
    for r in sched_races:
        assert r["status"] == "scheduled"

    # List with date and course filter
    first_race = races[0]
    filtered_res = client.get(f"/api/races?date={first_race['date']}&race_course={first_race['race_course']}")
    assert filtered_res.status_code == 200
    filtered_races = filtered_res.json()
    assert len(filtered_races) >= 1
    for r in filtered_races:
        assert r["date"] == first_race["date"]
        assert r["race_course"] == first_race["race_course"]

    # Get race detail
    sample_race_id = first_race["id"]
    detail_res = client.get(f"/api/races/{sample_race_id}")
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["id"] == sample_race_id
    assert len(detail["entries"]) >= 8

    # 404 for non-existent race
    not_found_res = client.get("/api/races/non_existent_id_999")
    assert not_found_res.status_code == 404


def test_model_training_and_active_model_api(client):
    """Test ML model training and active model metadata retrieval."""
    # Active model before training
    set_active_model(None, None)
    active_before = client.get("/api/models/active")
    assert active_before.status_code == 200
    assert active_before.json()["status"] == "not_trained"

    # Train model
    train_res = client.post(
        "/api/models/train",
        json={"model_type": "lightgbm", "test_size": 0.2, "random_state": 42},
    )
    assert train_res.status_code == 200
    train_data = train_res.json()
    assert train_data["status"] == "ok"
    assert "model_version" in train_data
    assert "roc_auc" in train_data
    assert train_data["trained_samples"] > 0
    assert len(train_data["feature_importance"]) > 0

    # Active model after training
    active_after = client.get("/api/models/active")
    assert active_after.status_code == 200
    active_data = active_after.json()
    assert active_data["status"] == "active"
    assert active_data["model_version"] == train_data["model_version"]
    assert "feature_importance" in active_data


def test_predictions_api(client):
    """Test prediction generation and persistence for a race."""
    # Fetch a scheduled race
    sched_res = client.get("/api/races?status=scheduled")
    assert sched_res.status_code == 200
    sched_races = sched_res.json()
    assert len(sched_races) > 0
    target_race_id = sched_races[0]["id"]

    # Generate predictions
    pred_res = client.get(f"/api/predictions/{target_race_id}")
    assert pred_res.status_code == 200
    preds = pred_res.json()
    assert len(preds) >= 8

    # Check structure
    for p in preds:
        assert "horse_number" in p
        assert "win_prob" in p
        assert "place_prob" in p
        assert "expected_value" in p
        assert "recommendation_mark" in p

    # Verify recommendations marks include ◎, ◯, ▲
    marks = [p["recommendation_mark"] for p in preds]
    assert "◎" in marks
    assert "◯" in marks

    # Check race detail now includes predictions
    detail_res = client.get(f"/api/races/{target_race_id}")
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert len(detail["predictions"]) == len(preds)

    # 404 for non-existent race prediction
    not_found_res = client.get("/api/predictions/non_existent_id")
    assert not_found_res.status_code == 404


def test_backtest_api(client):
    """Test backtesting execution via REST API."""
    backtest_req = {
        "min_ev": 1.0,
        "bet_type": "tansho",
        "bet_amount": 1000,
        "use_kelly": False,
    }
    res = client.post("/api/backtest/run", json=backtest_req)
    assert res.status_code == 200
    result = res.json()

    assert "total_bets" in result
    assert "win_rate" in result
    assert "roi" in result
    assert "profit" in result
    assert "equity_curve" in result
    assert "bets" in result

    # Test Kelly criterion and fukusho strategy
    kelly_req = {
        "min_ev": 0.8,
        "bet_type": "fukusho",
        "bet_amount": 1000,
        "use_kelly": True,
        "kelly_fraction": 0.25,
    }
    res_k = client.post("/api/backtest/run", json=kelly_req)
    assert res_k.status_code == 200
    assert "total_bets" in res_k.json()


def test_simulation_wallet_auto_bet_and_settle(client):
    """Test paper trading simulation: wallet, auto-betting, settlement, and bets history."""
    # 1. Check wallet
    wallet_res = client.get("/api/simulation/wallet")
    assert wallet_res.status_code == 200
    wallet = wallet_res.json()
    assert wallet["session_id"] == "forward_live"
    assert wallet["current_points"] == 100000

    # 2. Reset wallet
    reset_res = client.post("/api/simulation/wallet/reset", json={"initial_points": 50000})
    assert reset_res.status_code == 200
    reset_wallet = reset_res.json()
    assert reset_wallet["current_points"] == 50000
    assert reset_wallet["total_invested"] == 0

    # 3. Auto-bet on scheduled races
    auto_bet_res = client.post(
        "/api/simulation/auto-bet",
        json={
            "session_id": "forward_live",
            "min_ev": 0.5,  # Low threshold to ensure bets are placed
            "bet_amount": 1000,
        },
    )
    assert auto_bet_res.status_code == 200
    auto_bet_data = auto_bet_res.json()
    assert auto_bet_data["session_id"] == "forward_live"
    assert auto_bet_data["placed_bets_count"] > 0
    assert auto_bet_data["remaining_points"] < 50000

    # 4. Check bets endpoint
    bets_res = client.get("/api/simulation/bets?status=pending")
    assert bets_res.status_code == 200
    bets = bets_res.json()
    assert len(bets) == auto_bet_data["placed_bets_count"]
    for b in bets:
        assert b["status"] == "pending"
        assert b["bet_points"] == 1000
        assert b["race_name"] is not None

    # 5. Settle pending bets on scheduled races (0 settled because scheduled status)
    settle_res = client.post("/api/simulation/settle?session_id=forward_live")
    assert settle_res.status_code == 200

    # 6. Manually change one race status to finished with payouts to test settlement outcome
    db = TestingSessionLocal()
    try:
        first_bet = bets[0]
        race = db.query(Race).filter(Race.id == first_bet["race_id"]).first()
        race.status = "finished"
        # Add winning payout
        payout = Payout(
            race_id=race.id,
            bet_type=first_bet["bet_type"],
            combination=first_bet["combination"],
            payout=350,
        )
        db.add(payout)
        db.commit()
    finally:
        db.close()

    # Settle again -> should settle 1 or more bets
    settle_res2 = client.post("/api/simulation/settle?session_id=forward_live")
    assert settle_res2.status_code == 200
    settle_data = settle_res2.json()
    assert settle_data["settled_bets_count"] >= 1

    # 7. Check updated wallet state
    updated_wallet = client.get("/api/simulation/wallet").json()
    assert updated_wallet["won_bets"] >= 1
    assert updated_wallet["total_returned"] > 0


def test_scrape_api_error_handling(client):
    """Test race scrape API failure handling."""
    with patch("app.data.scraper.NetkeibaScraper.scrape_race_and_save", return_value=None):
        res = client.post("/api/races/scrape?race_id=9999999999")
        assert res.status_code == 400
        assert "Could not scrape" in res.json()["detail"]
