"""Collect daily DSE prices for the prediction study.

One request per ticker to the exchange's day-end archive; a full date range is
returned in a single table (date, LTP, high, low, open, close).
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

import requests
import urllib3

urllib3.disable_warnings()

BASE = Path(__file__).resolve().parent.parent
OUT = BASE / "data" / "prices.csv"
OUT.parent.mkdir(parents=True, exist_ok=True)

URL = "https://old.dsebd.org/day_end_archive.php"
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124 Safari/537.36"}
START, END = "2024-06-01", "2026-10-27"

TICKERS = [
    "GP", "BRACBANK", "CITYBANK", "ISLAMIBANK", "EBL", "PUBALIBANK",
    "SQURPHARMA", "BEXIMCO", "ACMELAB", "RENATA", "WALTONHIL", "LHBL",
    "BSRMLTD", "TITASGAS", "JAMUNAOIL", "DESCO", "POWERGRID", "BATBC",
]


def clean(cell: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", cell)).strip()


def main() -> None:
    rows = []
    for ticker in TICKERS:
        try:
            response = requests.get(
                URL,
                params={"startDate": START, "endDate": END, "inst": ticker, "archive": "data"},
                headers=H,
                timeout=120,
                verify=False,
            )
        except Exception as exc:  # noqa: BLE001
            print(f"{ticker:11s} request failed: {exc}")
            continue

        table = None
        for candidate in re.findall(r"<table.*?</table>", response.text, re.S | re.I):
            head = re.search(r"<tr[^>]*>(.*?)</tr>", candidate, re.S | re.I)
            if head and "TRADING CODE" in clean(head.group(1)).upper():
                table = candidate
                break
        if table is None:
            print(f"{ticker:11s} no table")
            continue

        count = 0
        for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", table, re.S | re.I)[1:]:
            cells = [clean(c) for c in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S | re.I)]
            if len(cells) < 8:
                continue
            _, date, code, ltp, high, low, openp, close = cells[:8]
            rows.append(
                {
                    "date": date,
                    "ticker": code or ticker,
                    "ltp": ltp.replace(",", ""),
                    "high": high.replace(",", ""),
                    "low": low.replace(",", ""),
                    "open": openp.replace(",", ""),
                    "close": close.replace(",", ""),
                }
            )
            count += 1
        print(f"{ticker:11s} rows={count}")

    with OUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["date", "ticker", "ltp", "high", "low", "open", "close"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows)} rows to {OUT}")


if __name__ == "__main__":
    main()
