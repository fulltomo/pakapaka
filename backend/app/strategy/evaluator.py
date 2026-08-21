"""
Backtesting Simulation and Performance Evaluation Engine.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Union
from sqlalchemy.orm import Session

from app.models.schema import Race, RaceEntry, Payout, Prediction
from app.ml.model import HorseRacingModel
from app.ml.predictor import Predictor
from app.strategy.strategies import (
    BaseStrategy,
    BaseBetSizer,
    BetCandidate,
    get_strategy,
    get_bet_sizer,
)


@dataclass
class BacktestConfig:
    """
    Configuration parameters for historical backtesting.
    """
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    race_courses: Optional[List[str]] = None
    min_ev: float = 1.15
    min_prob: float = 0.0
    bet_strategy: Union[str, BaseStrategy] = "tansho_ev"
    bet_sizer: Union[str, BaseBetSizer] = "flat"
    bet_amount: int = 1000
    initial_points: int = 100000
    max_bets_per_race: Optional[int] = 2


@dataclass
class BacktestResult:
    """
    Detailed results and performance metrics from backtest execution.
    """
    total_races: int
    total_bets: int
    won_bets: int
    hit_rate: float  # Percentage (0.0 .. 100.0)
    total_invested: int
    total_returned: int
    profit: int
    roi: float  # Percentage (e.g. 105.4 %)
    profit_factor: float
    max_drawdown: float  # Maximum peak-to-trough percentage (e.g. 15.2 %)
    equity_curve: List[Dict[str, Any]] = field(default_factory=list)
    bets: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_races": self.total_races,
            "total_bets": self.total_bets,
            "won_bets": self.won_bets,
            "hit_rate": self.hit_rate,
            "total_invested": self.total_invested,
            "total_returned": self.total_returned,
            "profit": self.profit,
            "roi": self.roi,
            "profit_factor": self.profit_factor,
            "max_drawdown": self.max_drawdown,
            "equity_curve": self.equity_curve,
            "bets_count": len(self.bets),
        }


class BacktestEngine:
    """
    Executes chronological simulation of betting strategies over historical race data,
    calculating returns, drawdowns, hit rates, and equity progression.
    """

    def __init__(
        self,
        model: Optional[HorseRacingModel] = None,
        predictor: Optional[Predictor] = None,
    ):
        self.model = model
        self.predictor = predictor or (Predictor(model) if model else None)

    def run(
        self,
        db: Session,
        config: Optional[BacktestConfig] = None,
        min_ev: Optional[float] = None,
        min_prob: Optional[float] = None,
        bet_amount: Optional[int] = None,
        **kwargs,
    ) -> BacktestResult:
        """
        Runs backtesting against historical finished races in the database.
        """
        # Resolve config
        cfg = config or BacktestConfig()
        if min_ev is not None:
            cfg.min_ev = min_ev
        if min_prob is not None:
            cfg.min_prob = min_prob
        if bet_amount is not None:
            cfg.bet_amount = bet_amount

        # Strategy and sizer
        strategy = get_strategy(
            cfg.bet_strategy,
            min_ev=cfg.min_ev,
            min_prob=cfg.min_prob,
            max_bets=cfg.max_bets_per_race,
        )
        bet_sizer = get_bet_sizer(cfg.bet_sizer, bet_amount=cfg.bet_amount)

        # Query finished races
        query = db.query(Race).filter(Race.status == "finished")
        if cfg.start_date:
            query = query.filter(Race.date >= cfg.start_date)
        if cfg.end_date:
            query = query.filter(Race.date <= cfg.end_date)
        if cfg.race_courses:
            query = query.filter(Race.race_course.in_(cfg.race_courses))

        races = query.order_by(Race.date.asc(), Race.id.asc()).all()

        current_points = cfg.initial_points
        peak_points = cfg.initial_points
        max_drawdown = 0.0
        total_invested = 0
        total_returned = 0
        won_bets = 0
        total_bets = 0
        gross_profit = 0
        gross_loss = 0
        equity_curve: List[Dict[str, Any]] = []
        bets_log: List[Dict[str, Any]] = []

        for race in races:
            # Generate predictions if predictor is available, else use pre-computed predictions
            if self.predictor is not None:
                predictions = self.predictor.predict_race(race)
            elif race.predictions:
                predictions = race.predictions
            else:
                continue

            candidates = strategy.generate_candidates(race.id, predictions)

            for cand in candidates:
                bet_pts = bet_sizer.calculate_bet_amount(cand, current_points=current_points)
                if bet_pts <= 0:
                    continue

                current_points -= bet_pts
                total_invested += bet_pts
                total_bets += 1

                # Determine outcome from Payout or finish position
                won = False
                payout_points = 0

                payout_match = next(
                    (p for p in race.payouts if p.bet_type == cand.bet_type and p.combination == cand.combination),
                    None,
                )

                if payout_match is not None:
                    won = True
                    payout_points = int(bet_pts * (payout_match.payout / 100.0))
                else:
                    # Fallback to entry result if payouts table is empty
                    entry = next((e for e in race.entries if e.horse_number == cand.horse_number), None)
                    if entry and entry.finish_position is not None:
                        if cand.bet_type == "tansho" and entry.finish_position == 1:
                            won = True
                            payout_points = int(bet_pts * cand.odds)
                        elif cand.bet_type == "fukusho":
                            threshold = 3 if len(race.entries) >= 8 else 2
                            if entry.finish_position <= threshold:
                                won = True
                                payout_points = int(bet_pts * cand.odds)

                if won:
                    won_bets += 1
                    total_returned += payout_points
                    current_points += payout_points
                    profit = payout_points - bet_pts
                    if profit > 0:
                        gross_profit += profit
                else:
                    profit = -bet_pts
                    gross_loss += bet_pts

                # Update drawdown
                if current_points > peak_points:
                    peak_points = current_points
                dd = ((peak_points - current_points) / peak_points * 100.0) if peak_points > 0 else 0.0
                if dd > max_drawdown:
                    max_drawdown = dd

                bets_log.append({
                    "race_id": race.id,
                    "race_name": race.race_name,
                    "date": race.date,
                    "horse_number": cand.horse_number,
                    "horse_name": cand.horse_name,
                    "bet_type": cand.bet_type,
                    "combination": cand.combination,
                    "bet_points": bet_pts,
                    "odds": cand.odds,
                    "expected_value": cand.expected_value,
                    "won": won,
                    "payout_points": payout_points,
                    "profit": profit,
                    "balance_after": current_points,
                })

            equity_curve.append({
                "date": race.date,
                "race_id": race.id,
                "points": current_points,
                "profit": current_points - cfg.initial_points,
                "roi": round((total_returned / total_invested * 100.0), 2) if total_invested > 0 else 100.0,
            })

        # Calculate summary metrics
        hit_rate = round((won_bets / total_bets * 100.0), 2) if total_bets > 0 else 0.0
        roi = round((total_returned / total_invested * 100.0), 2) if total_invested > 0 else 0.0
        net_profit = total_returned - total_invested

        if gross_loss > 0:
            profit_factor = round(gross_profit / gross_loss, 2)
        elif gross_profit > 0:
            profit_factor = 999.0
        else:
            profit_factor = 0.0

        return BacktestResult(
            total_races=len(races),
            total_bets=total_bets,
            won_bets=won_bets,
            hit_rate=hit_rate,
            total_invested=total_invested,
            total_returned=total_returned,
            profit=net_profit,
            roi=roi,
            profit_factor=profit_factor,
            max_drawdown=round(max_drawdown, 2),
            equity_curve=equity_curve,
            bets=bets_log,
        )

    def run_backtest(self, db: Session, config: BacktestConfig) -> BacktestResult:
        """Alias matching plan specification."""
        return self.run(db=db, config=config)
