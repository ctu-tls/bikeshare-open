# Forecasting daily Capital Bikeshare demand, 2011-2012

Target: `cnt`, total rides per day. The split is by date: train is 2011 (348 rows), validation is H1 2012 (182 rows) and test is H2 2012 (184 rows). Reproduce with `make all && make test`.

## Results

"Before" is `make all` on the unmodified-starter commit f9700b5 (reproduce with `git checkout f9700b5 && make all`), the 14-feature set. "After" adds `cnt_roll_7_std`, for 15 features (`reports/metrics.json`). All values are copied exactly from those files.

| Model | Features | Valid R^2 | Valid MAE | Test R^2 | Test MAE |
|---|---|---:|---:|---:|---:|
| baseline_mean | before | -0.9318 | 2002.2 | -2.1441 | 2847.7 |
| baseline_mean | after | -0.9318 | 2002.2 | -2.1441 | 2847.7 |
| baseline_persistence | before | 0.4507 | 900.6 | 0.5099 | 840.1 |
| baseline_persistence | after | 0.4507 | 900.6 | 0.5099 | 840.1 |
| ridge | before | 0.6475 | 832.9 | 0.5833 | 947.1 |
| ridge | after | 0.7224 | 700.4 | 0.6356 | 840.3 |
| hgb | before | 0.2185 | 1296.6 | -0.4975 | 1972.6 |
| hgb | after | 0.0977 | 1381.6 | -0.6959 | 2108.4 |

The baselines use no engineered features, so their rows are identical before and after.

**Negative R^2.** Four results score below zero, meaning they are worse than predicting each split's own mean:
- `baseline_mean` on validation and on test, both before and after. It predicts the 2011 average, and 2012 sits about 63% higher (mean daily rides 3,427 in 2011 against 5,600 in 2012).
- `hgb` on test, both before (-0.4975) and after (-0.6959).

**Models losing to a baseline.** This is a separate question from negative R^2:
- `hgb` loses to persistence on every split, metric and feature set. For example, after the change, validation R^2 is 0.0977 against 0.4507. It still beats the mean baseline everywhere.
- `ridge` loses to persistence on test MAE in both versions: 947.1 against 840.1 before, and 840.3 against 840.1 after. It beats persistence on test R^2, and on both validation metrics.
- No model loses to the mean baseline.

## Headline finding

A linear model on lagged demand forecasts 2012 well, and gradient-boosted trees do not. Ridge reaches validation R^2 0.722 (MAE 700) and test R^2 0.636 (MAE 840). That beats persistence's 0.451 / 901 on validation and 0.510 on test R^2, and ties it on test MAE. HGB, trained on the same 15 features, scores 0.098 on validation and -0.696 on test. The cause is extrapolation. Mean daily ridership rose from 3,427 in 2011 to 5,600 in 2012, and a tree can predict only values inside the range it saw in training. A ridge coefficient on `cnt_lag_1` or `cnt_roll_7` scales with the new level. My feature, `cnt_roll_7_std`, helps ridge (validation R^2 0.648 to 0.722, MAE 833 to 700) and hurts HGB (0.219 to 0.098), so it improves the model we would deploy and widens the gap to the model that was already failing.

## Exercise 4: target transformation

`scripts/ex4_target_transform.py` refits HGB with the same settings as `MODELS["hgb"]` (`random_state=0`, `max_iter=300`) on the same features and split, with four versions of the target. Each prediction is converted back to a count before scoring. The script is not part of `make all`.

| Target | Back-transform | Valid R^2 | Valid MAE |
|---|---|---:|---:|
| raw `cnt` | none | 0.0977 | 1381.6 |
| `log1p(cnt)` | `expm1` | -0.0282 | 1493.3 |
| `cnt - cnt_lag_1` | `+ cnt_lag_1` | 0.5642 | 885.8 |
| `cnt / cnt_roll_7` | `x cnt_roll_7` | **0.7483** | **685.5** |

The raw row matches HGB's validation numbers in `metrics.json` exactly, which confirms the setup is the same. Ratio was chosen on validation alone, with a margin of 0.18 R^2 over delta. **The test set was touched once**, for the ratio model only: test R^2 0.628, MAE 832.8 (`"test_touched": 1` in `reports/ex4_target_transform.json`). For comparison, persistence on test scores 0.510 / 840.1.

The transform is defensible, not just the winner of the comparison. Dividing by the trailing 7-day level makes the target scale-free, so the trees learn day-to-day patterns relative to the recent level, and the 2011-to-2012 growth no longer has to be extrapolated. `log1p` does not help because it compresses the level shift but does not remove it. The caveat is that ratio HGB beats persistence's test MAE by only 7 rides. **`reports/metrics.json` stays untransformed**: its hash was the same before and after the script ran, and the pipeline's HGB still trains on raw `cnt`. The ratio result is an experiment and has not replaced the headline model.

## Exercise 5: ridge vs persistence

Ridge is worth deploying over persistence. On test, persistence wins MAE by 0.2 rides (840.1 against 840.3), which is a practical tie on a typical day of about 5,600 rides. Ridge has the higher R^2, 0.636 against 0.510, and on validation it wins both metrics (0.722 / 700 against 0.451 / 901). R^2 is based on squared error, so a higher R^2 at equal MAE means fewer large misses. On test, ridge misses by more than 2,000 rides on 10 days against persistence's 17, and by more than 3,000 on 2 days against 6. Its RMSE is 1,051 against 1,219. Large misses matter most for rebalancing: a 3,000-ride error leaves docks empty or full across the system, while a 300-ride error does not. Persistence fails on weather swings. On the 67 test days where weather severity changed from the day before, its MAE is 1,141 against ridge's 973. It also fails on the rebound after Hurricane Sandy. On 2012-10-31 it predicted 1,096 (the storm-depressed 10-30 count) for a 5,566-ride day, an error of 4,470, where ridge missed by 995. Ridge has its own Sandy failures: on 10-29 (22 rides) it missed by 4,284, and on 10-30 by 3,109 against persistence's 1,074. Neither model can anticipate a storm. The counterargument: on the 117 test days with unchanged weather, persistence is more accurate (MAE 668 against 764), and it needs no training, features or monitoring.

The miss counts, RMSE, weather split and Sandy-week errors come from `scripts/ex5_check.py` (outside `make all`; writes nothing, including `reports/metrics.json`). It refits ridge exactly as `src.train` does. These test-set diagnostics were run after model selection, and they change no model or choice.

## Attribution

Agent model: qwen3.5:9b via Ollama (bikeshare-coder, num_ctx 65536), then Claude Opus 5.5 via my Claude Max plan.

**Model switches and tooling issues**
- qwen3.5:9b wrote the failing feature test for `cnt_roll_7_std` (`/new-feature` steps 1-2, commit `6e22749`). I added the `numpy` import by hand.
- At about 8:45 PM on Nov 25 I switched to Opus 5.5 through `.claude/settings.local.json`, because single local turns took about 10 minutes and one session hung.
- `agent/audit.py` ran with `AUDIT_MODEL=opus`.
- `make model` failed on Ollama 0.40.18 (`ollama create -f -`). I worked around it with a temporary Modelfile.

**Agent-generated components**
- Tests:
  - `test_cnt_roll_7_std_value_on_known_date` (qwen).
  - `test_every_raw_column_is_classified`, `test_encode_weather_rejects_unknown_labels` and `test_raw_csv_is_unmodified` (Opus).
- Feature code: `cnt_roll_7_std` in `src/features.py`, and `RAW_CATEGORICAL_COLS` and `RAW_SHA256` in `src/config.py`.
- The `/seed-fault` skill (`.claude/skills/seed-fault/SKILL.md`).
- The fault 1-4 write-ups in `docs/SEEDED_FAULTS.md`.
- The auditor report in `docs/AUDIT.md` (the `leakage-auditor` subagent).
- `scripts/ex4_target_transform.py` and `scripts/ex5_check.py`.
- Edits to `CLAUDE.md`.
- The draft of this report.

I also used Claude (Opus 5.5) in the Claude app as a planning assistant. It gave step-by-step guidance, prompts, commit messages and a draft of my audit verdict, which I edited.

**My decisions**

| Decision | Record |
|---|---|
| Chose `cnt_roll_7_std` and kept it despite the HGB drop | `docs/DECISIONS.md` (`cnt_roll_7_std` line), commit `7bbce55` |
| Chose a `temp`-value edit for fault 4 so the suite could not see it | commit `3815107`, `docs/SEEDED_FAULTS.md` fault 4 |
| Chose the four candidate transforms | `docs/DECISIONS.md` (HGB target transform line), commit `dd91ab7` |
| Took the pro-ridge position in Exercise 5 | `docs/DECISIONS.md` (Exercise 5 ridge vs persistence line) |
| Wrote the audit verdict | commit `f6c940b`, `docs/AUDIT.md` "My verdict" |

Every decision maps to a DECISIONS.md line or a commit.
