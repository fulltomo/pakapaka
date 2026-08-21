"""
Forward Trading (Simulation) & Virtual Wallet REST API.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, Body
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.schema import SimulatedBet, WalletSession, Race
from app.schemas.pydantic_models import (
    WalletSessionSchema,
    SimulatedBetSchema,
    AutoBetRequest,
    AutoBetResultSchema,
)
from app.strategy.simulator import ForwardSimulator
from app.api.models import get_active_model

router = APIRouter(prefix="/simulation", tags=["simulation"])


@router.get("/wallet", response_model=WalletSessionSchema)
def get_wallet(
    session_id: str = Query("forward_live", description="Simulation session identifier"),
    db: Session = Depends(get_db),
):
    """
    Retrieves the current status, balance, ROI, win rate, and total profit of a virtual wallet session.
    """
    simulator = ForwardSimulator()
    wallet = simulator.get_or_create_wallet(db, session_id=session_id)
    return WalletSessionSchema.model_validate(wallet)


@router.post("/wallet/reset", response_model=WalletSessionSchema)
def reset_wallet(
    data: Optional[dict] = Body(default=None),
    session_id: Optional[str] = Query(None, description="Simulation session identifier"),
    initial_points: Optional[int] = Query(None, description="Initial points to reset wallet to"),
    db: Session = Depends(get_db),
):
    """
    Resets the virtual wallet balance and statistics to initial points, clearing previous bets.
    """
    # Extract session_id and initial_points from body or query
    req_body = data or {}
    target_session = req_body.get("session_id") or session_id or "forward_live"
    points = req_body.get("initial_points") or initial_points or 100000

    wallet = db.query(WalletSession).filter(WalletSession.session_id == target_session).first()
    if wallet is None:
        wallet = WalletSession(session_id=target_session)
        db.add(wallet)

    wallet.initial_points = points
    wallet.current_points = points
    wallet.total_invested = 0
    wallet.total_returned = 0
    wallet.total_bets = 0
    wallet.won_bets = 0
    wallet.max_drawdown = 0.0

    # Clear prior bets for this session
    db.query(SimulatedBet).filter(SimulatedBet.session_id == target_session).delete()

    db.commit()
    db.refresh(wallet)
    return WalletSessionSchema.model_validate(wallet)


@router.post("/auto-bet", response_model=AutoBetResultSchema)
def auto_bet_scheduled_races(
    req: Optional[AutoBetRequest] = None,
    db: Session = Depends(get_db),
):
    """
    Scans scheduled races, predicts outcomes with the active model, generates EV bets,
    and automatically registers pending tickets in the virtual wallet.
    """
    request_data = req or AutoBetRequest()
    model = get_active_model()
    simulator = ForwardSimulator(model=model)

    strategy_name = request_data.bet_type
    if not strategy_name.endswith("_ev") and strategy_name in ("tansho", "fukusho", "wide", "umaren"):
        strategy_name = f"{strategy_name}_ev"

    bet_sizer_name = "kelly" if request_data.use_kelly else "flat"

    try:
        placed = simulator.auto_bet_scheduled_races(
            session=db,
            session_id=request_data.session_id,
            min_ev=request_data.min_ev,
            min_prob=request_data.min_prob,
            bet_amount=request_data.bet_amount,
            strategy=strategy_name,
            bet_sizer=bet_sizer_name,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Auto-bet failed: {str(e)}")

    wallet = simulator.get_or_create_wallet(db, session_id=request_data.session_id)
    total_spent = sum(b.bet_points for b in placed)

    placed_schemas = [
        SimulatedBetSchema(
            id=b.id,
            session_id=b.session_id,
            race_id=b.race_id,
            bet_type=b.bet_type,
            combination=b.combination,
            bet_points=b.bet_points,
            odds_at_bet=b.odds_at_bet,
            expected_value_at_bet=b.expected_value_at_bet,
            status=b.status,
            payout_points=b.payout_points,
            profit=b.profit,
            created_at=b.created_at,
            race_name=b.race.race_name if b.race else None,
            race_date=b.race.date if b.race else None,
        )
        for b in placed
    ]

    return AutoBetResultSchema(
        session_id=request_data.session_id,
        placed_bets_count=len(placed),
        total_points_spent=total_spent,
        remaining_points=wallet.current_points,
        placed_bets=placed_schemas,
    )


@router.post("/settle")
def settle_finished_races(
    session_id: str = Query("forward_live", description="Simulation session identifier"),
    db: Session = Depends(get_db),
):
    """
    Checks all pending simulated bets against finished race results and payouts,
    crediting winning returns to the wallet.
    """
    simulator = ForwardSimulator()
    settled = simulator.settle_all_finished_races(session=db, session_id=session_id)
    wallet = simulator.get_or_create_wallet(session=db, session_id=session_id)

    settled_schemas = [
        SimulatedBetSchema(
            id=b.id,
            session_id=b.session_id,
            race_id=b.race_id,
            bet_type=b.bet_type,
            combination=b.combination,
            bet_points=b.bet_points,
            odds_at_bet=b.odds_at_bet,
            expected_value_at_bet=b.expected_value_at_bet,
            status=b.status,
            payout_points=b.payout_points,
            profit=b.profit,
            created_at=b.created_at,
            race_name=b.race.race_name if b.race else None,
            race_date=b.race.date if b.race else None,
        )
        for b in settled
    ]

    return {
        "status": "ok",
        "session_id": session_id,
        "settled_bets_count": len(settled),
        "settled_bets": settled_schemas,
        "current_points": wallet.current_points,
    }


@router.get("/bets", response_model=List[SimulatedBetSchema])
def list_bets(
    session_id: Optional[str] = Query("forward_live", description="Simulation session identifier"),
    status: Optional[str] = Query(None, description="Filter by bet status: pending, won, lost"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """
    Retrieves a paginated list of simulated bets for a session.
    """
    query = db.query(SimulatedBet)

    if session_id:
        query = query.filter(SimulatedBet.session_id == session_id)
    if status:
        query = query.filter(SimulatedBet.status == status)

    bets = query.order_by(SimulatedBet.created_at.desc(), SimulatedBet.id.desc()).offset(offset).limit(limit).all()

    return [
        SimulatedBetSchema(
            id=b.id,
            session_id=b.session_id,
            race_id=b.race_id,
            bet_type=b.bet_type,
            combination=b.combination,
            bet_points=b.bet_points,
            odds_at_bet=b.odds_at_bet,
            expected_value_at_bet=b.expected_value_at_bet,
            status=b.status,
            payout_points=b.payout_points,
            profit=b.profit,
            created_at=b.created_at,
            race_name=b.race.race_name if b.race else None,
            race_date=b.race.date if b.race else None,
        )
        for b in bets
    ]
