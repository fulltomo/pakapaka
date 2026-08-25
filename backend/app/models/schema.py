from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Index
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Race(Base):
    __tablename__ = "races"

    id = Column(String(32), primary_key=True, index=True)  # e.g., "202405010101"
    date = Column(String(16), nullable=False, index=True)  # "YYYY-MM-DD"
    race_course = Column(String(16), nullable=False, index=True)  # "東京", "中山", etc.
    race_number = Column(Integer, nullable=False)  # 1..12
    race_name = Column(String(64), nullable=False)
    distance = Column(Integer, nullable=False)  # in meters
    surface = Column(String(8), nullable=False)  # "芝", "ダート"
    track_condition = Column(String(8), nullable=False, default="良")  # "良", "稍重", "重", "不良"
    weather = Column(String(8), nullable=False, default="晴")  # "晴", "曇", "雨", "小雨"
    status = Column(String(16), nullable=False, default="scheduled", index=True)  # "scheduled", "finished", "cancelled"
    race_class = Column(String(32), nullable=True)      # "新馬", "未勝利", "1勝クラス", "オープン", "G1" ...
    race_condition = Column(String(32), nullable=True)  # "[指](定量)" — 出走条件と重量規定
    post_time = Column(String(8), nullable=True)        # 発走時刻 "17:50"
    lap_times = Column(String(256), nullable=True)      # 200mごとのラップ "12.2-10.9-11.1"
    pace = Column(String(64), nullable=True)            # 前半/後半3F "34.2-35.1"
    parser_version = Column(Integer, nullable=True)     # which scraper build wrote this row

    # Relationships
    entries = relationship(
        "RaceEntry",
        back_populates="race",
        cascade="all, delete-orphan",
        order_by="RaceEntry.horse_number",
    )
    payouts = relationship(
        "Payout",
        back_populates="race",
        cascade="all, delete-orphan",
    )
    predictions = relationship(
        "Prediction",
        back_populates="race",
        cascade="all, delete-orphan",
        order_by="Prediction.horse_number",
    )
    bets = relationship(
        "SimulatedBet",
        back_populates="race",
        cascade="all, delete-orphan",
    )


class RaceEntry(Base):
    __tablename__ = "race_entries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    race_id = Column(String(32), ForeignKey("races.id", ondelete="CASCADE"), nullable=False, index=True)
    horse_id = Column(String(32), nullable=False, index=True)
    horse_name = Column(String(64), nullable=False)
    post_position = Column(Integer, nullable=False)  # 枠番 (1..8)
    horse_number = Column(Integer, nullable=False)  # 馬番 (1..18)
    jockey_name = Column(String(32), nullable=False)
    trainer_name = Column(String(32), nullable=False)
    sex = Column(String(4), nullable=False)  # "牡", "牝", "セ"
    age = Column(Integer, nullable=False)
    handicap_weight = Column(Float, nullable=False)  # 斤量 (e.g., 57.0)
    horse_weight = Column(Integer, nullable=True, default=0)  # 馬体重 (e.g., 500)
    horse_weight_diff = Column(Integer, nullable=True, default=0)  # 増減 (e.g., +2, -4)
    odds = Column(Float, nullable=False, default=1.0)  # 単勝オッズ
    popularity = Column(Integer, nullable=True)  # 人気順 (1..18)
    finish_position = Column(Integer, nullable=True)  # 着順 (1..18)
    finish_time = Column(String(16), nullable=True)  # 走破タイム (e.g., "2:24.5")
    margin = Column(String(16), nullable=True)  # 着差 (e.g., "クビ", "1 1/2")
    final_600m = Column(Float, nullable=True)          # 上がり3ハロン (e.g., 33.4)
    corner_positions = Column(String(32), nullable=True)  # 通過順位 "4-5-5-3"
    prize_money = Column(Float, nullable=True)         # 獲得賞金 (万円)
    owner_name = Column(String(64), nullable=True)     # 馬主

    # Relationships
    race = relationship("Race", back_populates="entries")

    __table_args__ = (
        Index("idx_race_horse_num", "race_id", "horse_number"),
    )


class Payout(Base):
    __tablename__ = "payouts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    race_id = Column(String(32), ForeignKey("races.id", ondelete="CASCADE"), nullable=False, index=True)
    bet_type = Column(String(16), nullable=False)  # "tansho", "fukusho", "umaren", "wide", "sanrenpuku", "sanrentan"
    combination = Column(String(32), nullable=False)  # e.g., "5", "3-5", "1-3-5"
    payout = Column(Integer, nullable=False)  # 100円あたりの払戻金 (e.g., 350)

    # Relationships
    race = relationship("Race", back_populates="payouts")


class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    race_id = Column(String(32), ForeignKey("races.id", ondelete="CASCADE"), nullable=False, index=True)
    horse_number = Column(Integer, nullable=False)
    model_version = Column(String(32), nullable=True)
    win_prob = Column(Float, nullable=False)  # 0.0 .. 1.0
    place_prob = Column(Float, nullable=False)  # 0.0 .. 1.0
    expected_value = Column(Float, nullable=False)  # win_prob * odds
    recommendation_mark = Column(String(8), nullable=False, default="-")  # "◎", "◯", "▲", "☆", "-"
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    race = relationship("Race", back_populates="predictions")

    __table_args__ = (
        Index("idx_pred_race_horse", "race_id", "horse_number"),
    )


class SimulatedBet(Base):
    __tablename__ = "simulated_bets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(32), ForeignKey("wallet_sessions.session_id", ondelete="CASCADE"), nullable=False, index=True)
    race_id = Column(String(32), ForeignKey("races.id", ondelete="CASCADE"), nullable=False, index=True)
    bet_type = Column(String(16), nullable=False)  # "tansho", "fukusho", "wide", etc.
    combination = Column(String(32), nullable=False)  # e.g., "5", "3-5"
    bet_points = Column(Integer, nullable=False)  # 賭けたポイント
    odds_at_bet = Column(Float, nullable=False)  # 投票時のオッズ
    expected_value_at_bet = Column(Float, nullable=False)  # 投票時の期待値
    status = Column(String(16), nullable=False, default="pending", index=True)  # "pending", "won", "lost", "refunded"
    payout_points = Column(Integer, nullable=False, default=0)  # 的中時の払戻ポイント
    profit = Column(Integer, nullable=False, default=0)  # 純損益 (payout_points - bet_points)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    race = relationship("Race", back_populates="bets")
    wallet_session = relationship("WalletSession", back_populates="bets")


class WalletSession(Base):
    __tablename__ = "wallet_sessions"

    session_id = Column(String(32), primary_key=True, index=True)  # e.g., "forward_live", "backtest_20240501"
    initial_points = Column(Integer, nullable=False, default=100000)
    current_points = Column(Integer, nullable=False, default=100000)
    total_invested = Column(Integer, nullable=False, default=0)
    total_returned = Column(Integer, nullable=False, default=0)
    total_bets = Column(Integer, nullable=False, default=0)
    won_bets = Column(Integer, nullable=False, default=0)
    max_drawdown = Column(Float, nullable=False, default=0.0)

    # Relationships
    bets = relationship(
        "SimulatedBet",
        back_populates="wallet_session",
        cascade="all, delete-orphan",
        order_by="SimulatedBet.created_at.desc()",
    )


class Horse(Base):
    """Per-horse profile from db.netkeiba.com/horse/{id}. One row per horse, scraped once."""

    __tablename__ = "horses"

    horse_id = Column(String(32), primary_key=True, index=True)
    horse_name = Column(String(64), nullable=True)
    birth_date = Column(String(16), nullable=True)      # "2023-02-28"
    sire = Column(String(64), nullable=True, index=True)          # 父
    sire_sire = Column(String(64), nullable=True)                 # 父父 (サイアーライン)
    dam = Column(String(64), nullable=True)                       # 母
    broodmare_sire = Column(String(64), nullable=True, index=True) # 母父
    breeder = Column(String(64), nullable=True, index=True)        # 生産者
    origin = Column(String(32), nullable=True)                     # 産地
    auction_price = Column(Float, nullable=True)       # セリ取引価格 (万円). None when not sold at auction.
    trainer_name = Column(String(32), nullable=True)
    stable = Column(String(8), nullable=True)          # "栗東" / "美浦"
    owner_name = Column(String(64), nullable=True)
    scraped_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
