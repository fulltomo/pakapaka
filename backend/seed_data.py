"""
Initial Data Seeding and Model Bootstrapping Script for PakaPaka.

Performs complete end-to-end setup:
1. Initializes database schema and default forward trading wallet session.
2. Seeds 100 finished races with realistic entries, odds, and payouts.
3. Seeds 20 scheduled upcoming races for live inference and simulation.
4. Trains an initial LightGBM model using ModelTrainer and saves to data/models/latest_model.joblib.
5. Runs Predictor to generate calibrated win/place probabilities, EV, and recommendation marks for scheduled races.
6. Simulates historical forward trading bets on finished races and settles them, creating a rich equity progression history.
7. Auto-bets on upcoming scheduled races to provide active pending tickets for immediate dashboard interaction.
"""

import os
import sys
from pathlib import Path
from typing import Optional

# Ensure backend root is on sys.path
BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import settings
from app.core.database import engine, SessionLocal, init_db
from app.models.schema import Base, Race, RaceEntry, Payout, Prediction, SimulatedBet, WalletSession
from app.data.sample_generator import SampleDataGenerator
from app.ml.trainer import ModelTrainer
from app.ml.predictor import Predictor
from app.strategy.simulator import ForwardSimulator
from app.strategy.strategies import TanshoEVStrategy, FlatBetSizer


def seed_initial_data(
    num_finished_races: int = 100,
    num_scheduled_races: int = 20,
    seed: int = 42,
    clean_db: bool = True,
    model_dir: str = "data/models",
) -> dict:
    """
    Seeds database with historical and scheduled races, trains the initial LightGBM model,
    generates race predictions, and simulates forward trading bets.

    Returns
    -------
    dict
        Summary of seeded entities and training metrics.
    """
    print("=" * 70)
    print("🏇 PakaPaka AI 競馬投資システム - 初期データ投入＆モデル学習")
    print("=" * 70)

    # 1. Initialize / Clean Database
    if clean_db:
        print("\n[1/6] データベースのテーブルを初期化中...")
        Base.metadata.drop_all(bind=engine)
    init_db()
    print("  ✓ テーブルスキーマ初期化完了")
    print(f"  ✓ 初期ウォレットセッション '{settings.DEFAULT_FORWARD_SESSION_ID}' (残高: {settings.DEFAULT_WALLET_INITIAL_POINTS:,} pt) を準備")

    db = SessionLocal()
    try:
        # 2. Seed Realistic Races
        print(f"\n[2/6] JRAサンプルレースデータを生成中 (確定: {num_finished_races}件, 予定: {num_scheduled_races}件)...")
        generator = SampleDataGenerator(seed=seed)
        races = generator.generate_races(
            db=db,
            count=num_finished_races,
            scheduled_count=num_scheduled_races,
            start_date="2024-01-06",
        )

        total_entries = sum(len(r.entries) for r in races)
        total_payouts = sum(len(r.payouts) for r in races)
        finished_races = [r for r in races if r.status == "finished"]
        scheduled_races = [r for r in races if r.status == "scheduled"]

        print(f"  ✓ レース生成完了: 合計 {len(races)} レース")
        print(f"    - 確定レース: {len(finished_races)} 件 (払戻金レコード: {total_payouts} 件)")
        print(f"    - 出走前レース: {len(scheduled_races)} 件")
        print(f"    - 出走頭数: 合計 {total_entries} 頭")

        # 3. Train LightGBM Model
        print("\n[3/6] LightGBM 機械学習モデルの学習およびキャリブレーションを実行中...")
        os.makedirs(model_dir, exist_ok=True)
        trainer = ModelTrainer(
            model_dir=model_dir,
            test_size=0.2,
            random_state=seed,
            calibration_method="sigmoid",
        )
        model, metrics = trainer.train(db=db, save_model=True)

        print(f"  ✓ モデル学習完了: {metrics['model_version']}")
        print(f"    - 学習サンプル数: {metrics['train_samples']:,} 件")
        print(f"    - テストサンプル数: {metrics['test_samples']:,} 件")
        print(f"    - 単勝 ROC-AUC: {metrics['roc_auc']:.4f}")
        print(f"    - 単勝 LogLoss: {metrics['log_loss']:.4f}")
        print(f"    - 単勝 Brier Score: {metrics['brier_score']:.4f}")
        print(f"    - 複勝 ROC-AUC: {metrics['place_roc_auc']:.4f}")
        print(f"  ✓ モデル保存完了: {model_dir}/latest_model.joblib")

        # 4. Generate AI Predictions for Scheduled Races
        print("\n[4/6] 出走予定レースに対する AI 予想（勝率・複勝率・EV・印）を生成中...")
        predictor = Predictor(model=model)
        total_preds_saved = 0

        for race in scheduled_races:
            predictions = predictor.predict_race(race)
            saved = predictor.save_predictions(db, race, predictions)
            total_preds_saved += len(saved)

        print(f"  ✓ 予想生成完了: {len(scheduled_races)} レース / {total_preds_saved} 出走馬の予想レコードを保存")

        # 5. Populate Historical Simulated Bets & Settle for Realistic Equity Curve
        print("\n[5/6] 過去確定レースに対するシミュレーション投票履歴を生成・精算中...")
        simulator = ForwardSimulator(model=model, predictor=predictor)
        wallet = simulator.get_or_create_wallet(db, session_id=settings.DEFAULT_FORWARD_SESSION_ID)

        # Place bets on the last 30 finished races using TanshoEVStrategy
        strategy = TanshoEVStrategy(min_ev=1.05, min_prob=0.0, max_bets_per_race=2)
        sizer = FlatBetSizer(bet_amount=1000)

        history_races_to_bet = finished_races[-30:]
        historical_bets_placed = 0

        for race in history_races_to_bet:
            preds = predictor.predict_race(race)
            # Save predictions for historical inspection as well
            predictor.save_predictions(db, race, preds)

            candidates = strategy.generate_candidates(race.id, preds)
            for cand in candidates:
                bet_pts = sizer.calculate_bet_amount(cand, current_points=wallet.current_points)
                if bet_pts <= 0 or wallet.current_points < bet_pts:
                    continue

                wallet.current_points -= bet_pts
                wallet.total_invested += bet_pts
                wallet.total_bets += 1

                sim_bet = SimulatedBet(
                    session_id=settings.DEFAULT_FORWARD_SESSION_ID,
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
                db.add(sim_bet)
                historical_bets_placed += 1

        db.commit()

        # Settle the placed historical bets
        settled_bets = simulator.settle_all_finished_races(db, session_id=settings.DEFAULT_FORWARD_SESSION_ID)
        db.refresh(wallet)

        roi = (wallet.total_returned / wallet.total_invested * 100.0) if wallet.total_invested > 0 else 0.0
        win_rate = (wallet.won_bets / wallet.total_bets * 100.0) if wallet.total_bets > 0 else 0.0

        print(f"  ✓ 履歴投票・精算完了: {len(settled_bets)} 件の投票を処理")
        print(f"    - ウォレット残高: {wallet.current_points:,} pt (純損益: {wallet.current_points - wallet.initial_points:+,} pt)")
        print(f"    - 回収率 (ROI): {roi:.1f}%")
        print(f"    - 的中率: {win_rate:.1f}% ({wallet.won_bets} 勝 / {wallet.total_bets} 投票)")
        print(f"    - 最大ドローダウン: {wallet.max_drawdown:.1f}%")

        # 6. Auto-bet on upcoming scheduled races
        print("\n[6/6] 未発走レースへの自動投票（pending状態）を実行中...")
        placed_scheduled_bets = simulator.auto_bet_scheduled_races(
            session=db,
            session_id=settings.DEFAULT_FORWARD_SESSION_ID,
            min_ev=1.10,
            bet_amount=1000,
        )
        db.refresh(wallet)
        print(f"  ✓ 出走前レース投票完了: {len(placed_scheduled_bets)} 件の新規投票を待機中 (pending)")

        print("\n" + "=" * 70)
        print("🎉 初期データ投入および環境構築が正常に完了しました！")
        print("   バックエンド起動: uvicorn main:app --reload --port 8000")
        print("   フロントエンド起動: cd frontend && npm run dev")
        print("=" * 70)

        return {
            "finished_races": len(finished_races),
            "scheduled_races": len(scheduled_races),
            "model_version": metrics["model_version"],
            "roc_auc": metrics["roc_auc"],
            "settled_bets": len(settled_bets),
            "pending_bets": len(placed_scheduled_bets),
            "wallet_balance": wallet.current_points,
            "roi": roi,
        }
    finally:
        db.close()


if __name__ == "__main__":
    seed_initial_data()
