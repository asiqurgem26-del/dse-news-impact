"""Event-impact analysis: did the news move the price?

For each company-specific news event, estimate abnormal returns under the three
models of the reference implementation (market-adjusted, CAPM, constant-adjusted)
over [-5,+5], and compare:

  1. signed reactions by tone (good vs bad) and by event type;
  2. absolute reactions on news days against matched non-news (placebo) days;
  3. cross-sectional regressions of signed and absolute CAR on news characteristics.

Outputs: results/impact_events.csv, results/impact_placebo.csv,
results/impact_summary.json, figures/impact_path.png, figures/impact_abs.png.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

BASE = Path(__file__).resolve().parent.parent
DATA = BASE / "data"
RESULTS = BASE / "results"
FIG = BASE / "figures"
for folder in (RESULTS, FIG):
    folder.mkdir(exist_ok=True)

MODELS = {"ma": "ar_ma", "capm": "ar_capm", "ca": "ar_ca"}
OFFSETS = list(range(-5, 6))
WINDOWS = {"car_m11": (-1, 1), "car_01": (0, 1), "car_02": (0, 2), "car_05": (0, 5)}

prices = pd.read_csv(DATA / "prices.csv", parse_dates=["date"]).dropna(subset=["close"])
wide = prices.pivot_table(index="date", columns="ticker", values="close", aggfunc="last").sort_index()
returns = wide.pct_change()
market = returns.mean(axis=1, skipna=True)
days = list(wide.index)
pos = {d: i for i, d in enumerate(days)}

news = pd.read_csv(DATA / "news_scored.csv").rename(columns={"title": "headline"})
news["about_p"] = pd.to_numeric(news["about_p"], errors="coerce")
news = news[news["about_p"] >= 0.70].copy()
news["date"] = pd.to_datetime(news["date"])
news["sent_conf"] = pd.to_numeric(news["sent_conf"], errors="coerce")
news = news.sort_values("sent_conf", ascending=False).drop_duplicates(["ticker", "date"]).sort_values("date")

articles = pd.read_csv(DATA / "articles_scored.csv").drop_duplicates(["ticker", "headline"])
articles = articles.rename(columns={"sentiment": "sentiment_b", "sent_conf": "sent_conf_b",
                                    "p_good": "p_good_b", "p_bad": "p_bad_b",
                                    "p_neutral": "p_neutral_b", "about_p": "about_p_b",
                                    "event_type": "event_type_b", "body_chars": "body_chars"})
articles = articles[["ticker", "headline", "sentiment_b", "sent_conf_b", "p_good_b", "p_bad_b",
                     "p_neutral_b", "about_p_b", "event_type_b", "quant_p", "body_chars"]]
news = news.merge(articles, on=["ticker", "headline"], how="left")


def estimate(ticker: str, i: int) -> dict | None:
    est = slice(i - 131, i - 11)
    y = returns[ticker].iloc[est].to_numpy()
    x = market.iloc[est].to_numpy()
    mask = np.isfinite(y) & np.isfinite(x)
    if mask.sum() < 60:
        return None
    xm = np.column_stack([np.ones(mask.sum()), x[mask]])
    (alpha, beta), *_ = np.linalg.lstsq(xm, y[mask], rcond=None)
    resid = y[mask] - (alpha + beta * x[mask])
    return {"alpha": float(alpha), "beta": float(beta),
            "sigma": float(np.std(resid, ddof=2)), "const_mean": float(np.nanmean(y))}


def abnormal_path(ticker: str, i: int, est: dict) -> dict:
    out = {}
    for offset in OFFSETS:
        j = i + offset
        r, m = returns[ticker].iloc[j], market.iloc[j]
        if not (np.isfinite(r) and np.isfinite(m)):
            out[offset] = {k: np.nan for k in MODELS}
            continue
        out[offset] = {
            "ma": float(r - m),
            "capm": float(r - (est["alpha"] + est["beta"] * m)),
            "ca": float(r - est["const_mean"]),
        }
    return out


def summarise(path: dict) -> dict:
    row = {}
    for key in MODELS:
        for wname, (a, b) in WINDOWS.items():
            vals = [path[o][key] for o in range(a, b + 1) if o in path]
            row[f"{key}_{wname}"] = float(np.nansum(vals)) if vals else np.nan
        row[f"{key}_ar0"] = path[0][key]
        row[f"{key}_abs_ar0"] = abs(path[0][key])
        row[f"{key}_abs_car01"] = abs(row[f"{key}_car_01"])
    return row


# ------------------------------------------------------------------ events
rows = []
for _, item in news.iterrows():
    ticker = item["ticker"]
    if ticker not in wide.columns:
        continue
    future = [d for d in days if d >= item["date"]]
    if not future:
        continue
    event_day = future[0]
    i = pos[event_day]
    if i < 140 or i + 6 >= len(days):
        continue
    est = estimate(ticker, i)
    if est is None:
        continue
    path = abnormal_path(ticker, i, est)
    if not np.isfinite(path[0]["ma"]):
        continue
    row = {
        "ticker": ticker,
        "company": item["company"],
        "news_date": item["date"].date().isoformat(),
        "event_date": event_day.date().isoformat(),
        "headline": item["headline"],
        "sentiment_h": item["sentiment"],
        "tone_h": float(item["p_good"]) - float(item["p_bad"]),
        "p_good_h": float(item["p_good"]),
        "p_bad_h": float(item["p_bad"]),
        "sent_conf_h": float(item["sent_conf"]),
        "about_p_h": float(item["about_p"]),
        "event_type_h": item["event_type"],
        "sentiment_b": item.get("sentiment_b"),
        "tone_b": (float(item["p_good_b"]) - float(item["p_bad_b"])) if pd.notna(item.get("p_good_b")) else np.nan,
        "sent_conf_b": item.get("sent_conf_b"),
        "quant_p": item.get("quant_p"),
        "body_chars": item.get("body_chars"),
        "event_type_b": item.get("event_type_b"),
        "pre20": float(np.nanprod(1 + returns[ticker].iloc[i - 20 : i]) - 1),
        "pre60vol": float(np.nanstd(returns[ticker].iloc[i - 60 : i], ddof=1)),
        "beta": est["beta"],
        "sigma": est["sigma"],
        "is_news": 1,
    }
    row.update(summarise(path))
    row["_path"] = json.dumps({str(o): path[o] for o in OFFSETS})
    rows.append(row)

events = pd.DataFrame(rows)
events.to_csv(RESULTS / "impact_events.csv", index=False)
print("events:", len(events))

# ------------------------------------------------------------------ placebo
rng = np.random.default_rng(42)
event_days: dict[str, list[int]] = {}
for _, row in events.iterrows():
    match = next(d for d in days if d.date().isoformat() == row["event_date"])
    event_days.setdefault(row["ticker"], []).append(pos[match])

placebo_rows = []
per_event = 5
for _, row in events.iterrows():
    ticker = row["ticker"]
    banned = set()
    for d in event_days.get(ticker, []):
        banned.update(range(d - 10, d + 11))
    candidates = [i for i in range(140, len(days) - 6) if i not in banned]
    if not candidates:
        continue
    for i in rng.choice(candidates, size=min(per_event, len(candidates)), replace=False):
        est = estimate(ticker, int(i))
        if est is None:
            continue
        path = abnormal_path(ticker, int(i), est)
        if not np.isfinite(path[0]["ma"]):
            continue
        r = {
            "ticker": ticker,
            "date": days[int(i)].date().isoformat(),
            "beta": est["beta"],
            "sigma": est["sigma"],
            "pre20": float(np.nanprod(1 + returns[ticker].iloc[int(i) - 20 : int(i)]) - 1),
            "pre60vol": float(np.nanstd(returns[ticker].iloc[int(i) - 60 : int(i)], ddof=1)),
            "is_news": 0,
        }
        r.update(summarise(path))
        placebo_rows.append(r)

placebo = pd.DataFrame(placebo_rows)
placebo.to_csv(RESULTS / "impact_placebo.csv", index=False)
print("placebo:", len(placebo))


# ------------------------------------------------------------------ statistics
def t_summary(x: np.ndarray) -> dict:
    x = x[np.isfinite(x)]
    if len(x) < 2:
        return {"n": int(len(x))}
    t, p = stats.ttest_1samp(x, 0.0)
    try:
        w, wp = stats.wilcoxon(x)
    except ValueError:
        w, wp = float("nan"), float("nan")
    se = x.std(ddof=1) / math.sqrt(len(x))
    return {"n": int(len(x)), "mean": float(x.mean()), "median": float(np.median(x)),
            "sd": float(x.std(ddof=1)), "se": float(se), "t": float(t), "p": float(p),
            "wilcoxon_p": float(wp),
            "ci_low": float(x.mean() - 1.96 * se), "ci_high": float(x.mean() + 1.96 * se)}


summary: dict = {"n_events": int(len(events)), "n_placebo": int(len(placebo)), "n_tickers": int(events.ticker.nunique())}
summary["windows"] = {w: {m: t_summary(events[f"{m}_{w}"].to_numpy()) for m in MODELS} for w in WINDOWS}
summary["ar0"] = {m: t_summary(events[f"{m}_ar0"].to_numpy()) for m in MODELS}


def group_test(frame: pd.DataFrame, col: str, group_col: str) -> dict:
    out = {}
    groups = [g for g in ["good", "bad", "neutral"] if (frame[group_col] == g).sum() >= 2]
    for g in groups:
        out[g] = t_summary(frame.loc[frame[group_col] == g, col].to_numpy())
    if "good" in groups and "bad" in groups:
        a = frame.loc[frame[group_col] == "good", col].dropna()
        b = frame.loc[frame[group_col] == "bad", col].dropna()
        t, p = stats.ttest_ind(a, b, equal_var=False)
        out["good_vs_bad"] = {"diff": float(a.mean() - b.mean()), "t": float(t), "p": float(p),
                              "n_good": int(len(a)), "n_bad": int(len(b))}
    return out


summary["by_tone_headline"] = {w: group_test(events, f"ma_{w}", "sentiment_h") for w in ["ar0", "car_m11", "car_01", "car_05"]}
summary["by_tone_article"] = {w: group_test(events.dropna(subset=["tone_b"]), f"ma_{w}", "sentiment_b") for w in ["ar0", "car_m11", "car_01", "car_05"]}

summary["by_event_type"] = {}
for kind, frame in events.groupby("event_type_h"):
    summary["by_event_type"][kind] = {
        "n": int(len(frame)),
        "mean_car01": float(frame["ma_car_01"].mean()),
        "mean_abs_car01": float(frame["ma_abs_car01"].mean()),
        "t_p": float(stats.ttest_1samp(frame["ma_car_01"], 0).pvalue) if len(frame) > 1 else None,
    }

# News vs placebo, absolute impact
summary["placebo"] = {}
for col in ["ma_abs_ar0", "ma_abs_car01", "capm_abs_car01", "ca_abs_car01", "ma_car_01"]:
    a = events[col].dropna().to_numpy()
    b = placebo[col].dropna().to_numpy()
    t, p = stats.ttest_ind(a, b, equal_var=False)
    u, up = stats.mannwhitneyu(a, b, alternative="two-sided")
    summary["placebo"][col] = {"news_mean": float(a.mean()), "placebo_mean": float(b.mean()),
                               "diff": float(a.mean() - b.mean()), "t": float(t), "p": float(p),
                               "mannwhitney_p": float(up)}


# ------------------------------------------------------------------ regressions
def ols_hc1(y: np.ndarray, X: np.ndarray, names: list[str]) -> dict:
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    n, k = X.shape
    xtx_inv = np.linalg.pinv(X.T @ X)
    h = np.einsum("ij,jk,ik->i", X, xtx_inv, X)
    meat = X.T @ (X * (resid**2 / (1 - h))[:, None])
    cov = xtx_inv @ meat @ xtx_inv * n / (n - k)
    se = np.sqrt(np.diag(cov))
    from math import lgamma

    def tp(t, df):
        # two-sided p via normal approximation for large df; exact t via betainc
        x = df / (df + t * t)
        a, b = df / 2.0, 0.5
        if x <= 0:
            return 1.0
        if x >= 1:
            return 0.0
        bt = math.exp(lgamma(a + b) - lgamma(a) - lgamma(b) + a * math.log(x) + b * math.log(1 - x))
        # continued fraction
        def cf(a, b, x):
            maxit, eps, fpmin = 200, 3e-12, 1e-300
            qab, qap, qam = a + b, a + 1, a - 1
            c, d = 1.0, 1 - qab * x / qap
            d = fpmin if abs(d) < fpmin else d
            d = 1 / d
            h = d
            for m in range(1, maxit + 1):
                m2 = 2 * m
                aa = m * (b - m) * x / ((qam + m2) * (a + m2))
                d = 1 + aa * d; d = fpmin if abs(d) < fpmin else d
                c = 1 + aa / c; c = fpmin if abs(c) < fpmin else c
                d = 1 / d; h *= d * c
                aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
                d = 1 + aa * d; d = fpmin if abs(d) < fpmin else d
                c = 1 + aa / c; c = fpmin if abs(c) < fpmin else c
                d = 1 / d
                delta = d * c; h *= delta
                if abs(delta - 1) < eps:
                    break
            return h
        p = bt * cf(a, b, x) / a if x < (a + 1) / (a + b + 2) else 1 - bt * cf(b, a, 1 - x) / b
        return float(p)

    return {name: {"coef": float(b), "se": float(s), "t": float(b / s) if s > 0 else None,
                   "p": tp(b / s, n - k) if s > 0 else None}
            for name, b, s in zip(names, beta, se)} | {"n": int(n), "r2": float(1 - resid.var() / y.var())}


# (a) pooled absolute impact: |CAR01| on news dummy + controls
pooled = pd.concat([
    events[["ma_abs_car01", "beta", "sigma", "pre60vol"]].assign(news=1),
    placebo[["ma_abs_car01", "beta", "sigma", "pre60vol"]].assign(news=0),
]).dropna()
X = np.column_stack([np.ones(len(pooled)), pooled["news"], pooled["beta"], pooled["sigma"], pooled["pre60vol"]])
summary["reg_abs_news"] = ols_hc1(pooled["ma_abs_car01"].to_numpy(), X,
                                  ["const", "news", "beta", "sigma", "pre60vol"])

# (b) signed reaction on tone, events only
ev = events.dropna(subset=["tone_h", "ma_car_01", "pre20", "pre60vol", "beta", "sigma"]).copy()
X = np.column_stack([np.ones(len(ev)), ev["tone_h"], ev["pre20"], ev["pre60vol"], ev["beta"], ev["sigma"]])
summary["reg_car_tone"] = ols_hc1(ev["ma_car_01"].to_numpy(), X,
                                  ["const", "tone", "pre20", "pre60vol", "beta", "sigma"])

# (c) absolute reaction on news characteristics, events only
ev2 = events.dropna(subset=["ma_abs_car01", "tone_h", "about_p_h", "beta", "sigma"]).copy()
ev2["abs_tone"] = ev2["tone_h"].abs()
ev2["log_body"] = np.log(ev2["body_chars"].clip(lower=1).fillna(1))
ev2["quant"] = pd.to_numeric(ev2["quant_p"], errors="coerce").fillna(0)
type_dummies = pd.get_dummies(ev2["event_type_h"], prefix="type", drop_first=True).astype(float)
X = np.column_stack([np.ones(len(ev2)), ev2["abs_tone"], ev2["about_p_h"], ev2["log_body"],
                     ev2["quant"], ev2["beta"], ev2["sigma"], type_dummies.to_numpy()])
names = ["const", "abs_tone", "relevance", "log_body", "quantitative", "beta", "sigma"] + list(type_dummies.columns)
summary["reg_abs_characteristics"] = ols_hc1(ev2["ma_abs_car01"].to_numpy(), X, names)

summary["descriptives"] = {
    "mean_abs_ar0_news": float(events["ma_abs_ar0"].mean()),
    "mean_abs_car01_news": float(events["ma_abs_car01"].mean()),
    "mean_abs_car01_placebo": float(placebo["ma_abs_car01"].mean()),
    "share_up_car01": float((events["ma_car_01"] > 0).mean()),
    "mean_car01": float(events["ma_car_01"].mean()),
}
(RESULTS / "impact_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

# ------------------------------------------------------------------ figures
def path_values(group: str):
    subset = events[events["sentiment_h"] == group]
    paths = [json.loads(p) for p in subset["_path"]]
    means = []
    for off in OFFSETS:
        vals = [p[str(off)]["ma"] for p in paths if str(off) in p and np.isfinite(p[str(off)]["ma"])]
        means.append(float(np.mean(vals)) if vals else np.nan)
    return means


plt.figure(figsize=(6.4, 4.2))
for group, colour in [("good", "#1a7f37"), ("bad", "#c62828")]:
    vals = path_values(group)
    plt.plot(OFFSETS, np.array(vals) * 100, marker="o", color=colour, label=f"{group} news")
plt.axhline(0, color="grey", linewidth=1)
plt.axvline(0, color="grey", linestyle="--", linewidth=1)
plt.xlabel("trading days from news")
plt.ylabel("average abnormal return (%)")
plt.title("Abnormal returns around news, by tone")
plt.legend()
plt.tight_layout()
plt.savefig(FIG / "impact_path.png", dpi=220)
plt.close()

plt.figure(figsize=(6.4, 4.0))
bins = np.linspace(0, 0.12, 30)
plt.hist(events["ma_abs_car01"].dropna() * 100, bins=bins, alpha=0.65, label="news days", color="#1f4e79", density=True)
plt.hist(placebo["ma_abs_car01"].dropna() * 100, bins=bins, alpha=0.55, label="non-news days", color="#c55a11", density=True)
plt.xlabel("|CAR[0,+1]| (%)")
plt.ylabel("density")
plt.title("Absolute reaction: news versus non-news days")
plt.legend()
plt.tight_layout()
plt.savefig(FIG / "impact_abs.png", dpi=220)
plt.close()

print(json.dumps({k: summary[k] for k in ["n_events", "n_placebo", "descriptives", "placebo"]}, indent=2))
print("wrote results/impact_*.csv, impact_summary.json, figures/impact_*.png")
