"""
Historical Strategy Backtesting REST API.
"""

from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.pydantic_models import (
    BacktestRequest,
    BacktestResultSchema,
    EquityPoint,
    SimulatedBetSchema,
)
from app.strategy.evaluator import BacktestEngine, BacktestConfig
from app.api.models import get_active_model

router = APIRouter(prefix="/backtest", tags=["backtest"])


@router.post("/run", response_model=BacktestResultSchema)
def run_backtest(
    req: BacktestRequest,
    db: Session = Depends(get_db),
):
    """
    Executes historical strategy backtesting over finished races in the database.
    Calculates ROI, hit rate, drawdown, and equity progression.
    """
    model = get_active_model()
    engine = BacktestEngine(model=model)

    strategy_name = req.bet_type
    if not strategy_name.endswith("_ev") and strategy_name in ("tansho", "fukusho", "wide", "umaren"):
        strategy_name = f"{strategy_name}_ev"

    bet_sizer_name = "kelly" if req.use_kelly else "flat"

    config = BacktestConfig(
        start_date=req.start_date,
        end_date=req.end_date,
        min_ev=req.min_ev,
        min_prob=req.min_prob,
        bet_strategy=strategy_name,
        bet_sizer=bet_sizer_name,
        bet_amount=req.bet_amount,
    )

    try:
        result = engine.run(db=db, config=config)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Backtest execution failed: {str(e)}")

    equity_points = [
        EquityPoint(
            date=ep["date"],
            race_id=ep["race_id"],
            cumulative_profit=ep["profit"],
            balance=ep["points"],
            drawdown=0.0,
        )
        for ep in result.equity_curve
    ]

    bets_list = [
        SimulatedBetSchema(
            id=idx,
            session_id="backtest",
            race_id=b["race_id"],
            bet_type=b["bet_type"],
            combination=str(b["combination"]),
            bet_points=b["bet_points"],
            odds_at_bet=float(b["odds"]),
            expected_value_at_bet=float(b["expected_value"]),
            status="won" if b["won"] else "lost",
            payout_points=b["payout_points"],
            profit=b["profit"],
            created_at=datetime.now(timezone.utc),
            race_name=b.get("race_name"),
            race_date=b.get("date"),
        )
        for idx, b in enumerate(result.bets, start=1)
    ]

    return BacktestResultSchema(
        total_bets=result.total_bets,
        won_bets=result.won_bets,
        win_rate=result.hit_rate,
        total_invested=result.total_invested,
        total_returned=result.total_returned,
        profit=result.profit,
        roi=result.roi,
        max_drawdown=result.max_drawdown,
        profit_factor=result.profit_factor,
        equity_curve=equity_points,
        bets=bets_list,
    )
