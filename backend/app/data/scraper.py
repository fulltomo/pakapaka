import re
import time
from typing import Optional, Dict, Any, List
import httpx
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from app.models.schema import Race, RaceEntry, Payout
from app.data.cache import HTMLCache


class NetkeibaScraper:
    """
    Scraper for netkeiba race data with local HTML caching and rate-limiting.
    """

    BASE_DB_URL = "https://db.netkeiba.com/race/{race_id}/"
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
        rate_limit_delay: float = 1.0,
        timeout: float = 10.0,
    ):
        self.cache = cache if cache is not None else HTMLCache()
        self.rate_limit_delay = rate_limit_delay
        self.timeout = timeout
        self._last_request_time: float = 0.0

    def fetch_race_html(self, race_id: str, use_cache: bool = True) -> Optional[str]:
        """
        Fetches HTML for a given race ID, checking cache first and rate-limiting live requests.
        """
        if use_cache and self.cache.has(race_id):
            return self.cache.get(race_id)

        # Rate limiting check
        elapsed = time.time() - self._last_request_time
        if elapsed < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - elapsed)

        url = self.BASE_DB_URL.format(race_id=race_id)
        try:
            with httpx.Client(timeout=self.timeout, headers=self.DEFAULT_HEADERS) as client:
                response = client.get(url)
                self._last_request_time = time.time()
                if response.status_code != 200:
                    return None
                content = response.text
                if use_cache:
                    self.cache.set(race_id, content)
                return content
        except Exception:
            return None

    def _parse_race_metadata(self, soup: BeautifulSoup, race_id: str) -> Dict[str, Any]:
        """
        Extracts race name, course, distance, surface, weather, track condition from HTML soup.
        """
        race_name = "レース"
        rname_elem = soup.find(class_="RaceName") or soup.find("h1") or soup.find(class_="racedata")
        if rname_elem:
            race_name = rname_elem.get_text(strip=True)

        # Race Course & Number
        race_course = "東京"
        race_number = 11
        rdata02 = soup.find(class_="RaceData02")
        if rdata02:
            rdata02_text = rdata02.get_text()
            course_match = re.search(r"(東京|中山|京都|阪神|新潟|中京|小倉|札幌|函館|福島)", rdata02_text)
            if course_match:
                race_course = course_match.group(1)
            num_match = re.search(r"(\d+)R", rdata02_text)
            if num_match:
                race_number = int(num_match.group(1))

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

            weather_match = re.search(r"天候:?([^\s/]+)", txt)
            if weather_match:
                weather = weather_match.group(1).strip(" :")

            cond_match = re.search(r"馬場:?([^\s/]+)", txt)
            if cond_match:
                track_condition = cond_match.group(1).strip(" :")
            else:
                cond_match2 = re.search(r"(?:芝|ダート|ダ):?\s*(良|稍重|重|不良)", txt)
                if cond_match2:
                    track_condition = cond_match2.group(1).strip()

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
            "status": "finished",
        }

    def _parse_entries(self, soup: BeautifulSoup, race_id: str) -> List[Dict[str, Any]]:
        """
        Parses race result table into list of entry dictionaries.
        """
        entries = []
        table = soup.find("table", class_=re.compile(r"race_table|nk_tb_common"))
        if not table:
            return entries

        rows = table.find_all("tr")[1:]  # Skip header
        for row in rows:
            cols = row.find_all(["td", "th"])
            if len(cols) < 8:
                continue

            try:
                # 0: 着順, 1: 枠番, 2: 馬番, 3: 馬名, 4: 性齢, 5: 斤量, 6: 騎手, 7: タイム
                finish_pos_text = cols[0].get_text(strip=True)
                finish_position = int(finish_pos_text) if finish_pos_text.isdigit() else None

                post_position_text = cols[1].get_text(strip=True)
                post_position = int(post_position_text) if post_position_text.isdigit() else 1

                horse_num_text = cols[2].get_text(strip=True)
                horse_number = int(horse_num_text) if horse_num_text.isdigit() else len(entries) + 1

                horse_link = cols[3].find("a")
                horse_name = cols[3].get_text(strip=True)
                horse_id = f"h_{horse_number}"
                if horse_link and horse_link.get("href"):
                    h_match = re.search(r"/horse/(\d+)/?", horse_link["href"])
                    if h_match:
                        horse_id = h_match.group(1)

                sex_age_text = cols[4].get_text(strip=True)
                sex = sex_age_text[0] if sex_age_text else "牡"
                age_match = re.search(r"\d+", sex_age_text)
                age = int(age_match.group(0)) if age_match else 4

                handicap_text = cols[5].get_text(strip=True)
                try:
                    handicap_weight = float(handicap_text)
                except ValueError:
                    handicap_weight = 57.0

                jockey_name = cols[6].get_text(strip=True)
                trainer_name = "未定"
                if len(cols) > 13:
                    trainer_name = cols[13].get_text(strip=True)

                finish_time = cols[7].get_text(strip=True) if len(cols) > 7 else None
                margin = cols[8].get_text(strip=True) if len(cols) > 8 else None

                # Odds & popularity
                odds = 1.0
                popularity = None
                if len(cols) > 9:
                    odds_text = cols[9].get_text(strip=True)
                    try:
                        odds = float(odds_text)
                    except ValueError:
                        odds = 1.0

                if len(cols) > 10:
                    pop_text = cols[10].get_text(strip=True)
                    if pop_text.isdigit():
                        popularity = int(pop_text)

                # Horse weight & diff
                horse_weight = 500
                horse_weight_diff = 0
                if len(cols) > 11:
                    weight_text = cols[11].get_text(strip=True)
                    w_match = re.search(r"(\d{3})(?:\(([+-]?\d+)\))?", weight_text)
                    if w_match:
                        horse_weight = int(w_match.group(1))
                        if w_match.group(2):
                            horse_weight_diff = int(w_match.group(2))

                entries.append({
                    "race_id": race_id,
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
            status=data["status"],
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

        db.add(race)
        db.commit()
        return race
