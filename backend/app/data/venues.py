"""
netkeiba race_id decoding.

A 12-digit race_id encodes YYYY | place(2) | kai(2) | day(2) | race_no(2),
so course and race number are recoverable without parsing the page.
"""

from typing import Dict, Optional, Tuple

JRA_COURSES: Dict[str, str] = {
    "01": "札幌", "02": "函館", "03": "福島", "04": "新潟", "05": "東京",
    "06": "中山", "07": "中京", "08": "京都", "09": "阪神", "10": "小倉",
}

# 地方競馬 (NAR). "帯広(ば)" is ban'ei — a different sport (200m sled pulling).
NAR_COURSES: Dict[str, str] = {
    "30": "門別", "31": "北見", "32": "岩見沢", "33": "帯広", "34": "旭川",
    "35": "盛岡", "36": "水沢", "37": "上山", "38": "三条", "39": "足利",
    "40": "宇都宮", "41": "高崎", "42": "浦和", "43": "船橋", "44": "大井",
    "45": "川崎", "46": "金沢", "47": "笠松", "48": "名古屋", "49": "紀三井寺",
    "50": "園田", "51": "姫路", "52": "益田", "53": "福山", "54": "高知",
    "55": "佐賀", "56": "荒尾", "57": "中津", "58": "札幌(地)", "59": "函館(地)",
    "60": "新潟(地)", "61": "中京(地)", "65": "帯広(ば)",
}

PLACE_CODES: Dict[str, str] = {**JRA_COURSES, **NAR_COURSES}

UNKNOWN_COURSE = "不明"


def decode_race_id(race_id: str) -> Tuple[Optional[str], Optional[int]]:
    """
    Returns (course_name, race_number) decoded from a 12-digit race_id.
    Either element is None when the id does not carry usable information.
    """
    rid = str(race_id or "")
    if len(rid) != 12 or not rid.isdigit():
        return None, None

    course = PLACE_CODES.get(rid[4:6])
    number = int(rid[10:12])
    return course, (number if 1 <= number <= 12 else None)


def is_jra(race_id: str) -> bool:
    """True when the race_id belongs to a JRA (central) racecourse."""
    rid = str(race_id or "")
    return len(rid) == 12 and rid[4:6] in JRA_COURSES
