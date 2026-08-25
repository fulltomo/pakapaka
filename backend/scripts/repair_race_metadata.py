"""
Backfills race_course / race_number from race_id.

The scraper defaulted every race it could not parse to 東京 / 11R, which silently
mislabelled all NAR and ban'ei races. Idempotent — safe to re-run.
"""

import argparse
import sqlite3
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.data.venues import decode_race_id, UNKNOWN_COURSE, JRA_COURSES  # noqa: E402


def repair(db_path: str, dry_run: bool = False) -> Counter:
    conn = sqlite3.connect(db_path)
    rows = conn.execute("select id, race_course, race_number from races").fetchall()

    stats, updates = Counter(), []
    for race_id, course, number in rows:
        new_course, new_number = decode_race_id(race_id)
        if new_course is None and new_number is None:
            stats["undecodable"] += 1
            continue
        new_course = new_course or UNKNOWN_COURSE
        new_number = new_number or number

        stats["jra" if race_id[4:6] in JRA_COURSES else "non_jra"] += 1
        if (new_course, new_number) != (course, number):
            stats["changed"] += 1
            updates.append((new_course, new_number, race_id))

    if updates and not dry_run:
        conn.executemany("update races set race_course=?, race_number=? where id=?", updates)
        conn.commit()
    conn.close()
    return stats


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", default="pakapaka.db")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    s = repair(args.db, args.dry_run)
    print(f"{'[dry-run] ' if args.dry_run else ''}"
          f"JRA={s['jra']:,}  non-JRA={s['non_jra']:,}  "
          f"undecodable={s['undecodable']:,}  rewritten={s['changed']:,}")
