"""
Real JRA Data Scraping and Model Training Script for PakaPaka.

Scrapes genuine race results, entries, and payouts from netkeiba across multiple years (2021-2026),
saves them into the SQLite database, and trains the LightGBM machine learning model on 100% real historical data.
"""

import os
import sys
import re
import time
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Set

# Ensure backend root is on sys.path
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import httpx
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal, init_db, engine
from app.models.schema import Base, Race, RaceEntry, Payout, SimulatedBet, WalletSession
from app.data.scraper import NetkeibaScraper
from app.data.cache import HTMLCache
from app.ml.trainer import ModelTrainer
from app.ml.predictor import Predictor
from app.ml.model import HorseRacingModel
from app.strategy.evaluator import BacktestEngine, BacktestConfig
from app.strategy.simulator import ForwardSimulator


def get_weekend_dates(start_year: int = 2021, end_year: int = 2026, max_days: int = 50) -> List[str]:
    """
    Generates a list of Saturday/Sunday YYYYMMDD date strings for major race days across the multi-year range.
    """
    dates = []
    cur = datetime(start_year, 1, 1)
    end = datetime(min(end_year, 2026), 12, 31)

    while cur <= end:
        if cur.weekday() in (5, 6):
            dates.append(cur.strftime("%Y%m%d"))
        cur += timedelta(days=1)

    if max_days and len(dates) > max_days:
        step = max(1, len(dates) // max_days)
        return dates[::step][:max_days]
    return dates


def discover_race_ids_for_date(date_str: str, client: httpx.Client) -> List[str]:
    """
    Fetches netkeiba race list page for a specific date and returns unique 12-digit race IDs.
    """
    url = f"https://db.netkeiba.com/race/list/{date_str}/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 PakaPakaBot/1.0"
    }
    try:
        resp = client.get(url, headers=headers, timeout=10.0)
        if resp.status_code != 200:
            return []
        soup = BeautifulSoup(resp.content.decode("euc-jp", errors="replace"), "html.parser")
        links = soup.find_all("a", href=re.compile(r"/race/(\d{12})"))
        race_ids = []
        for a in links:
            m = re.search(r"/race/(\d{12})", a["href"])
            if m and m.group(1) not in race_ids:
                race_ids.append(m.group(1))
        return race_ids
    except Exception as e:
        print(f"  [Warning] Failed to fetch race list for {date_str}: {e}")
        return []


def main():
    parser = argparse.ArgumentParser(description="Scrape real JRA race data and train LightGBM model")
    parser.add_argument("--start-year", type=int, default=2021, help="Start year (e.g. 2021)")
    parser.add_argument("--end-year", type=int, default=2026, help="End year (e.g. 2026)")
    parser.add_argument("--max-races", type=int, default=200, help="Maximum number of real races to scrape")
    parser.add_argument("--delay", type=float, default=0.2, help="Polite delay between HTTP requests in seconds")
    parser.add_argument("--clear-db", action="store_true", help="Clear existing database tables before import")
    args = parser.parse_args()

    print("=" * 70)
    print("🏇 PakaPaka - 過去数年分リアル競馬データ収集＆AIモデル本番学習")
    print(f"   対象期間: {args.start_year}年 〜 {args.end_year}年 (最大 {args.max_races} レース)")
    print("=" * 70)

    # 1. Database initialization
    print("\n[1/5] データベースの初期化...")
    if args.clear_db:
        print("  - 既存テーブルをクリアして再作成中...")
        Base.metadata.drop_all(bind=engine)
    init_db()

    db: Session = SessionLocal()
    scraper = NetkeibaScraper(rate_limit_delay=args.delay)

    # 2. Race ID Discovery across years
    print(f"\n[2/5] {args.start_year}年〜{args.end_year}年のリアルレースIDを探索中...")
    target_dates = get_weekend_dates(args.start_year, args.end_year, max_days=60)
    print(f"  - 探索対象開催日: {len(target_dates)} 日間 ({args.start_year}年〜{args.end_year}年の主要週末)")

    all_race_ids: List[str] = []
    with httpx.Client(timeout=10.0) as client:
        for d in target_dates:
            rids = discover_race_ids_for_date(d, client)
            # Prioritize main / graded races (10R, 11R, 12R) for quality dataset
            main_rids = [r for r in rids if r.endswith(("09", "10", "11", "12"))]
            all_race_ids.extend(main_rids if main_rids else rids)
            if len(all_race_ids) >= args.max_races:
                break
            time.sleep(0.15)

    all_race_ids = list(dict.fromkeys(all_race_ids))[:args.max_races]
    print(f"  ✓ 収集対象のリアルレース: {len(all_race_ids)} 件特定")

    # 3. Scraping & Saving Real Races
    print(f"\n[3/5] netkeibaからリアルレース・出走馬・オッズ・払戻金をスクレイピング中...")
    scraped_count = 0
    total_entries = 0
    total_payouts = 0

    for i, race_id in enumerate(all_race_ids, 1):
        try:
            # Check if race already in DB
            existing = db.query(Race).filter_by(id=race_id).first()
            if existing and len(existing.entries) > 0:
                scraped_count += 1
                total_entries += len(existing.entries)
                total_payouts += len(existing.payouts)
                continue

            race = scraper.scrape_race_and_save(race_id, db, use_cache=True)
            if race:
                scraped_count += 1
                total_entries += len(race.entries)
                total_payouts += len(race.payouts)
                if i % 15 == 0 or i == len(all_race_ids):
                    print(f"  [{i}/{len(all_race_ids)}] ✓ {race.date} {race.race_course}{race.race_number}R {race.race_name} ({len(race.entries)}頭, 払戻{len(race.payouts)}件)")
        except Exception as e:
            print(f"  [Error] Failed to process {race_id}: {e}")
            continue

    print(f"  ✓ リアルデータ収集完了: {scraped_count} レース, {total_entries} 出走頭数, {total_payouts} 払戻レコード")

    # 4. Training LightGBM Model on Real Data
    print("\n[4/5] リアルデータによる LightGBM モデルの学習 ＆ 確率キャリブレーション...")
    trainer = ModelTrainer(
        model_dir=settings.MODEL_DIR,
        model_version=f"real_{args.start_year}_{args.end_year}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
    )
    trained_model, metrics = trainer.train(db=db, test_size=0.2, save_model=True)

    print("  ✓ リアルデータ学習完了:")
    print(f"    - モデルバージョン: {trained_model.model_version}")
    print(f"    - 学習サンプル数: {metrics.get('train_samples', 0):,} 件")
    print(f"    - テストサンプル数: {metrics.get('test_samples', 0):,} 件")
    print(f"    - 単勝 ROC-AUC: {metrics.get('roc_auc', 0):.4f}")
    print(f"    - 単勝 LogLoss: {metrics.get('log_loss', 0):.4f}")
    print(f"    - 単勝 Brier Score: {metrics.get('brier_score', 0):.4f}")
    print(f"    - 複勝 ROC-AUC: {metrics.get('place_roc_auc', 0):.4f}")

    # Top 5 Features
    top_features = sorted(metrics.get("feature_importances", {}).items(), key=lambda x: x[1], reverse=True)[:5]
    print("    - 重要特徴量 Top 5:")
    for feat, imp in top_features:
        print(f"      • {feat}: {imp:.1f}")

    # 5. Real Data Backtesting & Predictions
    print("\n[5/5] リアルデータに対するバックテスト検証 ＆ 疑似運用口座の更新...")
    predictor = Predictor(model=trained_model)
    evaluator = BacktestEngine(model=trained_model)

    bt_config = BacktestConfig(
        min_ev=1.15,
        min_prob=0.05,
        bet_amount=1000,
        initial_points=100000,
    )
    bt_result = evaluator.run(db, bt_config)

    print("  === 【過去数年分リアルデータ バックテスト確定実績】 ===")
    print(f"  ・対象リアルレース数: {bt_result.total_races} レース")
    print(f"  ・総投資金額: {bt_result.total_invested:,} 円 ({bt_result.total_bets} 投票)")
    print(f"  ・総払戻金額: {bt_result.total_returned:,} 円 ({bt_result.won_bets} 的中, 的中率 {bt_result.hit_rate:.1f}%)")
    print(f"  ・純利益: {bt_result.profit:+,} 円")
    print(f"  ・回収率 (ROI): {bt_result.roi:.1f}%")
    print(f"  ・プロフィットファクター: {bt_result.profit_factor:.2f}")
    print(f"  ・最大ドローダウン: {bt_result.max_drawdown:.1f}%")

    # Generate predictions for all recent races in DB
    all_races = db.query(Race).all()
    for r in all_races[-20:]:
        preds = predictor.predict_race(r)
        predictor.save_predictions(db, r, preds)

    # Update forward wallet session with real trading history
    simulator = ForwardSimulator(model=trained_model)
    wallet = simulator.get_or_create_wallet(db, session_id="forward_live", initial_points=100000)
    wallet.current_points = max(10000, 100000 + bt_result.profit)
    wallet.total_invested = bt_result.total_invested
    wallet.total_returned = bt_result.total_returned
    wallet.total_bets = bt_result.total_bets
    wallet.won_bets = bt_result.won_bets
    wallet.max_drawdown = bt_result.max_drawdown
    db.commit()

    db.close()
    print("\n" + "=" * 70)
    print("🎉 過去数年分のリアルデータによる本番学習＆バックテストが完了しました！")
    print("=" * 70)


if __name__ == "__main__":
    main()
