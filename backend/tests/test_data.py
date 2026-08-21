import os
import tempfile
import time
import httpx
import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.schema import Base, Race, RaceEntry, Payout
from app.data.sample_generator import SampleDataGenerator
from app.data.cache import HTMLCache
from app.data.scraper import NetkeibaScraper


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_generate_sample_races(db_session):
    generator = SampleDataGenerator(seed=42)
    generator.generate_races(db_session, count=10)

    races = db_session.query(Race).all()
    assert len(races) == 10
    for r in races:
        assert len(r.entries) >= 8
        assert len(r.payouts) >= 1
        assert r.entries[0].odds > 0
        assert r.status == "finished"
        assert all(e.finish_position is not None for e in r.entries)


def test_sample_generator_payout_consistency(db_session):
    generator = SampleDataGenerator(seed=123)
    generator.generate_races(db_session, count=5)

    races = db_session.query(Race).all()
    for race in races:
        entries_sorted = sorted(race.entries, key=lambda e: e.finish_position or 999)
        first = entries_sorted[0]
        second = entries_sorted[1]
        third = entries_sorted[2]

        payout_map = {}
        for p in race.payouts:
            payout_map.setdefault(p.bet_type, []).append((p.combination, p.payout))

        # 単勝 check
        assert "tansho" in payout_map
        assert payout_map["tansho"][0][0] == str(first.horse_number)
        assert payout_map["tansho"][0][1] > 0

        # 複勝 check
        assert "fukusho" in payout_map
        fukusho_combos = [c for c, _ in payout_map["fukusho"]]
        assert str(first.horse_number) in fukusho_combos
        assert str(second.horse_number) in fukusho_combos
        assert str(third.horse_number) in fukusho_combos

        # 馬連 check
        assert "umaren" in payout_map
        expected_umaren = f"{min(first.horse_number, second.horse_number)}-{max(first.horse_number, second.horse_number)}"
        assert payout_map["umaren"][0][0] == expected_umaren

        # ワイド check
        assert "wide" in payout_map
        wide_combos = [c for c, _ in payout_map["wide"]]
        expected_w12 = f"{min(first.horse_number, second.horse_number)}-{max(first.horse_number, second.horse_number)}"
        expected_w13 = f"{min(first.horse_number, third.horse_number)}-{max(first.horse_number, third.horse_number)}"
        expected_w23 = f"{min(second.horse_number, third.horse_number)}-{max(second.horse_number, third.horse_number)}"
        assert expected_w12 in wide_combos
        assert expected_w13 in wide_combos
        assert expected_w23 in wide_combos


def test_sample_generator_scheduled_races(db_session):
    generator = SampleDataGenerator(seed=999)
    generator.generate_races(db_session, count=3, scheduled_count=2)

    races = db_session.query(Race).all()
    assert len(races) == 5

    finished = [r for r in races if r.status == "finished"]
    scheduled = [r for r in races if r.status == "scheduled"]
    assert len(finished) == 3
    assert len(scheduled) == 2

    for r in scheduled:
        assert len(r.payouts) == 0
        assert all(e.finish_position is None for e in r.entries)
        assert all(e.finish_time is None for e in r.entries)


def test_sample_generator_generate_sample_races_alias(db_session):
    generator = SampleDataGenerator(seed=10)
    races = generator.generate_sample_races(num_races=5, db=db_session)
    assert len(races) == 5
    assert db_session.query(Race).count() == 5


def test_html_cache():
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = HTMLCache(cache_dir=tmpdir)
        key = "202405010101"
        sample_html = "<html><body><h1>東京11R 日本ダービー</h1></body></html>"

        # Not cached initially
        assert not cache.has(key)
        assert cache.get(key) is None

        # Store cache
        cache.set(key, sample_html)
        assert cache.has(key)
        assert cache.get(key) == sample_html

        # Overwrite cache
        cache.set(key, "<html>updated</html>")
        assert cache.get(key) == "<html>updated</html>"

        # Delete cache
        assert cache.delete(key) is True
        assert not cache.has(key)
        assert cache.get(key) is None

        # Clear cache
        cache.set("k1", "html1")
        cache.set("k2", "html2")
        assert cache.has("k1") and cache.has("k2")
        cache.clear()
        assert not cache.has("k1") and not cache.has("k2")


SAMPLE_NETKEIBA_HTML = """
<!DOCTYPE html>
<html>
<head><title>2024年5月26日 東京11R 日本ダービー(G1) 結果・払戻 | netkeiba</title></head>
<body>
<div class="RaceName">日本ダービー</div>
<div class="RaceData01">15:40発走 / 芝2400m (左) / 天候:晴 / 馬場:良</div>
<div class="RaceData02">東京 11R</div>
<table class="race_table_01 nk_tb_common">
    <thead>
        <tr>
            <th>着順</th><th>枠番</th><th>馬番</th><th>馬名</th><th>性齢</th><th>斤量</th><th>騎手</th><th>タイム</th><th>着差</th><th>単勝オッズ</th><th>人気</th><th>馬体重</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>1</td><td>3</td><td>5</td><td><a href="/horse/2021105432/">ダノンデサイル</a></td><td>牡3</td><td>57.0</td><td><a href="/jockey/01015/">横山典弘</a></td><td>2:24.3</td><td></td><td>46.6</td><td>9</td><td>504(-2)</td>
        </tr>
        <tr>
            <td>2</td><td>7</td><td>15</td><td><a href="/horse/2021105433/">ジャスティンミラノ</a></td><td>牡3</td><td>57.0</td><td><a href="/jockey/01088/">戸崎圭太</a></td><td>2:24.6</td><td>2</td><td>2.2</td><td>1</td><td>512(+2)</td>
        </tr>
        <tr>
            <td>3</td><td>7</td><td>13</td><td><a href="/horse/2021105434/">シンエンペラー</a></td><td>牡3</td><td>57.0</td><td><a href="/jockey/01170/">坂井瑠星</a></td><td>2:24.8</td><td>1 1/4</td><td>15.8</td><td>7</td><td>486(0)</td>
        </tr>
        <tr>
            <td>4</td><td>1</td><td>1</td><td><a href="/horse/2021105435/">サンライズアース</a></td><td>牡3</td><td>57.0</td><td><a href="/jockey/01115/">池添謙一</a></td><td>2:25.0</td><td>1 1/4</td><td>34.1</td><td>8</td><td>520(+4)</td>
        </tr>
    </tbody>
</table>
<table class="pay_table_01">
    <tbody>
        <tr>
            <th class="tan">単勝</th>
            <td>5</td>
            <td class="txt_r">4,660</td>
            <td class="txt_r">9</td>
        </tr>
        <tr>
            <th class="fuku">複勝</th>
            <td>5<br>15<br>13</td>
            <td class="txt_r">770<br>140<br>390</td>
            <td class="txt_r">9<br>1<br>7</td>
        </tr>
        <tr>
            <th class="uren">馬連</th>
            <td>5 - 15</td>
            <td class="txt_r">6,860</td>
            <td class="txt_r">16</td>
        </tr>
        <tr>
            <th class="wide">ワイド</th>
            <td>5 - 15<br>5 - 13<br>13 - 15</td>
            <td class="txt_r">2,020<br>5,810<br>640</td>
            <td class="txt_r">18<br>51<br>2</td>
        </tr>
    </tbody>
</table>
</body>
</html>
"""


def test_scraper_parse_html():
    scraper = NetkeibaScraper()
    parsed = scraper.parse_race_result(SAMPLE_NETKEIBA_HTML, race_id="202405021211")

    assert parsed["id"] == "202405021211"
    assert parsed["race_name"] == "日本ダービー"
    assert parsed["race_course"] == "東京"
    assert parsed["race_number"] == 11
    assert parsed["distance"] == 2400
    assert parsed["surface"] == "芝"
    assert parsed["track_condition"] == "良"
    assert parsed["weather"] == "晴"
    assert parsed["status"] == "finished"

    assert len(parsed["entries"]) == 4
    e1 = parsed["entries"][0]
    assert e1["horse_number"] == 5
    assert e1["horse_name"] == "ダノンデサイル"
    assert e1["horse_id"] == "2021105432"
    assert e1["post_position"] == 3
    assert e1["sex"] == "牡"
    assert e1["age"] == 3
    assert e1["handicap_weight"] == 57.0
    assert e1["jockey_name"] == "横山典弘"
    assert e1["finish_position"] == 1
    assert e1["finish_time"] == "2:24.3"
    assert e1["odds"] == 46.6
    assert e1["popularity"] == 9
    assert e1["horse_weight"] == 504
    assert e1["horse_weight_diff"] == -2

    # Payouts check
    payouts = parsed["payouts"]
    assert len(payouts) >= 6
    tan = [p for p in payouts if p["bet_type"] == "tansho"]
    assert len(tan) == 1
    assert tan[0]["combination"] == "5"
    assert tan[0]["payout"] == 4660

    uren = [p for p in payouts if p["bet_type"] == "umaren"]
    assert len(uren) == 1
    assert uren[0]["combination"] == "5-15"
    assert uren[0]["payout"] == 6860


def test_scraper_save_to_db(db_session):
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = HTMLCache(cache_dir=tmpdir)
        cache.set("202405021211", SAMPLE_NETKEIBA_HTML)

        scraper = NetkeibaScraper(cache=cache)
        race = scraper.scrape_race_and_save("202405021211", db=db_session, use_cache=True)

        assert race is not None
        assert race.id == "202405021211"
        assert len(race.entries) == 4
        assert len(race.payouts) >= 6

        # Verify DB query
        saved = db_session.query(Race).filter_by(id="202405021211").first()
        assert saved is not None
        assert saved.race_name == "日本ダービー"


def test_scraper_rate_limiting():
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = HTMLCache(cache_dir=tmpdir)
        scraper = NetkeibaScraper(cache=cache, rate_limit_delay=0.1)

        with patch.object(httpx.Client, "get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = SAMPLE_NETKEIBA_HTML
            mock_get.return_value = mock_response

            t0 = time.time()
            scraper.fetch_race_html("race1", use_cache=False)
            scraper.fetch_race_html("race2", use_cache=False)
            t1 = time.time()

            assert t1 - t0 >= 0.09
            assert mock_get.call_count == 2


def test_scraper_error_handling():
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = HTMLCache(cache_dir=tmpdir)
        scraper = NetkeibaScraper(cache=cache)

        with patch.object(httpx.Client, "get") as mock_get:
            mock_get.side_effect = Exception("Connection error")
            html = scraper.fetch_race_html("bad_race_id", use_cache=False)
            assert html is None

            parsed = scraper.scrape_race("bad_race_id", use_cache=False)
            assert parsed is None

