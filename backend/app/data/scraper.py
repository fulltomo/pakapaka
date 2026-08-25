import re
import time
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
import httpx
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from app.models.schema import Race, RaceEntry, Payout, Horse
from app.data.cache import HTMLCache
from app.data.venues import decode_race_id, UNKNOWN_COURSE


# Bumped whenever the parser starts extracting fields older rows do not have, so a
# refresh pass can tell which races still need re-fetching.
PARSER_VERSION = 2


def _to_float(text: str):
    """Parses a numeric cell, tolerating thousands separators and blanks."""
    try:
        return float(str(text).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


class NetkeibaScraper:
    """
    Scraper for netkeiba race data with local HTML caching and rate-limiting.
    """

    BASE_DB_URL = "https://db.netkeiba.com/race/{race_id}/"
    HORSE_URL = "https://db.netkeiba.com/horse/{horse_id}/"
    PEDIGREE_URL = "https://db.netkeiba.com/horse/ped/{horse_id}/"
    DEFAULT_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36 PakaPakaBot/1.0"
        ),
        "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
    }

    def __init__(
        self,
        cache: Optional[HTMLCache] = None,
        rate_limit_delay: float = 1.2,
        min_delay: float = 1.0,
        max_delay: float = 2.2,
        timeout: float = 15.0,
        max_retries: int = 3,
    ):
        self.cache = cache if cache is not None else HTMLCache()
        self.rate_limit_delay = rate_limit_delay
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.timeout = timeout
        self.max_retries = max_retries
        self._last_request_time: float = 0.0

    def fetch_race_html(self, race_id: str, use_cache: bool = True) -> Optional[str]:
        """Fetches the result page for a race ID."""
        return self._fetch(self.BASE_DB_URL.format(race_id=race_id), race_id, use_cache)

    def fetch_horse_html(self, horse_id: str, use_cache: bool = True) -> Optional[str]:
        """Fetches the profile page for a horse ID."""
        return self._fetch(self.HORSE_URL.format(horse_id=horse_id), f"horse_{horse_id}", use_cache)

    def fetch_pedigree_html(self, horse_id: str, use_cache: bool = True) -> Optional[str]:
        """Fetches the pedigree page for a horse ID (the profile page renders its pedigree in JS)."""
        return self._fetch(self.PEDIGREE_URL.format(horse_id=horse_id), f"ped_{horse_id}", use_cache)

    def _fetch(self, url: str, cache_key: str, use_cache: bool = True) -> Optional[str]:
        """
        Polite fetch shared by every page type: jitter delay, local cache, retry with
        backoff on rate limiting.
        """
        import random
        if use_cache and self.cache.has(cache_key):
            return self.cache.get(cache_key)

        # Rate limiting check with random jitter
        target_delay = random.uniform(self.min_delay, self.max_delay) if self.max_delay > self.min_delay else self.rate_limit_delay
        elapsed = time.time() - self._last_request_time
        if elapsed < target_delay:
            time.sleep(target_delay - elapsed)

        for attempt in range(1, self.max_retries + 1):
            try:
                with httpx.Client(timeout=self.timeout, headers=self.DEFAULT_HEADERS) as client:
                    response = client.get(url)
                    self._last_request_time = time.time()

                    # Handle Rate-Limiting / Server Busy (429 or 503)
                    if response.status_code in (429, 503):
                        backoff = 20.0 * attempt
                        print(f"  [Scraper Warning] Rate limited ({response.status_code}). Backing off for {backoff}s before retry {attempt}/{self.max_retries}...")
                        time.sleep(backoff)
                        continue

                    if response.status_code != 200:
                        return None

                    # netkeiba uses euc-jp encoding
                    content = response.content.decode("euc-jp", errors="replace")
                    if use_cache:
                        self.cache.set(cache_key, content)
                    return content
            except Exception as e:
                if attempt == self.max_retries:
                    return None
                time.sleep(5.0 * attempt)
        return None

    def _parse_race_metadata(self, soup: BeautifulSoup, race_id: str) -> Dict[str, Any]:
        """
        Extracts race name, course, distance, surface, weather, track condition from HTML soup.
        """
        race_name = "レース"
        intro = soup.find(class_="data_intro")
        if intro and intro.find("h1"):
            race_name = intro.find("h1").get_text(strip=True)
        else:
            rname_elem = soup.find(class_="RaceName") or soup.find("h1") or soup.find(class_="racedata")
            if rname_elem:
                race_name = rname_elem.get_text(strip=True)

        # Race Course & Number.
        # The race_id is authoritative (it encodes both); the page is only a fallback,
        # since its course regex covers JRA venues alone and silently defaulted
        # every NAR/ban'ei race to 東京 / 11R.
        race_course, race_number = decode_race_id(race_id)
        rdata02 = soup.find(class_="RaceData02") or (intro.find(class_="smalltxt") if intro else None)
        if rdata02 and (race_course is None or race_number is None):
            rdata02_text = rdata02.get_text()
            if race_course is None:
                course_match = re.search(r"(東京|中山|京都|阪神|新潟|中京|小倉|札幌|函館|福島)", rdata02_text)
                if course_match:
                    race_course = course_match.group(1)
            if race_number is None:
                num_match = re.search(r"(\d+)R", rdata02_text)
                if num_match:
                    race_number = int(num_match.group(1))
        race_course = race_course or UNKNOWN_COURSE
        race_number = race_number or 0

        # Surface, Distance, Weather, Track Condition
        surface = "芝"
        distance = 2000
        weather = "晴"
        track_condition = "良"

        rdata01 = soup.find(class_="RaceData01") or soup.find(class_="racedata")
        if rdata01:
            txt = rdata01.get_text()
            if "ダ" in txt:
                surface = "ダート"
            elif "芝" in txt:
                surface = "芝"

            dist_match = re.search(r"(\d{3,4})m", txt)
            if dist_match:
                distance = int(dist_match.group(1))

            weather, track_condition = self._parse_going(txt, weather, track_condition)

        intro_txt = intro.get_text(" ", strip=True).replace(" ", " ") if intro else ""
        if intro_txt:
            weather, track_condition = self._parse_going(intro_txt, weather, track_condition)

        race_class, race_condition, post_time = self._parse_class(intro_txt)
        lap_times, pace = self._parse_lap(soup)

        # Date
        date_str = "2024-01-01"
        date_match = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日", soup.get_text())
        if date_match:
            y, m, d = date_match.groups()
            date_str = f"{int(y):04d}-{int(m):02d}-{int(d):02d}"

        return {
            "id": race_id,
            "date": date_str,
            "race_course": race_course,
            "race_number": race_number,
            "race_name": race_name,
            "distance": distance,
            "surface": surface,
            "track_condition": track_condition,
            "weather": weather,
            "race_class": race_class,
            "race_condition": race_condition,
            "post_time": post_time,
            "lap_times": lap_times,
            "pace": pace,
            "status": "finished",
        }

    # netkeiba writes these as "天候 : 晴" / "芝 : 良" — spaces around the colon are
    # what made the previous patterns miss and fall back to the defaults.
    WEATHER_VALUES = ("晴", "曇", "小雨", "雨", "小雪", "雪")
    GOING_VALUES = ("良", "稍重", "重", "不良")

    def _parse_going(self, txt: str, weather: str, track_condition: str):
        """Extracts weather and going, keeping the current values when absent."""
        w = re.search(r"天候\s*[:：]\s*(" + "|".join(self.WEATHER_VALUES) + ")", txt)
        if w:
            weather = w.group(1)
        c = re.search(r"(?:馬場|芝|ダート|ダ)\s*[:：]\s*(" + "|".join(self.GOING_VALUES) + ")", txt)
        if c:
            track_condition = c.group(1)
        return weather, track_condition

    def _parse_class(self, intro_txt: str):
        """
        Pulls race class, entry condition and post time out of the data_intro header, e.g.
        "... 発走 : 17:50 2026年08月23日 3回中京2日目 3歳以上1勝クラス  [指](定量)"
        """
        if not intro_txt:
            return None, None, None

        post = re.search(r"発走\s*[:：]\s*(\d{1,2}:\d{2})", intro_txt)
        post_time = post.group(1) if post else None

        # The class name sits between the meeting ("3回中京2日目") and the bracketed condition.
        cls = re.search(r"\d+回\S+?\d+日目\s*(.*?)\s*(?=[\[(]|$)", intro_txt)
        race_class = (cls.group(1).strip() or None) if cls else None

        cond = re.search(r"((?:\[[^\]]*\]|\([^)]*\))+)\s*$", intro_txt)
        race_condition = cond.group(1) if cond else None
        return race_class, race_condition, post_time

    def _parse_lap(self, soup: BeautifulSoup):
        """Extracts the 200m lap splits and the first/last 3F pace from the lap table."""
        for tb in soup.find_all("table", class_="result_table_02"):
            txt = tb.get_text(" ", strip=True).replace(" ", " ")
            if "ラップタイム" not in txt:
                continue
            laps = re.search(r"ラップ\s*([\d.\s\-]+?)\s*ペース", txt)
            lap_times = re.sub(r"\s*-\s*", "-", laps.group(1).strip()) if laps else None
            pace = re.search(r"\((\d+\.\d+\s*-\s*\d+\.\d+)\)", txt)
            return lap_times, (re.sub(r"\s*", "", pace.group(1)) if pace else None)
        return None, None

    def _parse_entries(self, soup: BeautifulSoup, race_id: str) -> List[Dict[str, Any]]:
        """
        Parses race result table into list of entry dictionaries using header-aware mapping.
        """
        entries = []
        table = soup.find("table", class_=re.compile(r"race_table|nk_tb_common"))
        if not table:
            return entries

        # Extract header column map
        header_tr = table.find("tr")
        col_map: Dict[str, int] = {}
        if header_tr:
            for idx, th in enumerate(header_tr.find_all(["th", "td"])):
                txt = th.get_text(strip=True)
                # Paywalled columns (ﾀｲﾑ指数 / ｽﾀｰﾄ指数 / 上がり指数 ...) are always blank, and
                # one of them contains the text "タイム指数(通常)" — which used to steal the
                # "タイム" mapping from the real finish-time column further left.
                if "指数" in txt:
                    continue
                if "着順" in txt or "着" == txt:
                    col_map.setdefault("finish_position", idx)
                elif "枠" in txt:
                    col_map.setdefault("post_position", idx)
                elif "馬番" in txt:
                    col_map.setdefault("horse_number", idx)
                elif "馬名" in txt:
                    col_map.setdefault("horse_name", idx)
                elif "性齢" in txt:
                    col_map.setdefault("sex_age", idx)
                elif "斤量" in txt:
                    col_map.setdefault("handicap_weight", idx)
                elif "騎手" in txt:
                    col_map.setdefault("jockey_name", idx)
                elif "タイム" in txt:
                    col_map.setdefault("finish_time", idx)
                elif "着差" in txt:
                    col_map.setdefault("margin", idx)
                elif "単勝" in txt or "オッズ" in txt:
                    col_map.setdefault("odds", idx)
                elif "人気" in txt:
                    col_map.setdefault("popularity", idx)
                elif "馬体重" in txt:
                    col_map.setdefault("horse_weight", idx)
                elif "上り" in txt:  # 上がり3ハロン. Distinct from the paywalled "上がり指数".
                    col_map.setdefault("final_600m", idx)
                elif "通過" in txt:
                    col_map.setdefault("corner_positions", idx)
                elif "賞金" in txt:
                    col_map.setdefault("prize_money", idx)
                elif "馬主" in txt:
                    col_map.setdefault("owner_name", idx)
                elif "調教師" in txt:
                    col_map.setdefault("trainer_name", idx)
                elif "厩舎" in txt and "ｺﾒﾝﾄ" not in txt and "コメント" not in txt:
                    col_map["trainer_name"] = idx

        rows = table.find_all("tr")[1:]  # Skip header
        for row in rows:
            cols = row.find_all(["td", "th"])
            if len(cols) < 5:
                continue

            try:
                def get_val(key: str, default: str = "") -> str:
                    idx = col_map.get(key)
                    if idx is not None and idx < len(cols):
                        return cols[idx].get_text(strip=True)
                    return default

                # Finish Position
                finish_pos_text = get_val("finish_position")
                finish_position = int(finish_pos_text) if finish_pos_text.isdigit() else None

                # Post position & Horse number
                post_pos_text = get_val("post_position", "1")
                post_position = int(post_pos_text) if post_pos_text.isdigit() else 1

                horse_num_text = get_val("horse_number", str(len(entries) + 1))
                horse_number = int(horse_num_text) if horse_num_text.isdigit() else len(entries) + 1

                # Horse Name & ID
                horse_idx = col_map.get("horse_name", 3)
                horse_name = "競走馬"
                horse_id = f"h_{horse_number}"
                if horse_idx < len(cols):
                    horse_name = cols[horse_idx].get_text(strip=True)
                    h_link = cols[horse_idx].find("a")
                    if h_link and h_link.get("href"):
                        h_match = re.search(r"/horse/(\d+)/?", h_link["href"])
                        if h_match:
                            horse_id = h_match.group(1)

                # Sex & Age
                sex_age_text = get_val("sex_age", "牡4")
                sex = sex_age_text[0] if sex_age_text else "牡"
                age_match = re.search(r"\d+", sex_age_text)
                age = int(age_match.group(0)) if age_match else 4

                # Handicap Weight
                handicap_text = get_val("handicap_weight", "57.0")
                try:
                    handicap_weight = float(handicap_text)
                except ValueError:
                    handicap_weight = 57.0

                jockey_name = get_val("jockey_name", "騎手")
                trainer_name_raw = get_val("trainer_name", "調教師")
                trainer_name = re.sub(r"\[.+?\]", "", trainer_name_raw).strip()

                finish_time = get_val("finish_time") or None
                margin = get_val("margin") or None

                final_600m = _to_float(get_val("final_600m"))
                corner_positions = get_val("corner_positions") or None
                prize_money = _to_float(get_val("prize_money"))
                owner_name = get_val("owner_name") or None

                # Odds & Popularity
                odds_text = get_val("odds", "1.0").replace(",", "")
                try:
                    odds = float(odds_text)
                except ValueError:
                    odds = 1.0

                pop_text = get_val("popularity", "")
                popularity = int(pop_text) if pop_text.isdigit() else None

                # Horse Weight & Diff
                weight_text = get_val("horse_weight", "500")
                horse_weight = 500
                horse_weight_diff = 0
                w_match = re.search(r"(\d{3})(?:\(([+-]?\d+)\))?", weight_text)
                if w_match:
                    horse_weight = int(w_match.group(1))
                    if w_match.group(2):
                        horse_weight_diff = int(w_match.group(2))

                entries.append({
                    "race_id": race_id,
                    "final_600m": final_600m,
                    "corner_positions": corner_positions,
                    "prize_money": prize_money,
                    "owner_name": owner_name,
                    "horse_id": horse_id,
                    "horse_name": horse_name,
                    "post_position": post_position,
                    "horse_number": horse_number,
                    "jockey_name": jockey_name,
                    "trainer_name": trainer_name,
                    "sex": sex,
                    "age": age,
                    "handicap_weight": handicap_weight,
                    "horse_weight": horse_weight,
                    "horse_weight_diff": horse_weight_diff,
                    "odds": odds,
                    "popularity": popularity,
                    "finish_position": finish_position,
                    "finish_time": finish_time,
                    "margin": margin,
                })
            except Exception:
                continue

        return entries

    def _parse_payouts(self, soup: BeautifulSoup, race_id: str) -> List[Dict[str, Any]]:
        """
        Parses payout tables into payout dictionaries.
        """
        payouts = []
        pay_tables = soup.find_all("table", class_=re.compile(r"pay_table"))
        for table in pay_tables:
            rows = table.find_all("tr")
            for row in rows:
                th = row.find("th")
                tds = row.find_all("td")
                if not th or len(tds) < 2:
                    continue

                th_text = th.get_text(strip=True)
                bet_type = None
                if "単勝" in th_text:
                    bet_type = "tansho"
                elif "複勝" in th_text:
                    bet_type = "fukusho"
                elif "枠連" in th_text:
                    bet_type = "wakuren"
                elif "馬連" in th_text:
                    bet_type = "umaren"
                elif "ワイド" in th_text:
                    bet_type = "wide"
                elif "馬単" in th_text:
                    bet_type = "umatan"
                elif "三連複" in th_text or "3連複" in th_text:
                    bet_type = "sanrenpuku"
                elif "三連単" in th_text or "3連単" in th_text:
                    bet_type = "sanrentan"

                if not bet_type:
                    continue

                comb_html = tds[0].decode_contents()
                pay_html = tds[1].decode_contents()

                comb_lines = [
                    re.sub(r"<[^>]+>", "", line).strip()
                    for line in re.split(r"<br\s*/?>", comb_html, flags=re.IGNORECASE)
                ]
                pay_lines = [
                    re.sub(r"<[^>]+>", "", line).strip().replace(",", "")
                    for line in re.split(r"<br\s*/?>", pay_html, flags=re.IGNORECASE)
                ]

                for comb, pay_str in zip(comb_lines, pay_lines):
                    clean_comb = re.sub(r"\s+", "", comb).replace("→", "-").replace("・", "-")
                    try:
                        payout_val = int(pay_str)
                        if clean_comb and payout_val > 0:
                            payouts.append({
                                "race_id": race_id,
                                "bet_type": bet_type,
                                "combination": clean_comb,
                                "payout": payout_val,
                            })
                    except ValueError:
                        continue

        return payouts

    def parse_race_result(self, html: str, race_id: str) -> Optional[Dict[str, Any]]:
        """
        Parses full race result HTML string into race metadata, entries, and payouts.
        """
        if not html:
            return None

        try:
            soup = BeautifulSoup(html, "html.parser")
            meta = self._parse_race_metadata(soup, race_id)
            entries = self._parse_entries(soup, race_id)
            payouts = self._parse_payouts(soup, race_id)

            meta["entries"] = entries
            meta["payouts"] = payouts
            return meta
        except Exception:
            return None

    def scrape_race(self, race_id: str, use_cache: bool = True) -> Optional[Dict[str, Any]]:
        """
        Fetches and parses a single race by race ID.
        """
        html = self.fetch_race_html(race_id, use_cache=use_cache)
        if not html:
            return None
        return self.parse_race_result(html, race_id)

    # ---- horse profile & pedigree -------------------------------------------------

    def parse_horse(self, profile_html: str, pedigree_html: Optional[str], horse_id: str) -> Optional[Dict[str, Any]]:
        """
        Builds a horse profile record. `pedigree_html` is optional — the profile page
        renders its own pedigree table in JavaScript, so the sire/dam names have to come
        from the separate /horse/ped/ page.
        """
        try:
            soup = BeautifulSoup(profile_html, "html.parser")
        except Exception:
            return None

        table = soup.find("table", class_=re.compile("db_prof_table"))
        if table is None:
            return None

        prof: Dict[str, str] = {}
        for tr in table.find_all("tr"):
            th, td = tr.find("th"), tr.find("td")
            if th and td:
                prof[th.get_text(strip=True)] = td.get_text(" ", strip=True)

        horse_name = None
        for elem in (soup.find("h1"), soup.title):
            if elem is None:
                continue
            candidate = re.split(r"[(（|]", elem.get_text(strip=True))[0].strip()
            if candidate:
                horse_name = candidate
                break

        trainer_raw = prof.get("調教師", "")
        stable_match = re.search(r"[（(]\s*(栗東|美浦|地方|海外)\s*[)）]", trainer_raw)

        record = {
            "horse_id": horse_id,
            "horse_name": horse_name or None,
            "birth_date": self._parse_jp_date(prof.get("生年月日")),
            "trainer_name": re.sub(r"[（(].*", "", trainer_raw).strip() or None,
            "stable": stable_match.group(1) if stable_match else None,
            "owner_name": prof.get("馬主") or None,
            "breeder": prof.get("生産者") or None,
            "origin": prof.get("産地") or None,
            "auction_price": self._parse_price(prof.get("セリ取引価格")),
            "sire": None, "sire_sire": None, "dam": None, "broodmare_sire": None,
        }
        if pedigree_html:
            record.update(self.parse_pedigree(pedigree_html))
        return record

    def parse_pedigree(self, html: str) -> Dict[str, Any]:
        """
        Reads the 5-generation pedigree table. Generations are encoded as rowspans:
        16 -> [sire, dam], 8 -> [sire's sire, sire's dam, dam's sire, dam's dam].
        """
        out = {"sire": None, "sire_sire": None, "dam": None, "broodmare_sire": None}
        try:
            table = BeautifulSoup(html, "html.parser").find("table", class_=re.compile("blood_table"))
        except Exception:
            return out
        if table is None:
            return out

        def names(rowspan: int) -> List[str]:
            cells = [td for td in table.find_all("td") if td.get("rowspan") == str(rowspan)]
            result = []
            for td in cells:
                link = td.find("a")
                result.append((link.get_text(strip=True) if link else td.get_text(" ", strip=True).split()[0]) or None)
            return result

        gen1, gen2 = names(16), names(8)
        if len(gen1) >= 2:
            out["sire"], out["dam"] = gen1[0], gen1[1]
        if len(gen2) >= 3:
            out["sire_sire"], out["broodmare_sire"] = gen2[0], gen2[2]
        return out

    @staticmethod
    def _parse_jp_date(text: Optional[str]) -> Optional[str]:
        """'2023年2月28日' -> '2023-02-28'"""
        m = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日", text or "")
        return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}" if m else None

    @staticmethod
    def _parse_price(text: Optional[str]) -> Optional[float]:
        """'4,200万円' -> 4200.0. '-' (not sold at auction) -> None."""
        m = re.search(r"([\d,]+)\s*万円", text or "")
        return float(m.group(1).replace(",", "")) if m else None

    def scrape_horse_and_save(self, horse_id: str, db: Session, with_pedigree: bool = True,
                              use_cache: bool = True) -> Optional[Horse]:
        """Scrapes one horse profile and upserts it into the horses table."""
        profile_html = self.fetch_horse_html(horse_id, use_cache=use_cache)
        if not profile_html:
            return None
        pedigree_html = self.fetch_pedigree_html(horse_id, use_cache=use_cache) if with_pedigree else None

        data = self.parse_horse(profile_html, pedigree_html, horse_id)
        if not data:
            return None

        horse = db.query(Horse).filter_by(horse_id=horse_id).first() or Horse(horse_id=horse_id)
        for key, value in data.items():
            setattr(horse, key, value)
        horse.scraped_at = datetime.now(timezone.utc)
        db.add(horse)
        return horse

    def scrape_race_and_save(
        self, race_id: str, db: Session, use_cache: bool = True
    ) -> Optional[Race]:
        """
        Scrapes a race and persists it to the database.
        """
        data = self.scrape_race(race_id, use_cache=use_cache)
        if not data:
            return None

        race = Race(
            id=data["id"],
            date=data["date"],
            race_course=data["race_course"],
            race_number=data["race_number"],
            race_name=data["race_name"],
            distance=data["distance"],
            surface=data["surface"],
            track_condition=data["track_condition"],
            weather=data["weather"],
            race_class=data.get("race_class"),
            race_condition=data.get("race_condition"),
            post_time=data.get("post_time"),
            lap_times=data.get("lap_times"),
            pace=data.get("pace"),
            status=data["status"],
            parser_version=PARSER_VERSION,
        )

        for e in data.get("entries", []):
            entry = RaceEntry(
                race_id=e["race_id"],
                horse_id=e["horse_id"],
                horse_name=e["horse_name"],
                post_position=e["post_position"],
                horse_number=e["horse_number"],
                jockey_name=e["jockey_name"],
                trainer_name=e.get("trainer_name", "未定"),
                sex=e["sex"],
                age=e["age"],
                handicap_weight=e["handicap_weight"],
                horse_weight=e.get("horse_weight", 0),
                horse_weight_diff=e.get("horse_weight_diff", 0),
                odds=e.get("odds", 1.0),
                popularity=e.get("popularity"),
                finish_position=e.get("finish_position"),
                finish_time=e.get("finish_time"),
                margin=e.get("margin"),
                final_600m=e.get("final_600m"),
                corner_positions=e.get("corner_positions"),
                prize_money=e.get("prize_money"),
                owner_name=e.get("owner_name"),
            )
            race.entries.append(entry)

        for p in data.get("payouts", []):
            payout = Payout(
                race_id=p["race_id"],
                bet_type=p["bet_type"],
                combination=p["combination"],
                payout=p["payout"],
            )
            race.payouts.append(payout)

        existing = db.query(Race).filter_by(id=data["id"]).first()
        if existing is not None:
            db.delete(existing)   # cascades to entries and payouts
            db.flush()

        db.add(race)
        db.commit()
        return race
