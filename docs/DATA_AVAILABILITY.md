# Data availability

## Sources

| Dataset | Source | Retrieved |
|---|---|---|
| Daily prices, 17 tickers | Dhaka Stock Exchange day-end archive, `https://old.dsebd.org/day_end_archive.php` | 27 October 2026 |
| Headlines, 474 items | The Daily Star financial coverage, `https://www.thedailystar.net/historical/financial` | 27 October 2026 |
| Article text, 86 items | The Daily Star article pages | 28 October 2026 |

## What is included

- **Prices:** `data/prices.csv` (8,143 stock-day observations). Public exchange data.
- **Headlines:** `data/news_raw.csv` (474 items with links). Short factual strings, included for
  research and verification.
- **Derived data:** Jev scores for headlines and articles, the event and placebo datasets, and all
  results. Released under CC BY 4.0.
- **Article metadata:** `articles_meta.csv` gives each article's URL, length, and fetch status.

## What is not included

- **Article bodies.** The Daily Star articles remain the newspaper's copyright and are not
  redistributed. URLs are provided so the text can be re-fetched with `code/collect_articles.py`.
- **The TypeSafe API key** used for scoring. Load it from `TYPESAFE_API_KEY`.
- **Raw HTML downloads**, which are large and unnecessary.

## Rebuilding

Live sources change; a rebuild may not return identical rows. The included CSVs are the version of
record for the manuscript.

## Privacy and ethics

Public information only. No human subjects, no personal data, no private filings. Article text may
quote company officials as reported in the press; this is public reporting, not data collected by the
author.

## Contact

Md Asiqur Rahman · `asiq@asiqrahman.com`
