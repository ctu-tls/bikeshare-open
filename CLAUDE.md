# Bikeshare demand capstone

Daily Capital Bikeshare counts, 2011-2012. We forecast `cnt` (total daily
rides) from calendar, weather, and lagged-demand features.

## Commands
- `make all && make test` - reproduce the headline result: ingest, features,
  train (writes `reports/metrics.json`), then the full suite.
- `make test` - run before claiming anything works. The hook runs only
  `tests/test_leakage.py`, so it is not a substitute.
- `scripts/` holds one-off experiments (e.g. `ex4_target_transform.py`). They
  stay out of `make all` and never write `reports/metrics.json`.

## Non-negotiable rules
- **Never** put `casual` or `registered` in a feature set: `casual +
  registered == cnt` exactly. Derive features via `feature_columns()`, which
  excludes `FORBIDDEN` (`src/config.py`); never hand-type a feature list.
- Every raw column is classified in `src/config.py`: `FORBIDDEN`, a feature,
  `RAW_CATEGORICAL_COLS` (string encoder inputs or date restatements), or
  `dteday`. `test_every_raw_column_is_classified` enforces it. Classify a new
  column with a one-line reason; never loosen the test.
- **Never** split randomly. Use `src.train.temporal_split`: train = 2011,
  valid = H1 2012, test = H2 2012. Select on validation; touch test once.
- Lag/rolling features: build after `reindex_to_calendar`, `.shift(1)` before
  aggregating, and add a named-date test in `tests/test_leakage.py`. A window
  longer than 7 days means raising `LAG_WARMUP`.
- Report the mean **and** persistence (yesterday's count) baselines with
  every model. A negative R^2 is a finding, not a bug to hide.
- **Never** write to `data/raw/` (no `make data --force`, no `cp`).
  `test_raw_csv_is_unmodified` pins its SHA-256 (`RAW_SHA256`). If it goes
  red, restore with `git checkout -- data/raw/bike_daily.csv`; never edit
  the hash to make it pass.
- Change `src/` with the Edit tool, never Bash (`sed`, `cp`, heredocs), so
  the PostToolUse leakage hook runs. The hook and deny rules see only Edit
  and Write.

## Skills
- `/new-feature <name>` - add a predictor test-first; record it in
  `docs/DECISIONS.md` with the validation delta.
- `/seed-fault <description>` - plant a deliberate fault with Edit, record
  diff, hook stderr and pytest tail in `docs/SEEDED_FAULTS.md`, and fix only
  when told "fix". Before saying a fault is fixed, confirm `git diff src/`
  matches HEAD; a planted fault once reached a commit.

## Style
- Standard library, pandas, scikit-learn only. No new dependencies without
  asking. Versions are pinned in `requirements.txt`.
- Modules are runnable: `python -m src.<module>` prints a one-line `OK ...`.
- Paths and constants live in `src/config.py`. Nothing is hardcoded twice.

## Gotchas
- `DATA_URL` is a mirror, NOT the UCI file: 728 rows from 2011-01-03, and
  2011-03-10 is missing. `weather` is `GOOD` / `MISTY` / `BAD`, not codes 1-4.
- Ridership grew ~65% from 2011 to 2012, so HGB on raw `cnt` cannot
  extrapolate (valid R^2 ~0.10). That is the headline, not an error. HGB on
  `cnt / cnt_roll_7` reaches 0.748 (`scripts/ex4_target_transform.py`).
- `cnt_roll_7_std` lifted ridge valid R^2 0.648 -> 0.722 but cut raw HGB
  0.219 -> 0.098. Re-check both models when changing it.
- 2012-10-29 (Hurricane Sandy, 22 rides) is in the test set.
