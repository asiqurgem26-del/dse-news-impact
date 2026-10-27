# Did the news move the price?

Code, data, and manuscript for an event-impact study on the Dhaka Stock Exchange.

**Paper:** *Did the News Move the Price? Event-Study Evidence from 70 News Events on the Dhaka Stock
Exchange* — [manuscript/main.pdf](manuscript/main.pdf)

**Author:** Md Asiqur Rahman, Department of Banking and Insurance, University of Dhaka ·
`asiq@asiqrahman.com`

---

## The question and the answer

Did company-specific news produce an abnormal price reaction on the DSE?

**Not detectably, on average.** The mean cumulative abnormal return is indistinguishable from zero in
every window and every model, and absolute reactions on news days are not larger than on matched
non-news days.

| Test | Result |
|---|---|
| Mean $CAR[0,+1]$, market-adjusted | **−0.18%** ($p=0.64$) |
| Good vs. bad news, $CAR[0,+1]$ | +0.38% vs. −1.92% (2.30 pp, $p=0.09$) |
| Absolute $CAR[0,+1]$, news vs. non-news | 1.81% vs. 1.45% ($p=0.28$) |
| Median absolute $CAR$, news vs. non-news | 0.92% vs. 1.02% |
| Minimum detectable mean reaction | 1.08 pp |
| Minimum detectable good−bad gap | 2.69 pp |

The only robust pattern is a weak negative asymmetry for bad news. The public package reproduces these
numbers without network access or an API key.

---

## Reproduce in about ten seconds

```bash
pip install -r requirements.txt
python code/event_impact.py      # 70 events, 350 placebo days, all tables and figures
python code/impact_extras.py     # bootstrap intervals and minimum detectable effects
```

Expected: mean $CAR[0,+1]=-0.18\%$; good−bad $=2.30$ pp; $|CAR|$ news vs. placebo $=1.81\%$ vs.
$1.45\%$.

---

## Contents

```
manuscript/        paper (PDF + LaTeX), self-contained bibliography in refs/
code/              collection, article fetching, Jev scoring, event-impact analysis
data/              prices, headlines, article metadata and scores
results/           event and placebo datasets, impact summary, regressions
figures/           abnormal-return path, absolute-impact distribution
refs/              DOI-verified bibliography
docs/              data availability note
```

### Data files

| File | What it is |
|---|---|
| `data/prices.csv` | Daily prices, 17 tickers, 8,143 rows |
| `data/news_raw.csv` | 474 Daily Star headlines with links |
| `data/news_scored.csv` | Headline relevance, tone, event type |
| `data/articles_meta.csv` | Article URL, length, fetch status (no article text) |
| `data/articles_scored.csv` | Full-text Jev scores |

---

## Why the article text is not here

The 86 Daily Star articles were fetched and scored for the study, but the bodies remain the
newspaper's copyright and are **not redistributed**. Reproduction is unaffected:

- `articles_meta.csv` keeps every article URL;
- `articles_scored.csv` keeps the scores derived from the text;
- `code/collect_articles.py` re-fetches the bodies.

To rebuild the text from source:

```bash
python code/collect_articles.py     # resolves links, fetches bodies, writes data/articles.csv
```

This needs network access. Re-scoring needs a TypeSafe API key, which is not stored here.

---

## Data sources

| Source | Use | Terms |
|---|---|---|
| Dhaka Stock Exchange day-end archive | Daily prices | Public exchange data; cite the exchange |
| The Daily Star | Headlines and article links | Research use; article bodies not redistributed |

No personal data are included. See [docs/DATA_AVAILABILITY.md](docs/DATA_AVAILABILITY.md).

---

## Use of generative AI

The manuscript and analysis code were prepared with the assistance of an AI writing and coding tool.
The author specified the design, verified the price data, reviewed the scoring output, and takes full
responsibility for the estimates and interpretations. The manuscript carries a formal declaration.

---

## Citation

```bibtex
@misc{rahman2026impact,
  author = {Rahman, Md Asiqur},
  title  = {Did the News Move the Price? Event-Study Evidence from 70 News Events
            on the Dhaka Stock Exchange},
  year   = {2026},
  note   = {Manuscript and replication package, University of Dhaka},
  url    = {https://github.com/asiqurgem26-del/dse-news-impact}
}
```

## Licence

- Code: MIT — see [LICENSE](LICENSE).
- Manuscript and figures: CC BY 4.0 — see [LICENSE-TEXT](LICENSE-TEXT).
- Third-party data: subject to the terms of the Dhaka Stock Exchange and The Daily Star.
