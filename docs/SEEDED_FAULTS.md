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

## Fault 2: shift(1) removed from cnt_roll_7

Edit to `src/features.py`, in `build_features()`:

```diff
-    out["cnt_roll_7"] = out[TARGET].shift(1).rolling(LAG_WARMUP).mean()
+    out["cnt_roll_7"] = out[TARGET].rolling(LAG_WARMUP).mean()
```

PostToolUse hook stderr (`.claude/hooks/check_leakage.sh`):

```
[${CLAUDE_PROJECT_DIR}/.claude/hooks/check_leakage.sh]: Leakage tests failed after editing /Users/claire/dsc180/bikeshare-open/src/features.py:
[714 rows x 29 columns]

    def test_rolling_mean_excludes_today(feats):
        """cnt_roll_7 must be the mean of the 7 calendar days *before* today."""
        by_date = feats.set_index("dteday")[TARGET]
        date = feats.dteday.iloc[200]
        window = [date - pd.Timedelta(days=k) for k in range(1, 8)]
        if all(d in by_date.index for d in window):
            expected = sum(by_date[d] for d in window) / 7
>           assert feats.set_index("dteday").cnt_roll_7[date] == pytest.approx(expected)
E           assert np.float64(4389.0) == 4414.857142857143 ± 0.00441486
E             
E             comparison failed
E             Obtained: 4389.0
E             Expected: 4414.857142857143 ± 0.00441486

tests/test_leakage.py:58: AssertionError
=================================================================== short test summary info ====================================================================
FAILED tests/test_leakage.py::test_rolling_mean_excludes_today - assert np.float64(4389.0) == 4414.857142857143 ± 0.00441486
1 failed, 7 passed in 0.61s
```

`python -m pytest tests/ -q 2>&1 | tail -15`:

```
        date = feats.dteday.iloc[200]
        window = [date - pd.Timedelta(days=k) for k in range(1, 8)]
        if all(d in by_date.index for d in window):
            expected = sum(by_date[d] for d in window) / 7
>           assert feats.set_index("dteday").cnt_roll_7[date] == pytest.approx(expected)
E           assert np.float64(4389.0) == 4414.857142857143 ± 0.00441486
E             
E             comparison failed
E             Obtained: 4389.0
E             Expected: 4414.857142857143 ± 0.00441486

tests/test_leakage.py:58: AssertionError
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_rolling_mean_excludes_today - assert np.fl...
1 failed, 15 passed in 1.37s
```

Fix (reverts the fault; `src/features.py` matches the last commit again):

```diff
-    out["cnt_roll_7"] = out[TARGET].rolling(LAG_WARMUP).mean()
+    out["cnt_roll_7"] = out[TARGET].shift(1).rolling(LAG_WARMUP).mean()
```

Turns to fix: 1 (the "fix" request).

Final `make test`:

```
16 passed in 1.31s
```

## Fault 3: encode_weather no longer raises on unknown labels

Edit to `src/features.py`, in `encode_weather()` (the unknown-label check stays):

```diff
-        raise ValueError(f"unmapped weather labels: {sorted(unknown)}")
+        pass
```

PostToolUse hook (`.claude/hooks/check_leakage.sh`):

```
The hook ran and the leakage tests stayed green.
```

`python -m pytest tests/ -q 2>&1 | tail -15`:

```
................                                                         [100%]
16 passed in 1.49s
```

No test went red: the real data has only GOOD / MISTY / BAD, so the
missing raise is never exercised. Added a test, with the fault still planted.

New test in `tests/test_leakage.py` (plus `encode_weather` added to the
`from src.features import ...` line):

```python
def test_encode_weather_rejects_unknown_labels():
    """An unseen label must fail loudly. A silent NaN would be removed by
    dropna() and take the day with it -- the real data has no unknown
    labels today, so only a synthetic input can exercise this path."""
    with pytest.raises(ValueError, match="unmapped weather labels"):
        encode_weather(pd.Series(["GOOD", "STORMY"]))
```

PostToolUse hook on the test edit:

```
The hook did not fire.
```

(It matches only `src/*.py`; editing `tests/` does not trigger it. The new
test is in `tests/test_leakage.py`, so the hook will run it on future
`src/` edits.)

`python -m pytest tests/ -q 2>&1 | tail -15`, fault still planted:

```
=================================== FAILURES ===================================
__________________ test_encode_weather_rejects_unknown_labels __________________

    def test_encode_weather_rejects_unknown_labels():
        """An unseen label must fail loudly. A silent NaN would be removed by
        dropna() and take the day with it -- the real data has no unknown
        labels today, so only a synthetic input can exercise this path."""
>       with pytest.raises(ValueError, match="unmapped weather labels"):
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E       Failed: DID NOT RAISE ValueError

tests/test_leakage.py:25: Failed
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_encode_weather_rejects_unknown_labels - Fa...
1 failed, 16 passed in 1.68s
```

Fix (restores the raise; `src/features.py` matches the last commit again,
and the hook ran on this `src/` edit with no error):

```diff
-        pass
+        raise ValueError(f"unmapped weather labels: {sorted(unknown)}")
```

Turns to fix: 1 (the request to add the test and then fix; no literal
"fix" message, so that request counts as turn 1).

Final `make test`:

```
17 passed in 1.18s
```

### Re-planted with the new test in place

Same edit (`raise ValueError(...)` -> `pass`), made with the Edit tool. This
time the hook caught it. PostToolUse hook stderr:

```
[${CLAUDE_PROJECT_DIR}/.claude/hooks/check_leakage.sh]: Leakage tests failed after editing /Users/claire/dsc180/bikeshare-open/src/features.py:
F........                                                                                                                                                [100%]
=========================================================================== FAILURES ===========================================================================
__________________________________________________________ test_encode_weather_rejects_unknown_labels __________________________________________________________

    def test_encode_weather_rejects_unknown_labels():
        """An unseen label must fail loudly. A silent NaN would be removed by
        dropna() and take the day with it -- the real data has no unknown
        labels today, so only a synthetic input can exercise this path."""
>       with pytest.raises(ValueError, match="unmapped weather labels"):
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E       Failed: DID NOT RAISE ValueError

tests/test_leakage.py:25: Failed
=================================================================== short test summary info ====================================================================
FAILED tests/test_leakage.py::test_encode_weather_rejects_unknown_labels - Failed: DID NOT RAISE ValueError
1 failed, 8 passed in 0.74s
```

Restored the raise with the Edit tool; `make test` green again (see below).

## Fault 4: raw CSV overwritten via cp from Bash

Plan: corrupt one cell in a copy of `data/raw/bike_daily.csv` in `/tmp`, then
`cp` it over the raw file from the Bash tool, bypassing Edit/Write.

### Attempt 1: cnt changed, cp blocked by auto mode

The `/tmp` copy changed `cnt` on 2012-05-01 from 5740 to 5741 (one cell, 729
lines unchanged). The overwrite was refused:

```
$ cp /tmp/bike_daily.csv data/raw/bike_daily.csv
Permission to use Bash with command cp /tmp/bike_daily.csv data/raw/bike_daily.csv; echo "cp exit: $?" has been denied.
```

No permission prompt was shown: Claude Code's auto mode classifier blocked
it. The repo's own guards would **not** have stopped it:

- The PostToolUse hook in `.claude/settings.json` has matcher `Edit|Write`,
  so it never runs on a Bash call.
- The deny rules `Write(./data/raw/**)` and `Edit(./data/raw/**)` cover only
  the Write and Edit tools. The only Bash deny rule is `Bash(rm -rf:*)`.

So the protection came from the harness mode, not from anything checked into
the repo, and outside auto mode the overwrite could go through unchecked.
`data/raw/bike_daily.csv` was unchanged afterwards (SHA-256 `a6bed157...b5ad9dc`).

### Attempt 2: temp changed instead, cp to be run by hand

`cnt` was the wrong cell for testing the suite: `test_leakage_identity_holds`
checks `casual + registered == cnt` (653 + 5087 = 5740), so it would probably
have caught that edit. The `/tmp` copy was rewritten to change `temp`, which
no test checks against a known value:

```diff
-487,"2012-05-01","SPRING","2012","MAY","N","TUE",20.826651,35.618714,65.9583,10.458432,653,5087,5740,"Y","MISTY",486,6304
+487,"2012-05-01","SPRING","2012","MAY","N","TUE",21.826651,35.618714,65.9583,10.458432,653,5087,5740,"Y","MISTY",486,6304
```

```
$ shasum -a 256 /tmp/bike_daily.csv
feb94b217126afa397190814c76fca96bb42e02138492ab5497ba4ba95701ecd  /tmp/bike_daily.csv
```

The `cp` is to be run by hand from the user's shell, outside Claude Code.

### Corrupted file in place: the suite stays green

The user ran `cp /tmp/bike_daily.csv data/raw/bike_daily.csv` from their own
shell. No hook fired and no rule applied, because Claude Code was not involved.

```
$ shasum -a 256 data/raw/bike_daily.csv
feb94b217126afa397190814c76fca96bb42e02138492ab5497ba4ba95701ecd  data/raw/bike_daily.csv
```

`python -m pytest tests/ -q 2>&1 | tail -15` (the complete output):

```
.................                                                        [100%]
17 passed in 1.85s
```

No test sees the change. What would catch it: a content check on the raw file
itself. The row count, column set, calendar and leakage-identity tests all pass
because the file still has the right shape and `cnt` still equals
`casual + registered`. Only a hash (or a value-level snapshot) detects a
plausible-looking edit to a weather column.

### Mitigation: SHA-256 test

Expected hash added to `src/config.py` (constants live there, per CLAUDE.md):

```python
# SHA-256 of the raw CSV as committed. Any byte change to the raw file --
# including edits no other test can see, like one temp value -- fails
# tests/test_contract.py. Update this only after deliberately re-downloading.
RAW_SHA256 = "a6bed1577f6e4de56dcfae6d8315985073cc0ad3446c8c99ed60c86a0b5ad9dc"
```

New test in `tests/test_contract.py` (plus `import hashlib` and `RAW_SHA256`
added to the `from src.config import ...` line):

```python
def test_raw_csv_is_unmodified():
    """The raw file is an input, never an output. Hooks and deny rules only
    watch Edit/Write, so a `cp` from a shell can replace it silently; this
    catches any byte change, including ones no other test can see."""
    actual = hashlib.sha256(RAW.read_bytes()).hexdigest()
    assert actual == RAW_SHA256, f"{RAW.name} changed: sha256 {actual}"
```

The hook ran on the `src/config.py` edit and the leakage tests stayed green.
They do not include this test: it lives in `test_contract.py`, and the hook
runs only `test_leakage.py`.

`python -m pytest tests/ -q 2>&1 | tail -15`, corrupted file still in place:

```
        """The raw file is an input, never an output. Hooks and deny rules only
        watch Edit/Write, so a `cp` from a shell can replace it silently; this
        catches any byte change, including ones no other test can see."""
        actual = hashlib.sha256(RAW.read_bytes()).hexdigest()
>       assert actual == RAW_SHA256, f"{RAW.name} changed: sha256 {actual}"
E       AssertionError: bike_daily.csv changed: sha256 feb94b217126afa397190814c76fca96bb42e02138492ab5497ba4ba95701ecd
E       assert 'feb94b217126...ba4ba95701ecd' == 'a6bed1577f6e...0c86a0b5ad9dc'
E         
E         - a6bed1577f6e4de56dcfae6d8315985073cc0ad3446c8c99ed60c86a0b5ad9dc
E         + feb94b217126afa397190814c76fca96bb42e02138492ab5497ba4ba95701ecd

tests/test_contract.py:29: AssertionError
=========================== short test summary info ============================
FAILED tests/test_contract.py::test_raw_csv_is_unmodified - AssertionError: b...
1 failed, 17 passed in 1.37s
```

### Restored

```
$ git checkout -- data/raw/bike_daily.csv
$ shasum -a 256 data/raw/bike_daily.csv
a6bed1577f6e4de56dcfae6d8315985073cc0ad3446c8c99ed60c86a0b5ad9dc  data/raw/bike_daily.csv
```

Final `make test`:

```
18 passed in 1.09s
```

Remaining gap: the hash test only runs when someone runs `make test`. Nothing
runs it automatically after a Bash command or an out-of-band `cp`.
