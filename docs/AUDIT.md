# Audit: teammate's bikeshare-open

- **Repo:** https://github.com/randonDsc/bikeshare-open (local checkout: `~/dsc180/audit-target`)
- **Commit range:** `408cf60` (Unmodified starter) .. `c260cfe` (HEAD), 10 commits, 10 files changed
- **Auditor:** `leakage-auditor` subagent (`.claude/agents/`), run 2026-11-25

## Auditor output (verbatim)

**Audit of /Users/claire/dsc180/audit-target, diff 408cf60..c260cfe (10 commits, 10 files)**

I did not modify the audited repo; `git status` there is still clean. All mutation experiments ran in a throwaway clone at /private/tmp/claude-501/-Users-claire-dsc180-bikeshare-open/f74f2ce0-aff3-46d6-96aa-809ebfee7948/scratchpad/wc, with a starter worktree at .../scratchpad/starter. The test suite at HEAD shows `20 passed`.

**Headline:** the current code has no live target leakage and no temporal-split violation. The feature set (15 columns) contains no FORBIDDEN column, and every lag and rolling feature uses `.shift(1)` or more before aggregating. The scaler is fitted on train rows only, and the split is by date. The problem is that the guards are weaker than the docs and commit messages say. Several realistic faults leave the suite green and the hook silent, and one of those faults gives validation R^2 = 0.9999.

Pipeline numbers at HEAD, which I reproduced by running `python -m src.features && python -m src.train` in the clone (672 rows; train/valid/test = 306/182/184):

| Model | Valid R^2 | Valid MAE | Test R^2 | Test MAE |
|---|---|---|---|---|
| baseline_mean | -0.6894 | 1877.3 | -1.7717 | 2659.6 |
| baseline_persistence | 0.4507 | 900.6 | 0.5099 | 840.1 |
| ridge | 0.6839 | 777.5 | 0.6239 | 879.3 |
| hgb | 0.2415 | 1296.6 | -0.4600 | 1952.4 |

These match the validation numbers in DECISIONS.md. I ran test-set numbers only as the auditor.

---

### Findings, most severe first

**1. A feature derived from casual + registered passes every test and every hook (HIGH; this gap already existed in the starter, and the new allowlist commit claims to close it)**
- **Where:** `src/features.py` (`feature_columns`, a denylist of numeric columns) and `tests/test_contract.py:23` (`test_no_unclassified_columns_in_raw`). Commit c260cfe and `docs/DECISIONS.md:17` say "a new column cannot enter the model without being explicitly registered".
- **What's wrong:** `ALLOWED_RAW_COLS` is only compared against the columns of the raw CSV. `feature_columns()` never uses it. Any column created inside `build_features` is a feature if it is numeric and its name is not in FORBIDDEN.
- **Failure scenario:** someone adds `out["riders_total"] = out.casual + out.registered`, or `out["cnt_next"] = out[TARGET].shift(-1).fillna(0)`, or `out["casual_x"] = out.casual * 1.0`.
  - The suite stays at `20 passed` and the hook exits 0.
  - With `riders_total`, ridge validation R^2 goes from 0.6839 to 0.9999.
- **How verified:** mutation script (`scratchpad/mut.py`) applied each edit to `build_features` and ran the full suite: all `20 passed`. Same result on starter 408cf60 (`14 passed`), so the gap predates the diff. The R^2 comes from refitting ridge with the extra column.
- **Fix:** make `feature_columns()` an allowlist (raw features in `FEATURES_RAW` plus an explicit `ENGINEERED_COLS` set in config). Add a test that every feature column is either `>= 1` shifted or a calendar/weather column. Add a leakage probe: for every feature, assert `abs(corr(feature, cnt)) < 0.999`, and assert a ridge fit on it alone does not reach R^2 > 0.99.

**2. Removing `reindex_to_calendar` from `build_features` is undetectable (HIGH; already in the starter, still open after the diff)**
- **Where:** `src/features.py:59`, `tests/test_leakage.py:34`, `tests/test_contract.py:53` and `:59`.
- **What's wrong:**
  - `test_calendar_is_complete_before_lagging` calls `reindex_to_calendar(raw)` directly, not `build_features`, so it only checks the helper, not whether the pipeline uses it.
  - `test_lags_are_true_calendar_lags` skips any row whose previous calendar day is missing, which is exactly the row after the 2011-03-10 gap.
  - The new `cnt_roll_28` and `cnt_lag_7` tests check only 2012-03-15, far from the gap.
  - The row-loss bound (`LAG_WARMUP*(1+missing_days)` = 56) is an upper bound, so losing fewer rows always passes.
- **Failure scenario:** replace line 59 with `out = df.sort_values("dteday").reset_index(drop=True).copy()`.
  - The output has 700 rows instead of 672. The 28 extra rows (2011-03-11 to 2011-04-07) carry lag-1, lag-7 and rolling values shifted by one calendar day.
  - Train grows from 306 to 334 rows and ridge validation R^2 moves from 0.6839 to 0.6705. Suite: `20 passed`.
- **How verified:** mutation script; then rebuilt features with `reindex_to_calendar` stubbed out and refitted.
- **Fix:**
  - Make the row-loss check exact: `assert lost == allowed_loss`.
  - Assert `feats.dteday.diff().dt.days` reflects the true calendar, i.e. no row whose previous calendar day is absent from `raw` survives.
  - Add a named-date test on 2011-04-08, the first surviving row after the gap: `cnt_lag_7 == cnt(2011-04-01)`.

**3. The baselines rule is enforced only by a dictionary-key check, which the hook doesn't run (MEDIUM; already in the starter)**
- **Where:** `tests/test_contract.py:86` (`test_persistence_baseline_is_reported` only asserts `"baseline_persistence" in MODELS`) and `.claude/hooks/check_leakage.sh:41` (runs only `tests/test_leakage.py`).
- **Failure scenario:** in `src/train.py` I added `if name.startswith("baseline"): continue` inside the `fit_and_score` loop.
  - The hook exits 0 and the suite shows `20 passed`.
  - `reports/metrics.json` now has no mean or persistence baseline. This matters because ridge loses to persistence on test MAE (879.3 vs 840.1), and that comparison silently disappears.
- **How verified:** ran the hook with a `src/train.py` payload, then `pytest`, then `python -m src.train` in the clone.
- **Fix:** test the output of `fit_and_score()` (or `metrics.json`) for keys `baseline_mean` and `baseline_persistence` with valid and test scores. Have the hook run `tests/` in full, or add `test_contract.py`.

**4. The `cnt_roll_28` keep decision is recorded without the baselines (MEDIUM, breaks a repo rule; the conclusion survives)**
- **Where:** `docs/DECISIONS.md:15-16`.
- **What's wrong:** it reports ridge and hgb validation deltas but not the mean or persistence baselines. CLAUDE.md requires both "alongside every model".
- **Effect:** the decision still holds. Persistence on validation is R^2 0.4507 / MAE 900.6 and ridge is 0.6839 / 777.5. But the record as written cannot show that.
- **How verified:** reran the pipeline (table above).
- **Fix:** add the baseline line to the entry.

**5. The partial-window rolling mean is not caught (MEDIUM)**
- **Where:** `src/features.py:83` and `tests/test_contract.py:59`.
- **Failure scenario:** change line 83 to `.rolling(28, min_periods=1)`.
  - `cnt_roll_28` becomes a mean of 1 to 27 days for rows after the start and after the gap, still labelled a 28-day mean.
  - Those rows now survive `dropna()` and enter training. Suite: `20 passed`.
- **Why it passes:** the only `cnt_roll_28` test checks one date (2012-03-15) with a full window, and the row-loss test is `<=`.
- **How verified:** mutation script.
- **Fix:** same exact-equality row-loss assertion as finding 2, plus a named-date check within 28 days after the gap.

**6. The leakage hook can't see edits to tests/ or to guards outside test_leakage.py (MEDIUM; already in the starter)**
- **Where:** `.claude/hooks/check_leakage.sh:36` (only `*src/*.py` paths) and `:41` (only `test_leakage.py`); `.claude/settings.json` matcher `Edit|Write`.
- **What's wrong:**
  - Editing `tests/test_leakage.py` to weaken a test exits 0 without running anything (verified: `tests-path=0`).
  - The hash guard, row-loss bound, allowlist, and baseline tests all live in `test_contract.py`, which the hook never runs.
  - Bash writes bypass the hook completely, which `docs/SEEDED_FAULTS.md` already acknowledges.
- **How verified:** fed JSON payloads to the hook in the clone.
- **Fix:** match `*src/*.py|*tests/*.py`, run `pytest tests/ -q`, and add a Stop hook running `make test`.

**7. The hash-guard test doesn't test what its name says, and the guard doesn't cover "every stage" (LOW)**
- **Duplicate test:** `tests/test_contract.py:117` (`test_hash_guard_error_message_shows_hashes`) is a copy of `:92`. It only matches `"integrity check failed"`, so removing both hashes from the error message would still pass.
  - **Fix:** `match=RAW_SHA256` and assert that the actual hash appears in the message.
- **Overstated claim:** `docs/DECISIONS.md:17` says any raw change "fails every stage". `src/train.py` reads `data/processed/features.parquet` and never calls `load_raw()`, so a tampered or stale parquet is trained on unchecked.
  - **Fix:** store the raw hash in parquet metadata at `make features` and check it in `fit_and_score`.
- **Hash is correct:** I downloaded `DATA_URL` and its SHA-256 equals `a6bed157...5ad9dc`, the same as the tracked file at 408cf60 and at HEAD. So the pinned hash is the genuine upstream file, not the tampered copy from seeded fault 4.

**8. LAG_WARMUP is no longer tied to the code (LOW, latent)**
- **Where:** `src/config.py:84` and `src/features.py:13`.
- **What's wrong:** `src/features.py` imports `LAG_WARMUP` but no longer uses it (lines 79-83 hard-code 7 and 28). The row-loss docstring at `tests/test_contract.py:59` still describes the 7-day accounting ("their union is 7 rows").
- **Current state:** the bound is exact today (lost 56 = allowed 56).
- **Failure scenario:** if `cnt_roll_28` is later dropped and LAG_WARMUP stays 28, the bound loosens by 42 rows. Up to 42 silent drops, such as BAD-weather days lost to an encoder NaN, would pass.
- **Fix:** derive LAG_WARMUP from a single `WINDOWS` constant used by `build_features`, and assert equality in the row-loss test.

**9. A broken failure message in the new `cnt_roll_28` test (LOW, the test still goes red)**
- **Where:** `tests/test_leakage.py:110` calls `TARGET_DATE.date()` on a string.
- **Effect:** when the test fails, it raises `AttributeError: 'str' object has no attribute 'date'` instead of showing got/expected values. I confirmed this with the no-shift and 27-day-window mutations.
- **Fix:** use `target_date.date()`.

---

### Results by category
- **Target leakage in the current feature set:** none. `feature_columns` returns temp, atemp, hum, windspeed, dayofweek, is_weekend, is_holiday, is_workday, month_sin, month_cos, weather_severity, cnt_lag_1, cnt_lag_7, cnt_roll_7, cnt_roll_28. The guard gap is finding 1.
- **Temporal-split violations:** none. `temporal_split` is by date, the StandardScaler is inside a pipeline fitted on train only, and all new aggregations shift first. The test set was not used for the keep decision as far as the code shows.
- **Unreported baselines:** both baselines are computed in `train.py`. The rule is broken in DECISIONS.md (finding 4) and enforced only weakly (finding 3).
- **Weakened tests and guards:** findings 1-3 and 5-9.

**Claims I checked and found correct:**
- `cnt_lag_7` uses `shift(7)`; the test goes red if `shift(LAG_WARMUP)` is restored.
- Removing `.shift(1)` from `cnt_roll_28` turns the suite red.
- The weather-encoder test catches a removed `raise`.
- The hook exits 2 on the "casual in feature_columns" fault (verified on macOS; I could not test Windows).

## My verdict

I read the test code the auditor cites in audit-target at c260cfe. I did not re-run its mutation experiments myself. Note: the auditor downloaded DATA_URL to confirm the pinned hash, which I did not ask for.

1. Arithmetic leak (casual + registered under a new column name): agree, and it changes a number. Validation R² would jump to about 1.0 (auditor measured 0.9999) while every test stays green, because test_no_forbidden_features only compares column names to FORBIDDEN. It is not live in his current code, so his reported numbers are unaffected; it is a gap in the suite. Fix: a test that no feature equals or nearly equals cnt on the training rows.

2. Removing reindex_to_calendar is undetected: agree, and it changes numbers slightly. The lags after the missing 2011-03-10 would be off by a day for a week of training rows. The calendar test checks reindex_to_calendar directly, not that build_features calls it. My own repo has the same gap.

3. c260cfe's claim that ALLOWED_RAW_COLS closes the gap: does not change any model number. It is about the accuracy of his commit message. I could not verify this one in the time I had, it does not change any number.

4. Findings 4-9: I did not assess each of these individually in the time I had; the three above are the ones I judged most likely to change a reported number.