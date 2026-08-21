from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field, computed_field


# ==========================================
# Race & RaceEntry Schemas
# ==========================================

class RaceEntryBase(BaseModel):
    horse_id: str
    horse_name: str
    post_position: int
    horse_number: int
    jockey_name: str
    trainer_name: str
    sex: str
    age: int
    handicap_weight: float
    horse_weight: Optional[int] = 0
    horse_weight_diff: Optional[int] = 0
    odds: float = 1.0
    popularity: Optional[int] = None
    finish_position: Optional[int] = None
    finish_time: Optional[str] = None
    margin: Optional[str] = None


class RaceEntryCreate(RaceEntryBase):
    race_id: Optional[str] = None


class RaceEntrySchema(RaceEntryBase):
    id: int
    race_id: str

    model_config = ConfigDict(from_attributes=True)


class PayoutBase(BaseModel):
    bet_type: str
    combination: str
    payout: int


class PayoutCreate(PayoutBase):
    race_id: Optional[str] = None


class PayoutSchema(PayoutBase):
    id: int
    race_id: str

    model_config = ConfigDict(from_attributes=True)


class PredictionBase(BaseModel):
    horse_number: int
    model_version: Optional[str] = None
    win_prob: float
    place_prob: float
    expected_value: float
    recommendation_mark: str = "-"


class PredictionCreate(PredictionBase):
    race_id: Optional[str] = None


class PredictionSchema(PredictionBase):
    id: int
    race_id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RaceBase(BaseModel):
    id: str
    date: str
    race_course: str
    race_number: int
    race_name: str
    distance: int
    surface: str
    track_condition: str = "良"
    weather: str = "晴"
    status: str = "scheduled"


class RaceCreate(RaceBase):
    entries: Optional[List[RaceEntryCreate]] = None


class RaceSchema(RaceBase):
    model_config = ConfigDict(from_attributes=True)


class RaceDetailSchema(RaceBase):
    entries: List[RaceEntrySchema] = []
    payouts: List[PayoutSchema] = []
    predictions: List[PredictionSchema] = []

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# Simulation & Wallet Schemas
# ==========================================

class SimulatedBetBase(BaseModel):
    session_id: str
    race_id: str
    bet_type: str
    combination: str
    bet_points: int
    odds_at_bet: float
    expected_value_at_bet: float
    status: str = "pending"
    payout_points: int = 0
    profit: int = 0


class SimulatedBetCreate(SimulatedBetBase):
    pass


class SimulatedBetSchema(SimulatedBetBase):
    id: int
    created_at: datetime
    race_name: Optional[str] = None
    race_date: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class WalletSessionBase(BaseModel):
    session_id: str
    initial_points: int = 100000
    current_points: int = 100000
    total_invested: int = 0
    total_returned: int = 0
    total_bets: int = 0
    won_bets: int = 0
    max_drawdown: float = 0.0


class WalletSessionCreate(BaseModel):
    session_id: str
    initial_points: int = 100000


class WalletSessionSchema(WalletSessionBase):
    model_config = ConfigDict(from_attributes=True)

    @computed_field
    def roi(self) -> float:
        if self.total_invested <= 0:
            return 0.0
        return round((self.total_returned / self.total_invested) * 100, 2)

    @computed_field
    def win_rate(self) -> float:
        if self.total_bets <= 0:
            return 0.0
        return round((self.won_bets / self.total_bets) * 100, 2)

    @computed_field
    def profit(self) -> int:
        return self.total_returned - self.total_invested


# ==========================================
# Strategy & Backtest Schemas
# ==========================================

class BacktestRequest(BaseModel):
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    min_ev: float = 1.15
    bet_type: str = "tansho"
    bet_amount: int = 1000
    use_kelly: bool = False
    kelly_fraction: float = 0.25
    min_prob: float = 0.0


class EquityPoint(BaseModel):
    date: str
    race_id: str
    cumulative_profit: int
    balance: int
    drawdown: float


class BacktestResultSchema(BaseModel):
    total_bets: int
    won_bets: int
    win_rate: float
    total_invested: int
    total_returned: int
    profit: int
    roi: float
    max_drawdown: float
    profit_factor: float
    equity_curve: List[EquityPoint] = []
    bets: List[SimulatedBetSchema] = []


class AutoBetRequest(BaseModel):
    session_id: str = "forward_live"
    target_date: Optional[str] = None
    min_ev: float = 1.15
    bet_type: str = "tansho"
    bet_amount: int = 1000
    use_kelly: bool = False
    kelly_fraction: float = 0.25
    min_prob: float = 0.0


class AutoBetResultSchema(BaseModel):
    session_id: str
    placed_bets_count: int
    total_points_spent: int
    remaining_points: int
    placed_bets: List[SimulatedBetSchema] = []


# ==========================================
# ML Model & Sample Generator Schemas
# ==========================================

class ModelTrainRequest(BaseModel):
    model_type: str = "lightgbm"
    test_size: float = 0.2
    random_state: int = 42


class ModelTrainResponse(BaseModel):
    status: str
    model_version: str
    roc_auc: float
    log_loss: float
    feature_importance: Dict[str, float]
    trained_samples: int


class SampleDataGenerateRequest(BaseModel):
    count: int = 20


class SampleDataGenerateResponse(BaseModel):
    status: str
    generated_races: int
