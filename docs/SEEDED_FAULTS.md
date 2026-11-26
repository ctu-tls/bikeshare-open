# Seeded faults

## Feature test written before the feature (cnt_roll_7_std)

```
        window_dates = [target_date - pd.Timedelta(days=k) for k in range(1, 8)]
    
        if all(d in by_date.index for d in window_dates):
            expected_std = np.std([by_date[d] for d in window_dates], ddof=1)
    
            # Assert that cnt_roll_7_std exists and matches hand-computed value
>           assert hasattr(row, "cnt_roll_7_std"), "Feature 'cnt_roll_7_std' not found in feature set"
E           AssertionError: Feature 'cnt_roll_7_std' not found in feature set
E           assert False
E            +  where False = hasattr(dteday              2011-06-15 00:00:00\ninstant                           166.0\nseason                           SPRIN...        4891.0\ncnt_lag_7                        4401.0\ncnt_roll_7                  4605.571429\nName: 148, dtype: object, 'cnt_roll_7_std')

tests/test_leakage.py:81: AssertionError
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_cnt_roll_7_std_value_on_known_date - Asser...
1 failed, 7 passed in 0.34s
```

## Fault 1: forbidden column in feature_columns

Edit to `src/features.py`, in `feature_columns()`:

```diff
-    return [c for c in numeric if c not in FORBIDDEN]
+    return [c for c in numeric if c not in FORBIDDEN] + ["casual"]
```

PostToolUse hook stderr (`.claude/hooks/check_leakage.sh`):

```
[${CLAUDE_PROJECT_DIR}/.claude/hooks/check_leakage.sh]: Leakage tests failed after editing /Users/claire/dsc180/bikeshare-open/src/features.py:
__________________________________________________________________ test_no_forbidden_features __________________________________________________________________

feats =         dteday  instant  season      yr mnth holiday weekday  ...     month_sin  month_cos  weather_severity  cnt_lag_... -2.449294e-16   1.000000               1.0     1796.0      920.0  1531.428571      887.135250

[714 rows x 29 columns]

    def test_no_forbidden_features(feats):
        """Guards the gate, not the data: feature_columns() excludes FORBIDDEN by
        construction, so this cannot discover a *new* leaky column. What it
        catches is someone editing feature_columns() or FORBIDDEN -- which is
        exactly the fault the Step 7 hook demonstrates."""
        cols = set(feature_columns(feats))
>       assert not (cols & FORBIDDEN), f"forbidden columns in feature set: {cols & FORBIDDEN}"
E       AssertionError: forbidden columns in feature set: {'casual'}
E       assert not ({'atemp', 'casual', 'cnt_lag_1', 'cnt_lag_7', 'cnt_roll_7', 'cnt_roll_7_std', ...} & {'casual', 'cnt', 'cnt_2d_bfr', 'days_since_2011', 'instant', 'registered', ...})

tests/test_leakage.py:32: AssertionError
=================================================================== short test summary info ====================================================================
FAILED tests/test_leakage.py::test_no_forbidden_features - AssertionError: forbidden columns in feature set: {'casual'}
1 failed, 7 passed in 0.35s
```

`python -m pytest tests/ -q 2>&1 | tail -15`:

```
    def test_no_forbidden_features(feats):
        """Guards the gate, not the data: feature_columns() excludes FORBIDDEN by
        construction, so this cannot discover a *new* leaky column. What it
        catches is someone editing feature_columns() or FORBIDDEN -- which is
        exactly the fault the Step 7 hook demonstrates."""
        cols = set(feature_columns(feats))
>       assert not (cols & FORBIDDEN), f"forbidden columns in feature set: {cols & FORBIDDEN}"
E       AssertionError: forbidden columns in feature set: {'casual'}
E       assert not ({'atemp', 'casual', 'cnt_lag_1', 'cnt_lag_7', 'cnt_roll_7', 'cnt_roll_7_std', ...} & {'casual', 'cnt', 'cnt_2d_bfr', 'days_since_2011', 'instant', 'registered', ...})

tests/test_leakage.py:32: AssertionError
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_no_forbidden_features - AssertionError: fo...
1 failed, 15 passed in 1.18s
```

Fix (reverts the fault; `feature_columns()` matches the last commit again):

```diff
-    return [c for c in numeric if c not in FORBIDDEN] + ["casual"]
+    return [c for c in numeric if c not in FORBIDDEN]
```

Turns to fix: 1 (the "Fix fault 1" request).

Final `make test`:

```
16 passed in 1.06s
```
