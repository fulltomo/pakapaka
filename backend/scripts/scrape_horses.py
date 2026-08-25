"""
Scrapes one profile row per horse (pedigree, breeder, auction price) into the horses table.

Horse IDs come from race_entries, so this runs after the race pass. Honours the same
time limit / auto-resume contract as scrape_real_data.py: it stops cleanly before the
runner expires and reports whether more horses remain.
"""

import argparse
import os
import sys
import time
from pathlib import Path

# Windows consoles default to cp932, which cannot encode the progress output.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import select  # noqa: E402

from app.core.database import SessionLocal, init_db  # noqa: E402
from app.models.schema import Race, RaceEntry, Horse  # noqa: E402
from app.data.scraper import NetkeibaScraper  # noqa: E402
from app.data.venues import JRA_COURSES  # noqa: E402


def set_github_output(name: str, value: str) -> None:
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"{name}={value}\n")


def pending_horse_ids(db, jra_only: bool):
    """Horse IDs that appear in race_entries but have no row in horses yet."""
    stmt = select(RaceEntry.horse_id).join(Race, Race.id == RaceEntry.race_id).distinct()
    if jra_only:
        stmt = stmt.where(Race.race_course.in_(list(JRA_COURSES.values())))

    seen = {h for (h,) in db.execute(select(Horse.horse_id))}
    return [h for (h,) in db.execute(stmt) if h and h not in seen]


def main() -> None:
    ap = argparse.ArgumentParser(description="Scrape horse profiles and pedigrees from netkeiba")
    ap.add_argument("--jra-only", action="store_true", help="Only horses that ran in JRA races")
    ap.add_argument("--max-horses", type=int, default=0, help="Cap for this run (0 = no cap)")
    ap.add_argument("--min-delay", type=float, default=1.2)
    ap.add_argument("--max-delay", type=float, default=2.2)
    ap.add_argument("--time-limit-minutes", type=float, default=320.0, help="0 disables the limit")
    ap.add_argument("--skip-pedigree", action="store_true",
                    help="Profile only — halves requests but drops sire/dam")
    args = ap.parse_args()

    start = time.time()
    init_db()
    db = SessionLocal()

    todo = pending_horse_ids(db, args.jra_only)
    total_remaining = len(todo)
    if args.max_horses > 0:
        todo = todo[:args.max_horses]

    already = db.query(Horse).count()
    print("=" * 70)
    print(f"🐎 馬プロフィール収集  未取得 {total_remaining:,} 頭 / 取得済 {already:,} 頭")
    print(f"   今回の対象: {len(todo):,} 頭  ({'血統あり' if not args.skip_pedigree else '血統なし'}, "
          f"{args.min_delay}〜{args.max_delay}秒間隔)")
    print("=" * 70)

    scraper = NetkeibaScraper(min_delay=args.min_delay, max_delay=args.max_delay)
    done = failed = 0
    for i, horse_id in enumerate(todo, 1):
        if args.time_limit_minutes > 0 and (time.time() - start) / 60.0 >= args.time_limit_minutes:
            print(f"\n⏰ 制限時間に到達 ({args.time_limit_minutes:.0f}分)。コミットして次回へ引き継ぎます。")
            break
        try:
            horse = scraper.scrape_horse_and_save(
                horse_id, db, with_pedigree=not args.skip_pedigree, use_cache=True)
            if horse is None:
                failed += 1
            else:
                done += 1
                if done % 50 == 0:
                    db.commit()
                    print(f"  [{done:,}/{len(todo):,}] {horse.horse_name} "
                          f"父={horse.sire} 母父={horse.broodmare_sire} 生産={horse.breeder}")
        except Exception as e:
            failed += 1
            print(f"  [Error] {horse_id}: {e}")

    db.commit()
    remaining = total_remaining - done
    print(f"\n✓ 今回 {done:,} 頭を取得 (失敗 {failed:,})。残り {remaining:,} 頭。")

    set_github_output("scraped_count", str(done))
    set_github_output("remaining", str(remaining))
    set_github_output("has_more", "true" if remaining > 0 and done > 0 else "false")
    db.close()


if __name__ == "__main__":
    main()
