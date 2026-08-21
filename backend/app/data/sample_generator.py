import random
from datetime import datetime, timedelta
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session

from app.models.schema import Race, RaceEntry, Payout


# Realistic Japanese horse racing reference data
HORSE_NAME_PREFIXES = [
    "ドウ", "イクイ", "リバティ", "コント", "グラン", "ソダ", "タイトル", "エフ",
    "ジャスティン", "スターズ", "ディープ", "ソング", "シュネル", "タスティ", "ソール",
    "ベラジオ", "レガ", "ジャンタル", "ステラ", "プログ", "セリ", "ナミュ", "メイケイ",
    "ガイア", "パンサ", "ウシュバ", "キタサン", "サトノ", "ダノン", "メイショウ",
    "アドマイヤ", "マツリダ", "トーセン", "スマート", "ゴールド", "エア", "エイシン",
    "シンボリ", "ダイワ", "テイエム", "ハーツ", "レッド", "ウイン", "モーリス",
    "クロノ", "ラヴズ", "エピファ", "ロード", "ロードカナ", "ホウオウ", "ジャック",
    "ルージュ", "ブエナ", "ウォッカ", "オルフェ", "ジェンティル", "アーモンド",
]

HORSE_NAME_SUFFIXES = [
    "デュース", "ノックス", "アイランド", "レイル", "アレグリア", "シ", "ホルダー",
    "フォーリア", "パレス", "オンアース", "ボンド", "ライン", "マイスター", "エーラ",
    "オリエンス", "オペラ", "レイラ", "マンタル", "ヴェローチェ", "ノーシス", "フォス",
    "ール", "エール", "フォース", "ラッサ", "テソーロ", "ブラック", "ダイヤモンド",
    "プレミアム", "キング", "クラウン", "ビクトリー", "トップ", "ドリーム", "エース",
    "スカイ", "スピリット", "スター", "フラッシュ", "ヒーロー", "チャンプ", "クイーン",
    "エンプレス", "ナイト", "カイザー", "フェニックス", "シャドウ", "ブレイク",
    "インパクト", "ジェネシス", "ネイチャ", "ドール", "オーラ", "ルシファー",
]

JOCKEYS = [
    "ルメール", "川田将雅", "武豊", "坂井瑠星", "横山武史", "戸崎圭太", "松山弘平",
    "岩田望来", "鮫島克駿", "西村淳也", "田辺裕信", "三浦皇成", "菅原明良", "津村明秀",
    "丹内祐次", "モレイラ", "レーン", "デムーロ", "藤岡佑介", "池添謙一", "横山典弘",
    "和田竜二", "幸英明", "吉田隼人", "北村友一", "団野大成", "佐々木大輔",
]

TRAINERS = [
    "矢作芳人", "中内田充", "手塚貴久", "木村哲也", "友道康夫", "国枝栄", "杉山晴紀",
    "池江泰寿", "藤原英昭", "須貝尚介", "宮田敬介", "堀宣行", "音無秀孝", "鹿戸雄一",
    "斉藤崇史", "高野友和", "松永幹夫", "武幸四郎", "田中博康", "奥村武",
]

RACE_COURSES = [
    "東京", "中山", "京都", "阪神", "新潟", "中京", "小倉", "札幌", "函館", "福島"
]

COURSE_DISTANCES = {
    "東京": [1400, 1600, 1800, 2000, 2400],
    "中山": [1200, 1600, 1800, 2000, 2200, 2500],
    "京都": [1200, 1400, 1600, 1800, 2000, 2200, 2400, 3000, 3200],
    "阪神": [1200, 1400, 1600, 1800, 2000, 2200, 2400],
    "中京": [1200, 1400, 1600, 2000, 2200],
    "新潟": [1000, 1200, 1400, 1600, 1800, 2000],
    "小倉": [1200, 1800, 2000],
    "札幌": [1200, 1500, 1800, 2000],
    "函館": [1200, 1800, 2000],
    "福島": [1200, 1800, 2000],
}

RACE_NAMES_BY_GRADE = [
    "3歳未勝利", "3歳以上1勝クラス", "3歳以上2勝クラス", "3歳以上3勝クラス",
    "オープン特別", "若葉ステークス", "プリンシパルステークス", "エプソムカップ",
    "毎日王冠", "京都大賞典", "日本ダービー", "有馬記念", "天皇賞(秋)",
    "ジャパンカップ", "皐月賞", "菊花賞", "桜花賞", "優駿牝馬(オークス)",
    "安田記念", "マイルチャンピオンシップ", "宝塚記念", "エリザベス女王杯",
    "スプリンターズステークス", "高松宮記念", "フェブラリーステークス",
    "チャンピオンズカップ", "ホープフルステークス", "大阪杯", "ヴィクトリアマイル",
]

SURFACES = ["芝", "ダート"]
TRACK_CONDITIONS = ["良", "稍重", "重", "不良"]
WEATHERS = ["晴", "曇", "雨", "小雨"]
SEXES = ["牡", "牝", "セ"]
MARGINS = ["ハナ", "アタマ", "クビ", "1/2", "3/4", "1", "1 1/4", "1 1/2", "1 3/4", "2", "2 1/2", "3", "3 1/2", "4", "大差"]


class SampleDataGenerator:
    """
    Generates realistic synthetic Japanese horse racing data (races, entries, payouts)
    and persists them to an SQLAlchemy session for development, testing, and ML training.
    """

    def __init__(self, seed: Optional[int] = None):
        self.rng = random.Random(seed)
        self._horse_id_counter = 1000
        self._race_id_counter = 1

    def _generate_horse_name(self) -> str:
        prefix = self.rng.choice(HORSE_NAME_PREFIXES)
        suffix = self.rng.choice(HORSE_NAME_SUFFIXES)
        name = prefix + suffix
        if len(name) > 9:  # JRA maximum horse name length is 9 katakana characters
            name = name[:9]
        return name

    def _assign_post_positions(self, num_horses: int) -> List[int]:
        """
        Assigns standard 1..8 frame (枠番) numbers to 1..N horses.
        """
        frames = []
        base = num_horses // 8
        rem = num_horses % 8
        # Outer frames take the remainder horses in JRA
        counts = [base] * 8
        for i in range(rem):
            counts[7 - i] += 1
        
        frame_list = []
        for frame_idx, count in enumerate(counts, start=1):
            frame_list.extend([frame_idx] * count)
        return frame_list

    def _generate_odds_distribution(self, num_horses: int) -> List[float]:
        """
        Generates realistic odds following a Power-law distribution with total overround ~ 1.20
        """
        # Generate raw strength / popularity scores
        raw_probs = [self.rng.uniform(0.1, 1.0) ** 2.2 for _ in range(num_horses)]
        raw_probs.sort(reverse=True)
        total_p = sum(raw_probs)
        norm_probs = [p / total_p for p in raw_probs]

        # JRA takeout is typically 20-25%, so sum(1/odds) approx 1.22
        overround = self.rng.uniform(1.18, 1.25)
        odds_list = []
        for p in norm_probs:
            adjusted_p = p / overround
            raw_odds = 1.0 / max(adjusted_p, 0.001)
            # Bound and round realistically
            if raw_odds < 1.1:
                rounded_odds = round(self.rng.uniform(1.1, 1.5), 1)
            elif raw_odds < 10.0:
                rounded_odds = round(raw_odds, 1)
            elif raw_odds < 50.0:
                rounded_odds = round(raw_odds * 2) / 2.0  # round to 0.5
            elif raw_odds < 100.0:
                rounded_odds = round(raw_odds)
            else:
                rounded_odds = round(min(raw_odds, 350.0))
            odds_list.append(float(rounded_odds))

        # Ensure sorted descending popularity (ascending odds)
        odds_list.sort()
        return odds_list

    def _simulate_finish_order(self, odds_list: List[float]) -> List[int]:
        """
        Simulates finish order based on strength derived from odds plus stochastic race noise.
        Returns a list of 0-based horse indices ordered by finish position (1st, 2nd, ...).
        """
        # Score = log(1/odds) + Gumbel noise (Plackett-Luce model for race ranking)
        scores = []
        for idx, odds in enumerate(odds_list):
            true_ability = 1.0 / odds
            # Gumbel noise for extreme-value distribution
            u = self.rng.uniform(0.0001, 0.9999)
            gumbel_noise = - ( - (1.0 / 0.8) * (self.rng.uniform(-0.5, 0.5)) )
            performance = true_ability * (1.0 + self.rng.gauss(0, 0.35))
            scores.append((performance, idx))

        scores.sort(key=lambda x: x[0], reverse=True)
        return [idx for _, idx in scores]

    def _generate_finish_time(self, distance: int, surface: str, track_condition: str, position: int) -> Tuple[str, str]:
        """
        Generates realistic race finish time (e.g. '1:58.4') and margin (e.g. '1 1/2').
        """
        # Base speed in m/s (approx 16.5 m/s for turf 2000m ~ 121s)
        base_speed = 16.6 if surface == "芝" else 15.8
        if track_condition in ["重", "不良"]:
            base_speed *= 0.97
        elif track_condition == "稍重":
            base_speed *= 0.99

        base_seconds = distance / base_speed
        # Position time lag
        lag = (position - 1) * self.rng.uniform(0.12, 0.35)
        total_seconds = base_seconds + lag + self.rng.gauss(0, 0.4)
        if total_seconds < 50.0:
            total_seconds = 50.0

        minutes = int(total_seconds // 60)
        seconds = total_seconds % 60
        if minutes > 0:
            time_str = f"{minutes}:{seconds:04.1f}"
        else:
            time_str = f"{seconds:04.1f}"

        if position == 1:
            margin_str = ""
        else:
            margin_str = self.rng.choice(MARGINS)

        return time_str, margin_str

    def _calculate_payouts(
        self,
        race_id: str,
        entries: List[RaceEntry],
        finish_order_entries: List[RaceEntry],
    ) -> List[Payout]:
        """
        Calculates standard JRA payout tickets for tansho, fukusho, umaren, wide.
        """
        payouts = []
        if len(finish_order_entries) < 3:
            return payouts

        first = finish_order_entries[0]
        second = finish_order_entries[1]
        third = finish_order_entries[2]

        # 1. 単勝 (Tansho)
        tansho_payout = max(100, int(round(first.odds * 100 / 10.0) * 10))
        payouts.append(
            Payout(
                race_id=race_id,
                bet_type="tansho",
                combination=str(first.horse_number),
                payout=tansho_payout,
            )
        )

        # 2. 複勝 (Fukusho) - Top 3 (or Top 2 if entries < 8)
        fukusho_count = 3 if len(entries) >= 8 else 2
        for e in finish_order_entries[:fukusho_count]:
            # Place odds typically 1.1x to 0.35 * win_odds
            p = max(110, int(round(max(1.1, e.odds * 0.35) * 10)) * 10)
            payouts.append(
                Payout(
                    race_id=race_id,
                    bet_type="fukusho",
                    combination=str(e.horse_number),
                    payout=p,
                )
            )

        # 3. 馬連 (Umaren) - 1st & 2nd sorted
        h1, h2 = min(first.horse_number, second.horse_number), max(first.horse_number, second.horse_number)
        umaren_comb = f"{h1}-{h2}"
        umaren_val = max(150, int(round(first.odds * second.odds * 28 / 10.0) * 10))
        payouts.append(
            Payout(
                race_id=race_id,
                bet_type="umaren",
                combination=umaren_comb,
                payout=umaren_val,
            )
        )

        # 4. ワイド (Wide) - 1-2, 1-3, 2-3 combinations
        combos = [
            (first.horse_number, second.horse_number, first.odds * second.odds * 10),
            (first.horse_number, third.horse_number, first.odds * third.odds * 10),
            (second.horse_number, third.horse_number, second.odds * third.odds * 12),
        ]
        for a, b, raw_pay in combos:
            wa, wb = min(a, b), max(a, b)
            w_pay = max(120, int(round(raw_pay / 10.0) * 10))
            payouts.append(
                Payout(
                    race_id=race_id,
                    bet_type="wide",
                    combination=f"{wa}-{wb}",
                    payout=w_pay,
                )
            )

        return payouts

    def generate_races(
        self,
        db: Session,
        count: int = 20,
        scheduled_count: int = 0,
        start_date: str = "2024-01-06",
    ) -> List[Race]:
        """
        Generates `count` finished races + `scheduled_count` scheduled races.
        Persists all entities to `db` and returns the generated list of `Race` models.
        """
        generated_races = []
        current_dt = datetime.strptime(start_date, "%Y-%m-%d")

        total_races = count + scheduled_count

        for i in range(total_races):
            is_scheduled = i >= count
            race_course = self.rng.choice(RACE_COURSES)
            distance = self.rng.choice(COURSE_DISTANCES.get(race_course, [1600, 1800, 2000]))
            surface = self.rng.choice(SURFACES)
            track_condition = self.rng.choice(TRACK_CONDITIONS)
            weather = self.rng.choice(WEATHERS)
            race_number = (i % 12) + 1

            if i > 0 and (i % 12) == 0:
                current_dt += timedelta(days=self.rng.choice([1, 6, 7]))

            date_str = current_dt.strftime("%Y-%m-%d")
            course_idx = RACE_COURSES.index(race_course) + 1
            race_id = f"{current_dt.year}{course_idx:02d}{(i // 12) + 1:02d}{(i % 12) + 1:02d}"

            race_name = self.rng.choice(RACE_NAMES_BY_GRADE)
            if race_number == 11 and self.rng.random() < 0.6:
                # Grade race on 11R
                race_name = self.rng.choice(RACE_NAMES_BY_GRADE[10:])

            race = Race(
                id=race_id,
                date=date_str,
                race_course=race_course,
                race_number=race_number,
                race_name=race_name,
                distance=distance,
                surface=surface,
                track_condition=track_condition,
                weather=weather,
                status="scheduled" if is_scheduled else "finished",
            )

            # Entries (8 to 18 horses)
            num_horses = self.rng.randint(8, 18)
            post_positions = self._assign_post_positions(num_horses)
            odds_list = self._generate_odds_distribution(num_horses)

            # Assign odds to horses randomly (not just horse #1 is favorite)
            horse_odds_perm = list(odds_list)
            self.rng.shuffle(horse_odds_perm)

            # Generate entries
            entries = []
            for h_num in range(1, num_horses + 1):
                h_idx = h_num - 1
                self._horse_id_counter += 1
                horse_id = f"h{self._horse_id_counter}"
                horse_name = self._generate_horse_name()
                jockey_name = self.rng.choice(JOCKEYS)
                trainer_name = self.rng.choice(TRAINERS)
                sex = self.rng.choice(SEXES)
                age = self.rng.randint(3, 7) if sex != "セ" else self.rng.randint(4, 8)
                handicap_weight = round(self.rng.choice([54.0, 55.0, 56.0, 57.0, 58.0]), 1)
                horse_weight = self.rng.randint(430, 540)
                horse_weight_diff = self.rng.randint(-10, 10)
                odds = horse_odds_perm[h_idx]

                entry = RaceEntry(
                    race_id=race_id,
                    horse_id=horse_id,
                    horse_name=horse_name,
                    post_position=post_positions[h_idx],
                    horse_number=h_num,
                    jockey_name=jockey_name,
                    trainer_name=trainer_name,
                    sex=sex,
                    age=age,
                    handicap_weight=handicap_weight,
                    horse_weight=horse_weight,
                    horse_weight_diff=horse_weight_diff,
                    odds=odds,
                    popularity=None,
                    finish_position=None,
                    finish_time=None,
                    margin=None,
                )
                entries.append(entry)

            # Popularity ranks based on odds
            entries_by_odds = sorted(entries, key=lambda e: e.odds)
            for pop_rank, entry in enumerate(entries_by_odds, start=1):
                entry.popularity = pop_rank

            # If finished, simulate results and payouts
            if not is_scheduled:
                entry_odds_list = [e.odds for e in entries]
                finish_order_indices = self._simulate_finish_order(entry_odds_list)

                ordered_entries = []
                for finish_pos, idx in enumerate(finish_order_indices, start=1):
                    finishing_entry = entries[idx]
                    finishing_entry.finish_position = finish_pos
                    ftime, margin = self._generate_finish_time(
                        distance=distance,
                        surface=surface,
                        track_condition=track_condition,
                        position=finish_pos,
                    )
                    finishing_entry.finish_time = ftime
                    finishing_entry.margin = margin
                    ordered_entries.append(finishing_entry)

                # Generate payouts
                payouts = self._calculate_payouts(race_id, entries, ordered_entries)
                race.payouts.extend(payouts)

            race.entries.extend(entries)
            db.add(race)
            generated_races.append(race)

        db.commit()
        return generated_races

    def generate_sample_races(self, num_races: int, db: Session) -> List[Race]:
        """
        Alias for compatibility with task brief interface specification.
        """
        return self.generate_races(db=db, count=num_races)
