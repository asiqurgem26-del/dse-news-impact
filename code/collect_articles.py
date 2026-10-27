"""Resolve company-specific headlines to Daily Star articles and extract body text.

Only headlines classified as company-specific (about_p >= 0.70) are fetched,
which keeps the crawl small and focused. Resumable via data/articles.csv.
"""

from __future__ import annotations

import csv
import re
import time
from pathlib import Path

import requests
from googlenewsdecoder import gnewsdecoder

BASE = Path(__file__).resolve().parent.parent
DATA = BASE / "data"
OUT = DATA / "articles.csv"
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124 Safari/537.36"}

BAD = ("addEventListener", "document.", "function(", "Main navigation", "window.", "var ", "{")

FIELDS = ["ticker", "company", "date", "headline", "url", "page_title", "body", "body_chars", "status"]


def extract(html: str) -> tuple[str, str]:
    title_match = re.search(r"<title>(.*?)</title>", html, re.S | re.I)
    page_title = re.sub(r"\s+", " ", title_match.group(1)).strip() if title_match else ""
    body_parts = []
    for paragraph in re.findall(r"<p[^>]*>(.*?)</p>", html, re.S | re.I):
        text = re.sub(r"<[^>]+>", " ", paragraph)
        text = re.sub(r"&nbsp;?", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        if len(text) < 80 or any(token in text for token in BAD):
            continue
        body_parts.append(text)
    return page_title, " ".join(body_parts)


def main() -> None:
    with (DATA / "news_scored.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    rows = [r for r in rows if float(r["about_p"]) >= 0.70]
    print("company-specific headlines:", len(rows))

    existing = []
    if OUT.exists():
        with OUT.open(newline="", encoding="utf-8") as handle:
            existing = list(csv.DictReader(handle))
    done = {(r["ticker"], r["headline"]) for r in existing}
    todo = [r for r in rows if (r["ticker"], r["title"]) not in done]
    print("already fetched:", len(existing), "todo:", len(todo))

    out_rows = list(existing)
    for index, row in enumerate(todo, 1):
        url, status, body, page_title = "", "decode_failed", "", ""
        try:
            decoded = gnewsdecoder(row["link"], interval=1)
            if decoded.get("success"):
                url = decoded["decoded_url"]
                response = requests.get(url, headers=H, timeout=45)
                status = str(response.status_code)
                if response.status_code == 200:
                    page_title, body = extract(response.text)
        except Exception as exc:  # noqa: BLE001
            status = f"error:{type(exc).__name__}"
        out_rows.append(
            {
                "ticker": row["ticker"],
                "company": row["company"],
                "date": row["date"],
                "headline": row["title"],
                "url": url,
                "page_title": page_title,
                "body": body,
                "body_chars": len(body),
                "status": status,
            }
        )
        if index % 10 == 0:
            print(f"{index}/{len(todo)}", flush=True)
            with OUT.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=FIELDS)
                writer.writeheader()
                writer.writerows(out_rows)
        time.sleep(0.4)

    with OUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(out_rows)
    good = sum(1 for r in out_rows if int(r["body_chars"]) >= 300)
    print(f"wrote {len(out_rows)} rows; with body >=300 chars: {good}")


if __name__ == "__main__":
    main()
