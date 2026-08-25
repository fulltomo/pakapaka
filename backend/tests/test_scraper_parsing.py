"""Parsing contracts for the netkeiba scraper — the fields that used to be lost silently."""
import pytest
from bs4 import BeautifulSoup

from app.data.scraper import NetkeibaScraper, PARSER_VERSION


@pytest.fixture
def scraper():
    return NetkeibaScraper()


# --- going / weather: netkeiba writes "天候 : 晴", spaces around the colon ---

@pytest.mark.parametrize("text, weather, going", [
    ("天候 : 晴 / 芝 : 良", "晴", "良"),
    ("天候 : 雨 / ダート : 不良", "雨", "不良"),
    ("天候:曇/芝:稍重", "曇", "稍重"),
    ("天候 : 小雪 / 芝 : 重", "小雪", "重"),
])
def test_parse_going(scraper, text, weather, going):
    assert scraper._parse_going(text, "晴", "良") == (weather, going)


def test_parse_going_keeps_current_when_absent(scraper):
    assert scraper._parse_going("スポンサー名 焼肉新昌苑", "曇", "重") == ("曇", "重")


def test_parse_going_ignores_non_going_words(scraper):
    """The old loose pattern swallowed race names; only the four real values may match."""
    _, going = scraper._parse_going("芝 : 桜並木賞", "晴", "良")
    assert going == "良"


# --- class / condition / post time ---

INTRO = ("11 R 3歳以上1勝クラス 芝左1400m / 天候 : 晴 / 芝 : 良 / "
         "発走 : 17:50 2026年08月23日 3回中京2日目 3歳以上1勝クラス [指](定量)")


def test_parse_class(scraper):
    race_class, condition, post_time = scraper._parse_class(INTRO)
    assert race_class == "3歳以上1勝クラス"
    assert condition == "[指](定量)"
    assert post_time == "17:50"


def test_parse_class_on_empty_header(scraper):
    assert scraper._parse_class("") == (None, None, None)


# --- lap times & pace ---

def test_parse_lap(scraper):
    html = ('<table class="result_table_02"><tr><td>ラップタイム ラップ '
            '12.2 - 10.9 - 11.1 - 11.5 ペース 12.2 - 23.1 - 34.2 (34.2-33.8)</td></tr></table>')
    lap, pace = scraper._parse_lap(BeautifulSoup(html, "html.parser"))
    assert lap == "12.2-10.9-11.1-11.5"
    assert pace == "34.2-33.8"


def test_parse_lap_absent(scraper):
    assert scraper._parse_lap(BeautifulSoup("<div>no laps</div>", "html.parser")) == (None, None)


# --- pedigree: generations are encoded as rowspans, 16 -> sire/dam, 8 -> their parents ---

def _ped_html(names):
    cells = "".join(f'<td rowspan="{rs}"><a>{n}</a></td>' for rs, n in names)
    return f'<table class="blood_table"><tr>{cells}</tr></table>'


def test_parse_pedigree(scraper):
    out = scraper.parse_pedigree(_ped_html([
        (16, "モーリス"), (8, "スクリーンヒーロー"), (8, "メジロフランシス"),
        (16, "ピュアチャプレット"), (8, "クロフネ"), (8, "バプティスタ"),
    ]))
    assert out == {"sire": "モーリス", "sire_sire": "スクリーンヒーロー",
                   "dam": "ピュアチャプレット", "broodmare_sire": "クロフネ"}


def test_parse_pedigree_missing_table(scraper):
    assert scraper.parse_pedigree("<div/>") == {
        "sire": None, "sire_sire": None, "dam": None, "broodmare_sire": None}


# --- small value parsers ---

@pytest.mark.parametrize("text, expected", [
    ("4,200万円", 4200.0), ("935万円", 935.0), ("-", None), ("", None), (None, None)])
def test_parse_price(scraper, text, expected):
    assert scraper._parse_price(text) == expected


@pytest.mark.parametrize("text, expected", [
    ("2023年2月28日", "2023-02-28"), ("1995年12月5日", "1995-12-05"), ("不明", None), (None, None)])
def test_parse_jp_date(scraper, text, expected):
    assert scraper._parse_jp_date(text) == expected


# --- the regression: a paywalled column stealing the finish-time mapping ---

# Header strings exactly as BeautifulSoup reads them off the live page.
RESULT_TABLE = """
<table class="race_table_01">
  <tr>
    <th>着順</th><th>枠番</th><th>馬番</th><th>馬名</th><th>性齢</th><th>斤量</th>
    <th>騎手</th><th>タイム</th><th>着差</th>
    <th>ﾀｲﾑ指数タイム指数(通常)タイム指数マスター</th>
    <th>ﾀｲﾑ指数Mタイム指数(通常)タイム指数マスター</th>
    <th>ｽﾀｰﾄ指数</th><th>追走指数</th><th>上がり指数</th>
    <th>通過</th><th>上り</th><th>単勝</th><th>人気</th><th>馬体重</th>
    <th>調教ﾀｲﾑ</th><th>厩舎ｺﾒﾝﾄ</th><th>備考</th><th>調教師</th><th>馬主</th><th>賞金(万円)</th>
  </tr>
  <tr>
    <td>1</td><td>2</td><td>4</td><td><a href="/horse/2023107169/">エルハーベン</a></td>
    <td>牡3</td><td>54</td><td><a href="/jockey/01220/">田山旺佑</a></td><td>1:19.1</td><td></td>
    <td></td><td></td><td></td><td></td><td></td>
    <td>4-5</td><td>33.4</td><td>6.7</td><td>3</td><td>500(+16)</td>
    <td></td><td></td><td></td><td>[西] 藤岡健一</td><td>吉田勝己</td><td>820.0</td>
  </tr>
</table>
"""


def test_result_columns_survive_the_paywalled_index_columns(scraper):
    entries = scraper._parse_entries(BeautifulSoup(RESULT_TABLE, "html.parser"), "202607030211")
    assert len(entries) == 1
    e = entries[0]

    # "タイム指数(通常)" contains "タイム" and used to overwrite the real finish-time column.
    assert e["finish_time"] == "1:19.1"
    assert e["finish_position"] == 1
    assert e["final_600m"] == 33.4
    assert e["corner_positions"] == "4-5"
    assert e["prize_money"] == 820.0
    assert e["owner_name"] == "吉田勝己"
    assert e["odds"] == 6.7
    assert e["popularity"] == 3
    assert e["horse_id"] == "2023107169"
    assert e["trainer_name"].endswith("藤岡健一"), "厩舎ｺﾒﾝﾄ must not win the trainer column"
    assert e["horse_weight"] == 500


def test_parser_version_is_set_for_refresh_detection():
    assert isinstance(PARSER_VERSION, int) and PARSER_VERSION >= 2
