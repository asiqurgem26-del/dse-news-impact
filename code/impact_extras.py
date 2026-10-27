"""Supplementary statistics for the event-impact paper."""

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

BASE = Path(__file__).resolve().parent.parent
R = BASE / "results"
events = pd.read_csv(R / "impact_events.csv")
placebo = pd.read_csv(R / "impact_placebo.csv")

out = {}
out["n_events"] = int(len(events))
out["n_placebo"] = int(len(placebo))
out["sd_car01"] = float(events["ma_car_01"].std(ddof=1))
out["mde_car01"] = float(2.802 * events["ma_car_01"].std(ddof=1) / math.sqrt(len(events)))

a = events["ma_car_01"].dropna().to_numpy()
b = placebo["ma_car_01"].dropna().to_numpy()
out["median_abs_news"] = float(np.median(np.abs(events["ma_abs_car01"].dropna())))
out["median_abs_placebo"] = float(np.median(np.abs(placebo["ma_abs_car01"].dropna())))

# Bootstrap difference in absolute CAR
rng = np.random.default_rng(7)
diffs = []
for _ in range(20000):
    da = rng.choice(events["ma_abs_car01"].dropna().to_numpy(), len(events), replace=True).mean()
    db = rng.choice(placebo["ma_abs_car01"].dropna().to_numpy(), len(placebo), replace=True).mean()
    diffs.append(da - db)
out["abs_diff_ci"] = [float(np.percentile(diffs, 2.5)), float(np.percentile(diffs, 97.5))]

# Good minus bad CAR01, bootstrap
g = events.loc[events.sentiment_h == "good", "ma_car_01"].dropna().to_numpy()
bad = events.loc[events.sentiment_h == "bad", "ma_car_01"].dropna().to_numpy()
gd = []
for _ in range(20000):
    gd.append(rng.choice(g, len(g), replace=True).mean() - rng.choice(bad, len(bad), replace=True).mean())
out["good_bad_diff"] = float(g.mean() - bad.mean())
out["good_bad_ci"] = [float(np.percentile(gd, 2.5)), float(np.percentile(gd, 97.5))]
out["good_bad_p_welch"] = float(stats.ttest_ind(g, bad, equal_var=False).pvalue)

# MDE for the good-bad difference
pooled = math.sqrt(((len(g) - 1) * g.var(ddof=1) + (len(bad) - 1) * bad.var(ddof=1)) / (len(g) + len(bad) - 2))
se = pooled * math.sqrt(1 / len(g) + 1 / len(bad))
out["mde_good_bad"] = float(2.802 * se)

# CAR windows for all three models
summary = json.loads((R / "impact_summary.json").read_text(encoding="utf-8"))
table = {}
for model in ["ma", "capm", "ca"]:
    table[model] = {}
    for window in ["car_m11", "car_01", "car_02", "car_05"]:
        d = summary["windows"][window][model]
        table[model][window] = {k: d[k] for k in ["n", "mean", "t", "p"]}
out["car_table"] = table

(R / "impact_extras.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
print(json.dumps(out, indent=2))
