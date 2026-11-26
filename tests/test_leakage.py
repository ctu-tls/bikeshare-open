"""The tests that make the agent honest.

test_no_forbidden_features is the single most valuable test in this repo:
casual + registered == cnt exactly, so any model handed those columns
scores R^2 = 1.0 and looks brilliant while having learned nothing.
"""
import numpy as np
import pandas as pd
import pytest

from src.config import FORBIDDEN, TARGET
from src.features import build_features, encode_weather, feature_columns
from src.ingest import load_raw


@pytest.fixture(scope="module")
def feats():
    return build_features(load_raw())


def test_encode_weather_rejects_unknown_labels():
    """An unseen label must fail loudly. A silent NaN would be removed by
    dropna() and take the day with it -- the real data has no unknown
    labels today, so only a synthetic input can exercise this path."""
    with pytest.raises(ValueError, match="unmapped weather labels"):
        encode_weather(pd.Series(["GOOD", "STORMY"]))


def test_leakage_identity_holds(feats):
    """Documents *why* casual and registered are forbidden."""
    assert (feats.casual + feats.registered == feats[TARGET]).all()


def test_no_forbidden_features(feats):
    """Guards the gate, not the data: feature_columns() excludes FORBIDDEN by
    construction, so this cannot discover a *new* leaky column. What it
    catches is someone editing feature_columns() or FORBIDDEN -- which is
    exactly the fault the Step 7 hook demonstrates."""
    cols = set(feature_columns(feats))
    assert not (cols & FORBIDDEN), f"forbidden columns in feature set: {cols & FORBIDDEN}"


def test_lags_are_true_calendar_lags(feats):
    """cnt_lag_1 for date d must equal cnt on d-1, in calendar days."""
    by_date = feats.set_index("dteday")[TARGET]
    checked = 0
    for date, lag in feats.set_index("dteday").cnt_lag_1.items():
        prev = date - pd.Timedelta(days=1)
        if prev in by_date.index:
            assert lag == pytest.approx(by_date[prev]), f"bad lag at {date.date()}"
            checked += 1
    assert checked > 600, "too few rows actually verified"


def test_lag_is_not_the_target(feats):
    assert not (feats.cnt_lag_1 == feats[TARGET]).all()


def test_rolling_mean_excludes_today(feats):
    """cnt_roll_7 must be the mean of the 7 calendar days *before* today."""
    by_date = feats.set_index("dteday")[TARGET]
    date = feats.dteday.iloc[200]
    window = [date - pd.Timedelta(days=k) for k in range(1, 8)]
    if all(d in by_date.index for d in window):
        expected = sum(by_date[d] for d in window) / 7
        assert feats.set_index("dteday").cnt_roll_7[date] == pytest.approx(expected)


def test_cnt_roll_7_std_value_on_known_date():
    """Test that cnt_roll_7_std exists and has the correct value on 2011-06-15."""
    feats = build_features(load_raw())
    target_date = pd.Timestamp("2011-06-15")

    # Find the row for this date (accounting for gaps)
    idx = feats[feats.dteday == target_date].index
    if len(idx) != 1:
        pytest.fail(f"Expected exactly one row for 2011-06-15, found {len(idx)}")

    row = feats.loc[idx[0]]

    # Hand-compute: mean of cnt over the 7 calendar days before 2011-06-15
    by_date = feats.set_index("dteday")[TARGET]
    window_dates = [target_date - pd.Timedelta(days=k) for k in range(1, 8)]

    if all(d in by_date.index for d in window_dates):
        expected_std = np.std([by_date[d] for d in window_dates], ddof=1)

        # Assert that cnt_roll_7_std exists and matches hand-computed value
        assert hasattr(row, "cnt_roll_7_std"), "Feature 'cnt_roll_7_std' not found in feature set"
        actual_std = row.cnt_roll_7_std
        assert actual_std == pytest.approx(expected_std), (
            f"On {target_date.date()}, cnt_roll_7_std={actual_std:.4f} but expected "
            f"{expected_std:.4f}"
        )
    else:
        pytest.fail(f"Could not compute expected value: missing dates in window for 2011-06-15")


def test_no_missing_values(feats):
    assert feats[feature_columns(feats)].isna().sum().sum() == 0


def test_dates_are_sorted_and_unique(feats):
    assert feats.dteday.is_monotonic_increasing
    assert feats.dteday.is_unique
