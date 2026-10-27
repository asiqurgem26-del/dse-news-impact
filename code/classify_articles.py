"""Score full article text with Jev (resumable)."""

from __future__ import annotations

import csv
import os
import time
from pathlib import Path

import requests

BASE = Path(__file__).resolve().parent.parent
DATA = BASE / "data"
API = "https://api.typesafe.ai/v1/systemone"
MODEL = "jev-1.14.0"
HEADERS = {
    "Authorization": f"Bearer {os.environ['TYPESAFE_API_KEY']}",
    "Content-Type": "application/json",
}

QUESTIONS = {
    "about_company": {
        "type": "noul",
        "instructions": "Does `article` report news specifically about `company`?",
        "criteria": {
            "true": "The article names the company or a subsidiary and reports something that happened to it.",
            "false": "The article is about the economy, the market, another firm, or an unconnected person.",
        },
    },
    "sentiment": {
        "type": "choice",
        "instructions": "Is `article` good news or bad news for `company`?",
        "criteria": {
            "good": "Favourable: higher profit or revenue, dividend, new contract, expansion, approval, upgrade.",
            "bad": "Unfavourable: lower profit or revenue, dividend cut, loss, penalty, shutdown, lawsuit, downgrade.",
            "neutral": "Reports information without a clear favourable or unfavourable implication.",
        },
    },
    "event_type": {
        "type": "choice",
        "instructions": "What kind of event does `article` describe?",
        "criteria": {
            "earnings": "Profit, revenue, or financial results.",
            "dividend": "Dividend, bonus share, or rights issue.",
            "contract": "New business, contract, partnership, or expansion.",
            "regulatory": "Regulator, tax, penalty, licence, or legal action.",
            "management": "Board, management, or ownership change.",
            "market": "Share price or trading activity without firm-specific news.",
            "other": "None of the above.",
        },
    },
    "quantitative": {
        "type": "noul",
        "instructions": "Does `article` report a specific financial figure (profit, revenue, dividend rate, or amount)?",
        "criteria": {
            "true": "The article contains at least one concrete number about the company's finances.",
            "false": "The article contains no concrete financial figure.",
        },
    },
}

FIELDS = [
    "ticker", "company", "date", "headline", "url", "body_chars",
    "about_p", "sentiment", "sent_conf", "p_good", "p_bad", "p_neutral",
    "event_type", "event_conf", "quant_p", "model", "input_tokens",
]


def score(row: dict) -> dict:
    article = row["body"][:6000]
    payload = {
        "model": MODEL,
        "state": {
            "company": row["company"],
            "ticker": row["ticker"],
            "date": row["date"],
            "headline": row["headline"],
            "article": article,
        },
        "questions": QUESTIONS,
    }
    response = requests.post(API, headers=HEADERS, json=payload, timeout=90)
    response.raise_for_status()
    body = response.json()
    answers = body["answers"]
    sentiment, event = answers["sentiment"], answers["event_type"]
    return {
        "ticker": row["ticker"],
        "company": row["company"],
        "date": row["date"],
        "headline": row["headline"],
        "url": row["url"],
        "body_chars": int(row["body_chars"]),
        "about_p": answers["about_company"]["noul"],
        "sentiment": sentiment["choice"],
        "sent_conf": sentiment["confidence"],
        "p_good": sentiment["probabilities"].get("good"),
        "p_bad": sentiment["probabilities"].get("bad"),
        "p_neutral": sentiment["probabilities"].get("neutral"),
        "event_type": event["choice"],
        "event_conf": event["confidence"],
        "quant_p": answers["quantitative"]["noul"],
        "model": body.get("model"),
        "input_tokens": body["usage"]["input_tokens"],
    }


def main() -> None:
    with (DATA / "articles.csv").open(newline="", encoding="utf-8") as handle:
        rows = [r for r in csv.DictReader(handle) if int(r["body_chars"]) >= 300]
    out = DATA / "articles_scored.csv"
    existing = []
    if out.exists():
        with out.open(newline="", encoding="utf-8") as handle:
            existing = list(csv.DictReader(handle))
    done = {(r["ticker"], r["headline"]) for r in existing}
    todo = [r for r in rows if (r["ticker"], r["headline"]) not in done]
    print(f"articles={len(rows)} scored={len(existing)} todo={len(todo)}")

    scored = list(existing)
    for index, row in enumerate(todo, 1):
        try:
            scored.append(score(row))
        except Exception as exc:  # noqa: BLE001
            print(f"{index} failed: {row['headline'][:50]} ({exc})")
            continue
        if index % 10 == 0:
            print(f"{index}/{len(todo)}", flush=True)
            with out.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=FIELDS)
                writer.writeheader()
                writer.writerows(scored)
        time.sleep(0.1)

    with out.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(scored)
    print(f"wrote {len(scored)} rows")


if __name__ == "__main__":
    main()
