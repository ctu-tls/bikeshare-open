"""Exercise 5 diagnostics: ridge vs persistence error profile.

Test-set diagnostics run AFTER model selection: refits ridge exactly as
src.train does, prints error counts, RMSE, the Sandy week and a weather-change
split. It changes no model or choice, is not part of `make all`, and writes
nothing (in particular not reports/metrics.json).

Run: python scripts/ex5_check.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np, pandas as pd
from sklearn.base import clone
from src.config import PROCESSED, TARGET
from src.features import feature_columns
from src.train import MODELS, temporal_split
df=pd.read_parquet(PROCESSED); cols=feature_columns(df); tr,va,te=temporal_split(df)
r=clone(MODELS['ridge']).fit(tr[cols],tr[TARGET])
for name,part in [('valid',va),('test',te)]:
    y=part[TARGET].to_numpy(); er=np.abs(y-r.predict(part[cols])); ep=np.abs(y-part.cnt_lag_1.to_numpy())
    print(name,'mae r/p',er.mean().round(1),ep.mean().round(1),'rmse r/p',np.sqrt((er**2).mean()).round(0),np.sqrt((ep**2).mean()).round(0))
    for t in [1500,2000,3000]: print('  |err|>',t,'ridge',(er>t).sum(),'pers',(ep>t).sum())
    print('  max err ridge',er.max().round(0),'pers',ep.max().round(0))
    if name=='test':
        t=part.assign(er=er,ep=ep,pred=r.predict(part[cols])).set_index('dteday')
        print(t.loc['2012-10-28':'2012-10-31',[TARGET,'cnt_lag_1','pred','er','ep']].round(0))
        ws=t.weather_severity.diff().abs()>0
        print('  weather-change days n',ws.sum(),'mae ridge',t.er[ws].mean().round(0),'pers',t.ep[ws].mean().round(0))
        print('  same-weather days mae ridge',t.er[~ws].mean().round(0),'pers',t.ep[~ws].mean().round(0))
