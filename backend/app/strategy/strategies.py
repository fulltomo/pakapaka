"""
Betting Strategies, Candidate Generation, and Bankroll Sizing Engines.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Dict, Any, Union

from app.ml.predictor import PredictionResult
from app.models.schema import Prediction, Race


@dataclass
class BetCandidate:
    """
    Candidate ticket to be placed for a race.
    """
    race_id: str
    horse_number: int
    bet_type: str  # "tansho", "fukusho", "umaren", "wide", etc.
    odds: float
    win_prob: float = 0.0
    place_prob: float = 0.0
    expected_value: float = 0.0
    recommendation_mark: str = "-"
    horse_name: Optional[str] = None
    combination: Optional[str] = None

    def __post_init__(self):
        if self.combination is None:
            self.combination = str(self.horse_number)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "race_id": self.race_id,
            "horse_number": self.horse_number,
            "horse_name": self.horse_name,
            "bet_type": self.bet_type,
            "combination": self.combination,
            "odds": self.odds,
            "win_prob": self.win_prob,
            "place_prob": self.place_prob,
            "expected_value": self.expected_value,
            "recommendation_mark": self.recommendation_mark,
        }


def _normalize_prediction(pred: Union[PredictionResult, Prediction, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Helper to extract fields uniformly from PredictionResult, Prediction model, or Dict.
    """
    if isinstance(pred, PredictionResult):
        return {
            "horse_number": pred.horse_number,
            "horse_name": pred.horse_name,
            "odds": pred.odds,
            "win_prob": pred.win_prob,
            "place_prob": pred.place_prob,
            "expected_value": pred.expected_value,
            "recommendation_mark": pred.recommendation_mark,
        }
    elif isinstance(pred, Prediction):
        # Odds might be accessible if entry is loaded or approximate
        return {
            "horse_number": pred.horse_number,
            "horse_name": getattr(pred, "horse_name", None),
            "odds": (pred.expected_value / pred.win_prob) if pred.win_prob > 0 else 1.0,
            "win_prob": pred.win_prob,
            "place_prob": pred.place_prob,
            "expected_value": pred.expected_value,
            "recommendation_mark": pred.recommendation_mark,
        }
    elif isinstance(pred, dict):
        return pred
    else:
        return {
            "horse_number": getattr(pred, "horse_number", 1),
            "horse_name": getattr(pred, "horse_name", None),
            "odds": getattr(pred, "odds", 1.0),
            "win_prob": getattr(pred, "win_prob", 0.0),
            "place_prob": getattr(pred, "place_prob", 0.0),
            "expected_value": getattr(pred, "expected_value", 0.0),
            "recommendation_mark": getattr(pred, "recommendation_mark", "-"),
        }


class BaseStrategy(ABC):
    """
    Abstract Base Class for horse racing betting strategies.
    """
    name: str = "base"

    @abstractmethod
    def generate_candidates(
        self,
        race_id: str,
        predictions: Union[List[PredictionResult], List[Prediction], List[Dict[str, Any]]],
        **kwargs,
    ) -> List[BetCandidate]:
        """
        Filters and ranks predictions into betting candidates.
        """
        pass


class TanshoEVStrategy(BaseStrategy):
    """
    Win (単勝) Expected Value Strategy.
    Selects horses where win expected value (win_prob * odds) >= min_ev and win_prob >= min_prob.
    """
    name: str = "tansho_ev"

    def __init__(
        self,
        min_ev: float = 1.15,
        min_prob: float = 0.0,
        max_bets_per_race: Optional[int] = None,
    ):
        self.min_ev = min_ev
        self.min_prob = min_prob
        self.max_bets_per_race = max_bets_per_race

    def generate_candidates(
        self,
        race_id: str,
        predictions: Union[List[PredictionResult], List[Prediction], List[Dict[str, Any]]],
        **kwargs,
    ) -> List[BetCandidate]:
        candidates = []
        for raw_p in predictions:
            p = _normalize_prediction(raw_p)
            win_prob = float(p.get("win_prob", 0.0))
            odds = float(p.get("odds", 1.0))
            ev = float(p.get("expected_value", win_prob * odds))

            if ev >= self.min_ev and win_prob >= self.min_prob:
                candidates.append(
                    BetCandidate(
                        race_id=race_id,
                        horse_number=int(p["horse_number"]),
                        bet_type="tansho",
                        odds=odds,
                        win_prob=win_prob,
                        place_prob=float(p.get("place_prob", 0.0)),
                        expected_value=ev,
                        recommendation_mark=p.get("recommendation_mark", "-"),
                        horse_name=p.get("horse_name"),
                        combination=str(p["horse_number"]),
                    )
                )

        # Sort by expected value descending
        candidates.sort(key=lambda c: c.expected_value, reverse=True)

        if self.max_bets_per_race is not None and self.max_bets_per_race > 0:
            candidates = candidates[: self.max_bets_per_race]

        return candidates


class FukushoEVStrategy(BaseStrategy):
    """
    Place (複勝) Expected Value Strategy.
    Estimates place odds and expected value, selecting candidates with place_ev >= min_ev and place_prob >= min_prob.
    """
    name: str = "fukusho_ev"

    def __init__(
        self,
        min_ev: float = 1.10,
        min_prob: float = 0.0,
        max_bets_per_race: Optional[int] = None,
    ):
        self.min_ev = min_ev
        self.min_prob = min_prob
        self.max_bets_per_race = max_bets_per_race

    def generate_candidates(
        self,
        race_id: str,
        predictions: Union[List[PredictionResult], List[Prediction], List[Dict[str, Any]]],
        **kwargs,
    ) -> List[BetCandidate]:
        candidates = []
        for raw_p in predictions:
            p = _normalize_prediction(raw_p)
            place_prob = float(p.get("place_prob", 0.0))
            raw_odds = float(p.get("odds", 1.0))

            # Approximate place odds: max(1.1, raw_odds * 0.35)
            place_odds = round(max(1.1, raw_odds * 0.35), 2)
            place_ev = round(place_prob * place_odds, 4)

            if place_ev >= self.min_ev and place_prob >= self.min_prob:
                candidates.append(
                    BetCandidate(
                        race_id=race_id,
                        horse_number=int(p["horse_number"]),
                        bet_type="fukusho",
                        odds=place_odds,
                        win_prob=float(p.get("win_prob", 0.0)),
                        place_prob=place_prob,
                        expected_value=place_ev,
                        recommendation_mark=p.get("recommendation_mark", "-"),
                        horse_name=p.get("horse_name"),
                        combination=str(p["horse_number"]),
                    )
                )

        candidates.sort(key=lambda c: c.expected_value, reverse=True)

        if self.max_bets_per_race is not None and self.max_bets_per_race > 0:
            candidates = candidates[: self.max_bets_per_race]

        return candidates


class BaseBetSizer(ABC):
    """
    Abstract Base Class for money management / position sizing.
    """
    @abstractmethod
    def calculate_bet_amount(
        self,
        candidate: BetCandidate,
        current_points: int,
        **kwargs,
    ) -> int:
        """
        Calculates the number of points to wager on a candidate.
        """
        pass


class FlatBetSizer(BaseBetSizer):
    """
    Fixed / Flat bet sizing (e.g., fixed 1,000 points per ticket).
    """
    def __init__(self, bet_amount: int = 1000):
        self.bet_amount = max(100, (bet_amount // 100) * 100)

    def calculate_bet_amount(
        self,
        candidate: BetCandidate,
        current_points: int,
        **kwargs,
    ) -> int:
        if current_points < 100:
            return 0
        amount = min(self.bet_amount, current_points)
        return (amount // 100) * 100


class KellyBetSizer(BaseBetSizer):
    """
    Fractional Kelly Criterion Bet Sizer.
    Formula: f* = fraction * (p * odds - 1) / (odds - 1) * current_points
    Bounded within [min_bet, max_bet] and rounded to 100 pt increments.
    """
    def __init__(
        self,
        fraction: float = 0.25,
        min_bet: int = 100,
        max_bet: int = 10000,
    ):
        self.fraction = fraction
        self.min_bet = max(100, (min_bet // 100) * 100)
        self.max_bet = max(self.min_bet, (max_bet // 100) * 100)

    def calculate_bet_amount(
        self,
        candidate: BetCandidate,
        current_points: int,
        **kwargs,
    ) -> int:
        if current_points < self.min_bet:
            return 0

        p = candidate.win_prob if candidate.bet_type == "tansho" else candidate.place_prob
        odds = candidate.odds

        if odds <= 1.0 or p <= 0.0:
            return 0

        ev = p * odds
        if ev <= 1.0:
            return 0

        f_star = (p * odds - 1.0) / (odds - 1.0)
        if f_star <= 0.0:
            return 0

        raw_bet = self.fraction * f_star * current_points
        bounded_bet = max(self.min_bet, min(self.max_bet, raw_bet))
        rounded_bet = (int(bounded_bet) // 100) * 100

        if rounded_bet > current_points:
            rounded_bet = (current_points // 100) * 100

        if rounded_bet < self.min_bet:
            return 0

        return rounded_bet


def get_strategy(
    strategy_or_name: Union[str, BaseStrategy],
    min_ev: float = 1.15,
    min_prob: float = 0.0,
    max_bets: Optional[int] = None,
) -> BaseStrategy:
    """
    Factory function for obtaining strategy instance.
    """
    if isinstance(strategy_or_name, BaseStrategy):
        return strategy_or_name

    name = (strategy_or_name or "tansho_ev").lower()
    if name in ("tansho", "tansho_ev"):
        return TanshoEVStrategy(min_ev=min_ev, min_prob=min_prob, max_bets_per_race=max_bets)
    elif name in ("fukusho", "fukusho_ev"):
        return FukushoEVStrategy(min_ev=min_ev, min_prob=min_prob, max_bets_per_race=max_bets)
    else:
        return TanshoEVStrategy(min_ev=min_ev, min_prob=min_prob, max_bets_per_race=max_bets)


def get_bet_sizer(
    sizer_or_name: Union[str, BaseBetSizer],
    bet_amount: int = 1000,
    kelly_fraction: float = 0.25,
) -> BaseBetSizer:
    """
    Factory function for obtaining bet sizer instance.
    """
    if isinstance(sizer_or_name, BaseBetSizer):
        return sizer_or_name

    name = (sizer_or_name or "flat").lower()
    if name in ("kelly", "fractional_kelly"):
        return KellyBetSizer(fraction=kelly_fraction)
    else:
        return FlatBetSizer(bet_amount=bet_amount)
