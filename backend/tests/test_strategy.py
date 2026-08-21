import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.schema import Base, Race, RaceEntry, Payout, Prediction, SimulatedBet, WalletSession
from app.data.sample_generator import SampleDataGenerator
from app.ml.model import HorseRacingModel
from app.ml.trainer import ModelTrainer
from app.ml.predictor import Predictor, PredictionResult
from app.strategy.strategies import (
    BetCandidate,
    TanshoEVStrategy,
    FukushoEVStrategy,
    FlatBetSizer,
    KellyBetSizer,
    get_strategy,
    get_bet_sizer,
)
from app.strategy.evaluator import (
    BacktestConfig,
    BacktestResult,
    BacktestEngine,
)
from app.strategy.simulator import ForwardSimulator


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_bet_candidate_dataclass():
    cand = BetCandidate(
        race_id="202401010101",
        horse_number=3,
        bet_type="tansho",
        odds=4.5,
        win_prob=0.30,
        place_prob=0.60,
        expected_value=1.35,
        recommendation_mark="◎",
        horse_name="イクイノックス",
        combination="3",
    )
    assert cand.race_id == "202401010101"
    assert cand.horse_number == 3
    assert cand.expected_value == 1.35
    assert cand.combination == "3"
    cand_dict = cand.to_dict()
    assert cand_dict["race_id"] == "202401010101"
    assert cand_dict["bet_type"] == "tansho"


def test_tansho_ev_strategy():
    strategy = TanshoEVStrategy(min_ev=1.15, min_prob=0.05, max_bets_per_race=1)
    preds = [
        PredictionResult(horse_number=1, win_prob=0.40, place_prob=0.70, odds=2.0, expected_value=0.80, recommendation_mark="◎"),
        PredictionResult(horse_number=2, win_prob=0.25, place_prob=0.50, odds=5.0, expected_value=1.25, recommendation_mark="◯"),
        PredictionResult(horse_number=3, win_prob=0.02, place_prob=0.10, odds=70.0, expected_value=1.40, recommendation_mark="☆"),
    ]
    candidates = strategy.generate_candidates(race_id="r1", predictions=preds)
    # Horse #2 has EV=1.25 >= 1.15 and prob=0.25 >= 0.05 -> Candidate
    # Horse #3 has EV=1.40 >= 1.15 but prob=0.02 < 0.05 -> Filtered out
    # Horse #1 has EV=0.80 < 1.15 -> Filtered out
    assert len(candidates) == 1
    assert candidates[0].horse_number == 2
    assert candidates[0].bet_type == "tansho"
    assert candidates[0].expected_value == 1.25


def test_fukusho_ev_strategy():
    strategy = FukushoEVStrategy(min_ev=1.10, min_prob=0.30, max_bets_per_race=2)
    preds = [
        PredictionResult(horse_number=1, win_prob=0.30, place_prob=0.65, odds=3.0, expected_value=0.90, recommendation_mark="◎"),
        PredictionResult(horse_number=2, win_prob=0.10, place_prob=0.40, odds=10.0, expected_value=1.00, recommendation_mark="◯"),
        PredictionResult(horse_number=3, win_prob=0.05, place_prob=0.20, odds=20.0, expected_value=1.00, recommendation_mark="▲"),
    ]
    candidates = strategy.generate_candidates(race_id="r1", predictions=preds)
    # Fukusho EV approx: place_prob * place_odds
    # For horse #1: place_prob=0.65, place_odds ~ max(1.1, 3.0 * 0.35 = 1.05 -> 1.1) => EV = 0.65 * 1.1 = 0.715
    # For horse #2: place_prob=0.40, place_odds ~ max(1.1, 10.0 * 0.35 = 3.5) => EV = 0.40 * 3.5 = 1.40 >= 1.10, prob=0.40 >= 0.30
    assert len(candidates) == 1
    assert candidates[0].horse_number == 2
    assert candidates[0].bet_type == "fukusho"


def test_bet_sizers():
    flat_sizer = FlatBetSizer(bet_amount=1000)
    cand = BetCandidate(
        race_id="r1",
        horse_number=1,
        bet_type="tansho",
        odds=4.0,
        win_prob=0.35,
        expected_value=1.40,
    )
    # Flat sizer
    assert flat_sizer.calculate_bet_amount(cand, current_points=50000) == 1000
    assert flat_sizer.calculate_bet_amount(cand, current_points=500) == 500
    assert flat_sizer.calculate_bet_amount(cand, current_points=50) == 0

    # Kelly sizer: f* = fraction * (p * odds - 1) / (odds - 1)
    # fraction = 0.25, p = 0.35, odds = 4.0 => (0.35 * 4 - 1)/(4 - 1) = 0.4 / 3 = 0.13333
    # f* = 0.25 * 0.13333 = 0.03333
    # current_points = 100,000 => 3,333 -> rounded to nearest 100 = 3300
    kelly_sizer = KellyBetSizer(fraction=0.25, min_bet=100, max_bet=10000)
    bet = kelly_sizer.calculate_bet_amount(cand, current_points=100000)
    assert 3000 <= bet <= 3500
    assert bet % 100 == 0

    # Max bet limit
    huge_kelly = KellyBetSizer(fraction=1.0, min_bet=100, max_bet=5000)
    assert huge_kelly.calculate_bet_amount(cand, current_points=1000000) == 5000

    # Negative edge should give 0 bet
    bad_cand = BetCandidate(
        race_id="r1",
        horse_number=2,
        bet_type="tansho",
        odds=2.0,
        win_prob=0.40,
        expected_value=0.80,
    )
    assert kelly_sizer.calculate_bet_amount(bad_cand, current_points=100000) == 0

    # Factory helpers
    assert isinstance(get_strategy("tansho"), TanshoEVStrategy)
    assert isinstance(get_strategy("fukusho"), FukushoEVStrategy)
    assert isinstance(get_bet_sizer("flat"), FlatBetSizer)
    assert isinstance(get_bet_sizer("kelly"), KellyBetSizer)


def test_backtest_engine_run(db_session):
    generator = SampleDataGenerator(seed=42)
    generator.generate_races(db_session, count=25, scheduled_count=0)

    trainer = ModelTrainer()
    model, _ = trainer.train(db_session, save_model=False)

    backtester = BacktestEngine(model=model)
    config = BacktestConfig(
        min_ev=1.10,
        min_prob=0.05,
        bet_amount=1000,
        initial_points=100000,
    )
    result = backtester.run_backtest(db_session, config=config)

    assert isinstance(result, BacktestResult)
    assert result.total_races == 25
    assert result.total_bets >= 0
    assert result.total_invested == result.total_bets * 1000
    assert result.profit == result.total_returned - result.total_invested
    if result.total_invested > 0:
        assert result.roi == round((result.total_returned / result.total_invested) * 100.0, 2)
        assert 0.0 <= result.hit_rate <= 100.0
    assert result.max_drawdown >= 0.0
    assert len(result.equity_curve) > 0
    result_dict = result.to_dict()
    assert result_dict["total_races"] == 25


def test_backtest_engine_no_matching_races(db_session):
    backtester = BacktestEngine()
    config = BacktestConfig(start_date="2099-01-01")
    result = backtester.run(db_session, config=config)
    assert result.total_races == 0
    assert result.total_bets == 0
    assert result.roi == 0.0


def test_forward_simulator_lifecycle(db_session):
    generator = SampleDataGenerator(seed=123)
    # Generate 15 finished races and 5 scheduled races
    generator.generate_races(db_session, count=15, scheduled_count=5)

    trainer = ModelTrainer()
    model, _ = trainer.train(db_session, save_model=False)

    simulator = ForwardSimulator(model=model)
    wallet = simulator.get_or_create_wallet(db_session, session_id="test_live", initial_points=100000)
    assert wallet.current_points == 100000
    assert wallet.total_bets == 0

    # Place bets on scheduled races
    placed_bets = simulator.auto_bet_scheduled_races(
        db_session,
        session_id="test_live",
        min_ev=1.05,
        bet_amount=1000,
        max_bets_per_race=2,
    )
    assert len(placed_bets) > 0
    for bet in placed_bets:
        assert bet.status == "pending"
        assert bet.session_id == "test_live"
        assert bet.bet_points == 1000

    db_session.refresh(wallet)
    expected_invested = len(placed_bets) * 1000
    assert wallet.total_invested == expected_invested
    assert wallet.current_points == 100000 - expected_invested
    assert wallet.total_bets == len(placed_bets)

    # Calling auto_bet_scheduled_races again should not double-bet
    second_placed = simulator.auto_bet_scheduled_races(
        db_session,
        session_id="test_live",
        min_ev=1.05,
    )
    assert len(second_placed) == 0

    # Now simulate finishing the scheduled races
    scheduled_races = db_session.query(Race).filter(Race.status == "scheduled").all()
    for race in scheduled_races:
        race.status = "finished"
        # Simulate finish positions
        entry_odds = [e.odds for e in race.entries]
        order = generator._simulate_finish_order(entry_odds)
        ordered_entries = []
        for pos, idx in enumerate(order, start=1):
            e = race.entries[idx]
            e.finish_position = pos
            ordered_entries.append(e)
        payouts = generator._calculate_payouts(race.id, race.entries, ordered_entries)
        race.payouts.extend(payouts)

    db_session.commit()

    # Settle all finished races
    settled_bets = simulator.settle_all_finished_races(db_session, session_id="test_live")
    assert len(settled_bets) == len(placed_bets)

    db_session.refresh(wallet)
    for bet in settled_bets:
        assert bet.status in ("won", "lost")
        if bet.status == "won":
            assert bet.payout_points > 0
            assert bet.profit == bet.payout_points - bet.bet_points
        else:
            assert bet.payout_points == 0
            assert bet.profit == -bet.bet_points

    assert wallet.total_returned == sum(b.payout_points for b in settled_bets)
    assert wallet.current_points == 100000 - wallet.total_invested + wallet.total_returned
    assert wallet.won_bets == sum(1 for b in settled_bets if b.status == "won")

    # Settling again should return empty list
    settled_again = simulator.settle_all_finished_races(db_session, session_id="test_live")
    assert len(settled_again) == 0

    # Daily betting summary
    summary = simulator.run_daily_betting(db_session, session_id="test_live")
    assert summary["session_id"] == "test_live"
    assert summary["current_points"] == wallet.current_points
