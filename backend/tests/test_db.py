import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime

from app.models.schema import (
    Base,
    Race,
    RaceEntry,
    Payout,
    Prediction,
    SimulatedBet,
    WalletSession,
)
from app.schemas.pydantic_models import (
    RaceSchema,
    RaceDetailSchema,
    RaceEntrySchema,
    PayoutSchema,
    PredictionSchema,
    SimulatedBetSchema,
    WalletSessionSchema,
)
from app.core.config import Settings
from app.core.database import get_db, init_db, SessionLocal, engine


@pytest.fixture
def db_session():
    test_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=test_engine)
    Session = sessionmaker(bind=test_engine)
    session = Session()
    yield session
    session.close()


def test_create_race_and_entry(db_session):
    race = Race(
        id="202405010101",
        date="2024-05-01",
        race_course="東京",
        race_number=11,
        race_name="日本ダービー",
        distance=2400,
        surface="芝",
        track_condition="良",
        weather="晴",
        status="scheduled",
    )
    db_session.add(race)
    db_session.commit()

    entry = RaceEntry(
        race_id="202405010101",
        horse_id="h001",
        horse_name="ドウデュース",
        post_position=3,
        horse_number=5,
        jockey_name="武豊",
        trainer_name="友道康夫",
        sex="牡",
        age=3,
        handicap_weight=57.0,
        horse_weight=504,
        horse_weight_diff=0,
        odds=3.5,
        popularity=1,
    )
    db_session.add(entry)
    db_session.commit()

    saved_race = db_session.query(Race).filter_by(id="202405010101").first()
    assert saved_race is not None
    assert len(saved_race.entries) == 1
    assert saved_race.entries[0].horse_name == "ドウデュース"
    assert saved_race.entries[0].race.race_name == "日本ダービー"


def test_payout_and_prediction(db_session):
    race = Race(
        id="202405010102",
        date="2024-05-01",
        race_course="京都",
        race_number=12,
        race_name="天皇賞（春）",
        distance=3200,
        surface="芝",
        track_condition="良",
        weather="晴",
        status="finished",
    )
    db_session.add(race)
    db_session.commit()

    payout = Payout(
        race_id="202405010102",
        bet_type="tansho",
        combination="5",
        payout=350,
    )
    prediction = Prediction(
        race_id="202405010102",
        horse_number=5,
        model_version="v1.0.0",
        win_prob=0.35,
        place_prob=0.65,
        expected_value=1.225,
        recommendation_mark="◎",
    )
    db_session.add_all([payout, prediction])
    db_session.commit()

    saved_race = db_session.query(Race).filter_by(id="202405010102").first()
    assert len(saved_race.payouts) == 1
    assert saved_race.payouts[0].payout == 350
    assert len(saved_race.predictions) == 1
    assert saved_race.predictions[0].recommendation_mark == "◎"


def test_wallet_session_and_simulated_bet(db_session):
    wallet = WalletSession(
        session_id="forward_live",
        initial_points=100000,
        current_points=99000,
        total_invested=1000,
        total_returned=0,
        total_bets=1,
        won_bets=0,
        max_drawdown=1000.0,
    )
    db_session.add(wallet)
    db_session.commit()

    race = Race(
        id="202405010103",
        date="2024-05-01",
        race_course="阪神",
        race_number=10,
        race_name="宝塚記念",
        distance=2200,
        surface="芝",
        track_condition="良",
        weather="晴",
        status="scheduled",
    )
    db_session.add(race)
    db_session.commit()

    bet = SimulatedBet(
        session_id="forward_live",
        race_id="202405010103",
        bet_type="tansho",
        combination="3",
        bet_points=1000,
        odds_at_bet=4.2,
        expected_value_at_bet=1.35,
        status="pending",
        payout_points=0,
        profit=0,
    )
    db_session.add(bet)
    db_session.commit()

    saved_wallet = db_session.query(WalletSession).filter_by(session_id="forward_live").first()
    assert saved_wallet is not None
    assert len(saved_wallet.bets) == 1
    assert saved_wallet.bets[0].bet_points == 1000
    assert saved_wallet.bets[0].race.race_name == "宝塚記念"


def test_pydantic_schema_validation(db_session):
    race = Race(
        id="202405010104",
        date="2024-05-01",
        race_course="東京",
        race_number=11,
        race_name="ジャパンカップ",
        distance=2400,
        surface="芝",
        track_condition="良",
        weather="晴",
        status="scheduled",
    )
    db_session.add(race)
    db_session.commit()

    entry = RaceEntry(
        race_id="202405010104",
        horse_id="h002",
        horse_name="イクイノックス",
        post_position=1,
        horse_number=1,
        jockey_name="ルメール",
        trainer_name="木村哲也",
        sex="牡",
        age=4,
        handicap_weight=58.0,
        horse_weight=498,
        horse_weight_diff=2,
        odds=1.3,
        popularity=1,
    )
    db_session.add(entry)
    db_session.commit()

    saved_race = db_session.query(Race).filter_by(id="202405010104").first()
    schema = RaceDetailSchema.model_validate(saved_race)
    assert schema.id == "202405010104"
    assert schema.race_name == "ジャパンカップ"
    assert len(schema.entries) == 1
    assert schema.entries[0].horse_name == "イクイノックス"


def test_config_and_database_get_db():
    settings = Settings()
    assert settings.DATABASE_URL.startswith("sqlite")
    assert settings.DEFAULT_WALLET_INITIAL_POINTS == 100000

    db_gen = get_db()
    db = next(db_gen)
    assert db is not None
    db.close()


def test_init_db():
    test_engine = create_engine("sqlite:///:memory:")
    init_db(bind_engine=test_engine)

    Session = sessionmaker(bind=test_engine)
    session = Session()
    wallet = session.query(WalletSession).filter_by(session_id="forward_live").first()
    assert wallet is not None
    assert wallet.initial_points == 100000
    assert wallet.current_points == 100000

    # Test idempotence
    init_db(bind_engine=test_engine)
    count = session.query(WalletSession).filter_by(session_id="forward_live").count()
    assert count == 1
    session.close()

