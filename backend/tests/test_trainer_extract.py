"""Guards race_id decoding and the SQL dataset extraction (filtering, ordering, columns)."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.schema import Base, Race, RaceEntry
from app.ml.trainer import ModelTrainer
from app.data.venues import decode_race_id, is_jra


@pytest.mark.parametrize("race_id, expected", [
    ("202105010812", ("東京", 12)),   # JRA: place 05
    ("202145010101", ("川崎", 1)),    # NAR: place 45 — used to be mislabelled 東京/11R
    ("202165010109", ("帯広(ば)", 9)),  # ban'ei
    ("202199010101", (None, 1)),      # unknown place code
    ("202105010899", ("東京", None)),  # race number out of range
    ("bad", (None, None)),
    ("", (None, None)),
])
def test_decode_race_id(race_id, expected):
    assert decode_race_id(race_id) == expected


def test_is_jra():
    assert is_jra("202105010812")
    assert not is_jra("202145010101")
    assert not is_jra("bad")


def _race(db, race_id, date, status, positions, course="東京"):
    db.add(Race(id=race_id, date=date, race_course=course, race_number=1, race_name="T",
                distance=1800, surface="芝", track_condition="良", weather="晴", status=status))
    for n, pos in enumerate(positions, start=1):
        db.add(RaceEntry(race_id=race_id, horse_id=f"h{race_id}{n}", horse_name=f"H{n}",
                         post_position=n, horse_number=n, jockey_name="武豊", trainer_name="矢作芳人",
                         sex="牡", age=4, handicap_weight=55.0, horse_weight=480, horse_weight_diff=0,
                         odds=3.0, popularity=n, finish_position=pos))


@pytest.fixture
def db():
    s = sessionmaker(bind=create_engine("sqlite://"))()
    Base.metadata.create_all(s.get_bind())
    _race(s, "r2", "2024-05-02", "finished", [1, 2, 3])
    _race(s, "r1", "2024-05-01", "finished", [1, 2, None])   # one entry not finished
    _race(s, "r3", "2024-05-03", "scheduled", [None, None])  # race not finished
    _race(s, "r4", "2024-05-04", "finished", [1, 2], course="大井")
    s.commit()
    return s


def test_extract_filters_and_orders(db):
    df = ModelTrainer()._extract_dataset_from_db(db)

    assert len(df) == 7, "scheduled races and null finish_position must be dropped"
    assert df["race_id"].tolist() == ["r1", "r1", "r2", "r2", "r2", "r4", "r4"], "chronological"
    for col in ("race_id", "race_date", "handicap_weight", "horse_weight", "sex", "age",
                "distance", "surface", "track_condition", "odds", "popularity",
                "jockey_name", "trainer_name", "finish_position"):
        assert col in df.columns, col


def test_race_courses_filter(db):
    df = ModelTrainer(race_courses=["東京"])._extract_dataset_from_db(db)
    assert set(df["race_course"]) == {"東京"}
    assert len(df) == 5, "the 大井 race must be excluded"

    with pytest.raises(ValueError):
        ModelTrainer(race_courses=["札幌"])._extract_dataset_from_db(db)
