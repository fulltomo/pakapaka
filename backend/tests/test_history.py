"""The as-of contract: a row's history features must never see its own race."""
import numpy as np
import pandas as pd
import pytest

from app.ml.history import add_history_features, HISTORY_FEATURES, MIN_RIDES


def _frame(rows):
    """rows: (race_id, date, horse_id, jockey, trainer, finish, odds)"""
    return pd.DataFrame(rows, columns=[
        "race_id", "race_date", "horse_id", "jockey_name", "trainer_name",
        "finish_position", "odds"])


def _horse_runs(finishes, horse="H1", jockey="J1", trainer="T1"):
    return _frame([(f"r{i:03d}", f"2024-01-{i + 1:02d}", horse, jockey, trainer, f, 5.0)
                   for i, f in enumerate(finishes)])


def test_expanding_rates_use_only_prior_races():
    out, _ = add_history_features(_horse_runs([1, 5, 1, 2]))

    assert out["horse_starts"].tolist() == [0, 1, 2, 3]
    np.testing.assert_allclose(out["horse_win_rate"], [np.nan, 1.0, 0.5, 2 / 3])
    np.testing.assert_allclose(out["horse_place_rate"], [np.nan, 1.0, 0.5, 2 / 3])
    np.testing.assert_allclose(out["horse_last_finish"], [np.nan, 1, 5, 1])
    np.testing.assert_allclose(out["horse_avg_finish3"], [np.nan, 1.0, 3.0, 7 / 3])


def test_days_since_last_race():
    df = _frame([("r1", "2024-03-01", "H1", "J1", "T1", 3, 4.0),
                 ("r2", "2024-03-21", "H1", "J1", "T1", 1, 4.0)])
    out, _ = add_history_features(df)
    np.testing.assert_allclose(out["horse_days_since_last"], [np.nan, 20])


def test_debut_runner_has_no_history():
    out, _ = add_history_features(_horse_runs([1]))
    assert out["horse_starts"].iloc[0] == 0
    for col in ("horse_win_rate", "horse_place_rate", "horse_last_finish",
                "horse_avg_finish3", "horse_avg_odds3", "horse_days_since_last"):
        assert pd.isna(out[col].iloc[0]), col


@pytest.mark.parametrize("new_finish", [1, 18])
def test_changing_the_last_result_changes_nothing(new_finish):
    """The decisive leak check: a race's own outcome must not reach any feature."""
    finishes = [1, 5, 1, 2, 7]
    base, _ = add_history_features(_horse_runs(finishes))

    altered = finishes[:-1] + [new_finish]
    after, _ = add_history_features(_horse_runs(altered))

    pd.testing.assert_frame_equal(base[HISTORY_FEATURES], after[HISTORY_FEATURES])


def test_result_is_independent_of_input_row_order():
    df = _horse_runs([1, 5, 1, 2])
    ordered, _ = add_history_features(df)
    shuffled, _ = add_history_features(df.sample(frac=1.0, random_state=0))
    pd.testing.assert_frame_equal(
        ordered[HISTORY_FEATURES].reset_index(drop=True),
        shuffled[HISTORY_FEATURES].reset_index(drop=True))


def test_jockey_rate_needs_a_minimum_sample():
    n = MIN_RIDES + 5
    df = _frame([(f"r{i:03d}", f"2024-01-{i + 1:02d}", f"H{i}", "J1", "T1", 1 if i % 4 == 0 else 6, 5.0)
                 for i in range(n)])
    out, _ = add_history_features(df)

    assert out["jockey_win_rate"].iloc[:MIN_RIDES].isna().all(), "too few prior rides -> NaN"
    assert out["jockey_win_rate"].iloc[MIN_RIDES:].notna().all()
    # Row MIN_RIDES sees exactly the first MIN_RIDES rides.
    expected = sum(1 for i in range(MIN_RIDES) if i % 4 == 0) / MIN_RIDES
    assert out["jockey_win_rate"].iloc[MIN_RIDES] == pytest.approx(expected)


def test_upcoming_race_gets_history_but_contributes_none():
    """A row with no finish_position (a race yet to run) still gets features."""
    df = _horse_runs([1, 2])
    df.loc[len(df)] = ("r099", "2024-02-01", "H1", "J1", "T1", np.nan, 5.0)
    out, _ = add_history_features(df)

    last = out.iloc[-1]
    assert last["horse_starts"] == 2
    assert last["horse_win_rate"] == pytest.approx(0.5)
    assert last["horse_last_finish"] == 2
