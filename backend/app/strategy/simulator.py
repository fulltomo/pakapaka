"""
Forward Testing (Paper Trading) and Live Wallet Simulation Engine.
"""

from typing import List, Optional, Union
from sqlalchemy.orm import Session

from app.models.schema import Race, RaceEntry, Payout, SimulatedBet, WalletSession
from app.ml.model import HorseRacingModel
from app.ml.predictor import Predictor
from app.strategy.strategies import (
    BaseStrategy,
    BaseBetSizer,
    TanshoEVStrategy,
    FlatBetSizer,
    get_strategy,
    get_bet_sizer,
)


class ForwardSimulator:
    """
    Simulates live / forward paper trading with virtual wallets, automated ticket placing
    on scheduled races, and outcome settlement upon race completion.
    """

    def __init__(
        self,
        model: Optional[HorseRacingModel] = None,
        predictor: Optional[Predictor] = None,
    ):
        self.model = model
        self.predictor = predictor or (Predictor(model) if model else None)

    def get_or_create_wallet(
        self,
        session: Session,
        session_id: str = "forward_live",
        initial_points: int = 100000,
    ) -> WalletSession:
        """
        Retrieves an existing wallet session or creates and initializes a new one.
        """
        wallet = session.query(WalletSession).filter(WalletSession.session_id == session_id).first()
        if wallet is None:
            wallet = WalletSession(
                session_id=session_id,
                initial_points=initial_points,
                current_points=initial_points,
                total_invested=0,
                total_returned=0,
                total_bets=0,
                won_bets=0,
                max_drawdown=0.0,
            )
            session.add(wallet)
            session.commit()
            session.refresh(wallet)
        return wallet

    def auto_bet_scheduled_races(
        self,
        session: Session,
        session_id: str = "forward_live",
        min_ev: float = 1.15,
        min_prob: float = 0.0,
        bet_amount: int = 1000,
        max_bets_per_race: int = 2,
        strategy: Optional[Union[str, BaseStrategy]] = None,
        bet_sizer: Optional[Union[str, BaseBetSizer]] = None,
    ) -> List[SimulatedBet]:
        """
        Scans all scheduled races, evaluates prediction models, generates betting candidates,
        and records pending bets while deducting points from the virtual wallet.
        """
        wallet = self.get_or_create_wallet(session, session_id)
        active_strategy = get_strategy(
            strategy or "tansho_ev",
            min_ev=min_ev,
            min_prob=min_prob,
            max_bets=max_bets_per_race,
        )
        active_sizer = get_bet_sizer(bet_sizer or "flat", bet_amount=bet_amount)

        scheduled_races = (
            session.query(Race)
            .filter(Race.status == "scheduled")
            .order_by(Race.date.asc(), Race.id.asc())
            .all()
        )

        placed_bets: List[SimulatedBet] = []

        for race in scheduled_races:
            # Check if bets already placed for this race in this session
            existing_bets = (
                session.query(SimulatedBet)
                .filter(SimulatedBet.session_id == session_id, SimulatedBet.race_id == race.id)
                .count()
            )
            if existing_bets > 0:
                continue

            # Obtain predictions
            if self.predictor is not None:
                predictions = self.predictor.predict_race(race)
                # Also save predictions to DB if not present
                if not race.predictions:
                    self.predictor.save_predictions(session, race, predictions)
            elif race.predictions:
                predictions = race.predictions
            else:
                continue

            candidates = active_strategy.generate_candidates(race.id, predictions)

            for cand in candidates:
                bet_pts = active_sizer.calculate_bet_amount(cand, current_points=wallet.current_points)
                if bet_pts <= 0 or wallet.current_points < bet_pts:
                    continue

                # Deduct points from wallet
                wallet.current_points -= bet_pts
                wallet.total_invested += bet_pts
                wallet.total_bets += 1

                sim_bet = SimulatedBet(
                    session_id=session_id,
                    race_id=race.id,
                    bet_type=cand.bet_type,
                    combination=cand.combination or str(cand.horse_number),
                    bet_points=bet_pts,
                    odds_at_bet=cand.odds,
                    expected_value_at_bet=cand.expected_value,
                    status="pending",
                    payout_points=0,
                    profit=0,
                )
                session.add(sim_bet)
                placed_bets.append(sim_bet)

        session.commit()
        for b in placed_bets:
            session.refresh(b)
        session.refresh(wallet)
        return placed_bets

    def settle_race(
        self,
        session: Session,
        race_id: str,
        session_id: str = "forward_live",
    ) -> List[SimulatedBet]:
        """
        Settles pending simulated bets for a specific finished race.
        """
        pending_bets = (
            session.query(SimulatedBet)
            .filter(
                SimulatedBet.session_id == session_id,
                SimulatedBet.race_id == race_id,
                SimulatedBet.status == "pending",
            )
            .all()
        )

        if not pending_bets:
            return []

        race = session.query(Race).filter(Race.id == race_id).first()
        if race is None or race.status != "finished":
            return []

        wallet = self.get_or_create_wallet(session, session_id)

        for bet in pending_bets:
            won = False
            payout_points = 0

            payout_match = next(
                (p for p in race.payouts if p.bet_type == bet.bet_type and p.combination == bet.combination),
                None,
            )

            if payout_match is not None:
                won = True
                payout_points = int(bet.bet_points * (payout_match.payout / 100.0))
            else:
                # Fallback to checking race entry finish positions
                entry = next((e for e in race.entries if str(e.horse_number) == bet.combination), None)
                if entry and entry.finish_position is not None:
                    if bet.bet_type == "tansho" and entry.finish_position == 1:
                        won = True
                        payout_points = int(bet.bet_points * bet.odds_at_bet)
                    elif bet.bet_type == "fukusho":
                        threshold = 3 if len(race.entries) >= 8 else 2
                        if entry.finish_position <= threshold:
                            won = True
                            payout_points = int(bet.bet_points * bet.odds_at_bet)

            if won:
                bet.status = "won"
                bet.payout_points = payout_points
                bet.profit = payout_points - bet.bet_points
                wallet.won_bets += 1
                wallet.total_returned += payout_points
                wallet.current_points += payout_points
            else:
                bet.status = "lost"
                bet.payout_points = 0
                bet.profit = -bet.bet_points

            # Update max drawdown metric
            peak = max(wallet.initial_points, wallet.current_points)
            dd = ((peak - wallet.current_points) / peak * 100.0) if peak > 0 else 0.0
            if dd > wallet.max_drawdown:
                wallet.max_drawdown = round(dd, 2)

        session.commit()
        for b in pending_bets:
            session.refresh(b)
        session.refresh(wallet)
        return pending_bets

    def settle_all_finished_races(
        self,
        session: Session,
        session_id: str = "forward_live",
    ) -> List[SimulatedBet]:
        """
        Finds all pending bets on finished races and settles them in chronological order.
        """
        pending_bets = (
            session.query(SimulatedBet)
            .filter(
                SimulatedBet.session_id == session_id,
                SimulatedBet.status == "pending",
            )
            .all()
        )

        if not pending_bets:
            return []

        # Find distinct race IDs
        distinct_race_ids = list(dict.fromkeys(b.race_id for b in pending_bets))

        all_settled = []
        for race_id in distinct_race_ids:
            settled = self.settle_race(session, race_id=race_id, session_id=session_id)
            all_settled.extend(settled)

        return all_settled

    def run_daily_betting(
        self,
        db: Session,
        session_id: str = "forward_live",
        **kwargs,
    ) -> dict:
        """
        Convenience method matching task interface specification to execute daily betting and settlement.
        """
        placed = self.auto_bet_scheduled_races(db, session_id=session_id, **kwargs)
        settled = self.settle_all_finished_races(db, session_id=session_id)
        wallet = self.get_or_create_wallet(db, session_id=session_id)
        return {
            "session_id": session_id,
            "placed_bets_count": len(placed),
            "settled_bets_count": len(settled),
            "current_points": wallet.current_points,
            "roi": round((wallet.total_returned / wallet.total_invested * 100.0), 2) if wallet.total_invested > 0 else 100.0,
        }
