"""Collect Daily Star headlines about the 18 sampled firms."""

from __future__ import annotations

import csv
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import quote

import requests

BASE = Path(__file__).resolve().parent.parent
OUT = BASE / "data" / "news_raw.csv"
OUT.parent.mkdir(parents=True, exist_ok=True)

H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124 Safari/537.36"}

COMPANIES = {
    "GP": "Grameenphone",
    "BRACBANK": "BRAC Bank",
    "CITYBANK": "City Bank",
    "ISLAMIBANK": "Islami Bank",
    "EBL": "Eastern Bank",
    "PUBALIBANK": "Pubali Bank",
    "SQURPHARMA": "Square Pharmaceuticals",
    "BEXIMCO": "Beximco",
    "ACMELAB": "ACME Laboratories",
    "RENATA": "Renata",
    "WALTONHIL": "Walton",
    "LHBL": "LafargeHolcim",
    "BSRMLTD": "BSRM",
    "TITASGAS": "Titas Gas",
    "JAMUNAOIL": "Jamuna Oil",
    "DESCO": "DESCO",
    "POWERGRID": "Power Grid",
    "BATBC": "British American Tobacco Bangladesh",
}

START = datetime(2025, 9, 1, tzinfo=timezone.utc)
END = datetime(2026, 10, 28, tzinfo=timezone.utc)


def parse_feed(text: str) -> list[dict]:
    root = ET.fromstring(text)
    items = []
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        try:
            when = parsedate_to_datetime(item.findtext("pubDate") or "")
        except (TypeError, ValueError):
            continue
        title = re.sub(r"\s+-\s+The Daily Star\s*$", "", title).strip()
        items.append({"title": title, "link": link, "date": when})
    return items


def main() -> None:
    rows, seen = [], set()
    for ticker, name in COMPANIES.items():
        query = f'site:thedailystar.net "{name}" when:2y'
        url = "https://news.google.com/rss/search?q=" + quote(query) + "&hl=en-US&gl=US&ceid=US:en"
        try:
            feed = parse_feed(requests.get(url, headers=H, timeout=45).text)
            kept = [item for item in feed if START <= item["date"] <= END]
            print(f"{ticker:11s} {name:38s} items={len(feed):3d} kept={len(kept):3d}")
            for item in kept:
                key = (ticker, item["title"].lower())
                if key in seen:
                    continue
                seen.add(key)
                rows.append(
                    {
                        "ticker": ticker,
                        "company": name,
                        "date": item["date"].date().isoformat(),
                        "title": item["title"],
                        "link": item["link"],
                    }
                )
        except Exception as exc:  # noqa: BLE001
            print(f"{ticker}: failed ({exc})")
        time.sleep(1.2)

    rows.sort(key=lambda row: (row["ticker"], row["date"]))
    with OUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["ticker", "company", "date", "title", "link"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows)} headlines to {OUT}")


if __name__ == "__main__":
    main()
