"""Exercise 4: does transforming the target rescue HGB?

HGB fails on 2012 because trees cannot extrapolate: ridership grew ~65%
from 2011 to 2012, and a tree trained on 2011 caps its predictions at the
2011 range. Each transform below re-expresses the target so the tree learns
something closer to scale-free, then maps predictions back to counts.

  raw    y = cnt
  log1p  y = log1p(cnt)               back: expm1(pred)
  delta  y = cnt - cnt_lag_1          back: pred + cnt_lag_1
  ratio  y = cnt / cnt_roll_7         back: pred * cnt_roll_7

cnt_lag_1 and cnt_roll_7 are features already (shifted, known before day d),
so using them to invert a prediction leaks nothing.

Selection is on VALIDATION only. Only the winner is scored on test, once.
Not part of `make all`; does not touch src/ or reports/metrics.json.

Run: python scripts/ex4_target_transform.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.metrics import mean_absolute_error, r2_score

from src.config import METRICS, PROCESSED, TARGET
from src.features import feature_columns
from src.train import MODELS, temporal_split

OUT = METRICS.parent / "ex4_target_transform.json"

# name -> (forward: frame -> transformed y, inverse: (frame, pred) -> cnt)
TRANSFORMS = {
    "raw": (lambda d: d[TARGET], lambda d, p: p),
    "log1p": (lambda d: np.log1p(d[TARGET]), lambda d, p: np.expm1(p)),
    "delta": (lambda d: d[TARGET] - d.cnt_lag_1, lambda d, p: p + d.cnt_lag_1.to_numpy()),
    "ratio": (lambda d: d[TARGET] / d.cnt_roll_7, lambda d, p: p * d.cnt_roll_7.to_numpy()),
}


def score(y_true, y_pred) -> dict:
    return {
        "r2": round(float(r2_score(y_true, y_pred)), 4),
        "mae": round(float(mean_absolute_error(y_true, y_pred)), 1),
    }


def fit(name: str, train: pd.DataFrame, cols: list[str]):
    forward, _ = TRANSFORMS[name]
    model = clone(MODELS["hgb"])  # same settings as src.train, fresh fit
    return model.fit(train[cols], forward(train))


def predict(name: str, model, part: pd.DataFrame, cols: list[str]) -> np.ndarray:
    _, inverse = TRANSFORMS[name]
    return inverse(part, model.predict(part[cols]))


def main() -> dict:
    df = pd.read_parquet(PROCESSED)
    cols = feature_columns(df)
    train, valid, test = temporal_split(df)

    models, valid_scores = {}, {}
    for name in TRANSFORMS:
        models[name] = fit(name, train, cols)
        valid_scores[name] = score(valid[TARGET], predict(name, models[name], valid, cols))
        print(f"valid  {name:6s}  R^2 {valid_scores[name]['r2']:7.4f}  MAE {valid_scores[name]['mae']:7.1f}")

    # Pick on validation R^2 alone; test has not been looked at yet.
    best = max(valid_scores, key=lambda n: valid_scores[n]["r2"])
    test_score = score(test[TARGET], predict(best, models[best], test, cols))
    print(f"best on validation: {best}")
    print(f"test   {best:6s}  R^2 {test_score['r2']:7.4f}  MAE {test_score['mae']:7.1f}"
          "  (test set touched once, for this transform only)")

    return {
        "model": "hgb",
        "hgb_params": MODELS["hgb"].get_params(),
        "n_features": len(cols),
        "features": cols,
        "n_train": len(train),
        "n_valid": len(valid),
        "n_test": len(test),
        "valid": valid_scores,
        "selected_on_valid": best,
        "test_selected_only": {best: test_score},
        "test_touched": 1,
    }


if __name__ == "__main__":
    res = main()
    OUT.write_text(json.dumps(res, indent=2))
    print(f"OK ex4_target_transform: best={res['selected_on_valid']} -> {OUT.relative_to(METRICS.parents[1])}")
