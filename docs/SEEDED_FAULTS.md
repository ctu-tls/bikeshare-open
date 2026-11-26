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
