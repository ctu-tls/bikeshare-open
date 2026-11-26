# Decisions

One line per methodological decision: what you chose, why, and what it changed.
Agents append here via the `/new-feature` skill; you append here by hand.

- Exclude `casual`, `registered`: they sum to `cnt` exactly. Leaky model R^2 1.000 -> honest ridge 0.583.
- Exclude `cnt_2d_bfr`: a shipped 2-day lag we cannot test the alignment of. Build our own lags instead.
- Exclude `instant`, `yr`, `days_since_2011`: time indexes let a tree predict a flat constant past 2011 and a linear model extrapolate a trend we have no grounds for.
- Split 2011 / H1 2012 / H2 2012 by date. Test set touched once, after all feature work.
- Report mean and persistence baselines with every score. Persistence (test R^2 0.510, MAE 840) is within 0.07 R^2 of ridge and beats it on MAE; that caveat goes in the report.
- Add `cnt_roll_7_std` (std of cnt over the 7 calendar days before d, `.shift(1).rolling(7).std()` on the reindexed calendar): every input is a count from d-7..d-1, known before d. LAG_WARMUP stays 7, no extra rows lost. Validation: ridge R^2 0.648 -> 0.722 (+0.075), MAE 833 -> 700; hgb R^2 0.219 -> 0.098 (-0.121), MAE 1297 -> 1382.
- Classify raw string columns (holiday, workday, weather, weekday, mnth, season) as RAW_CATEGORICAL_COLS in config.py: encoder inputs or date restatements, not leaks; new test_every_raw_column_is_classified fails on any unclassified raw column (shown red by removing 'weather').
