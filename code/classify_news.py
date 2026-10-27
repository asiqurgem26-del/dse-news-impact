"""Score headlines with Jev for the prediction study (resumable)."""

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
        "instructions": "Does `headline` report news specifically about `company`?",
        "criteria": {
            "true": "The headline names the company or a subsidiary and reports something that happened to it.",
            "false": "The headline is about the economy, the market, another firm, or an unconnected person.",
        },
    },
    "sentiment": {
        "type": "choice",
        "instructions": "Is `headline` good news or bad news for `company`?",
        "criteria": {
            "good": "Favourable: higher profit or revenue, dividend, new contract, expansion, approval, upgrade.",
            "bad": "Unfavourable: lower profit or revenue, dividend cut, loss, penalty, shutdown, lawsuit, downgrade.",
            "neutral": "Mentions the company without a clear favourable or unfavourable implication.",
        },
    },
    "event_type": {
        "type": "choice",
        "instructions": "What kind of event does `headline` describe?",
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
}

FIELDS = [
    "ticker", "company", "date", "title", "link", "about_p", "sentiment", "sent_conf",
    "p_good", "p_bad", "p_neutral", "event_type", "event_conf", "model", "input_tokens",
]


def score(row: dict) -> dict:
    payload = {
        "model": MODEL,
        "state": {k: row[k] for k in ["company", "ticker", "date", "title"]},
        "questions": QUESTIONS,
    }
    response = requests.post(API, headers=HEADERS, json=payload, timeout=60)
    response.raise_for_status()
    body = response.json()
    answers = body["answers"]
    sentiment, event = answers["sentiment"], answers["event_type"]
    return {
        **row,
        "about_p": answers["about_company"]["noul"],
        "sentiment": sentiment["choice"],
        "sent_conf": sentiment["confidence"],
        "p_good": sentiment["probabilities"].get("good"),
        "p_bad": sentiment["probabilities"].get("bad"),
        "p_neutral": sentiment["probabilities"].get("neutral"),
        "event_type": event["choice"],
        "event_conf": event["confidence"],
        "model": body.get("model"),
        "input_tokens": body["usage"]["input_tokens"],
    }


def main() -> None:
    with (DATA / "news_raw.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    out = DATA / "news_scored.csv"
    existing = []
    if out.exists():
        with out.open(newline="", encoding="utf-8") as handle:
            existing = list(csv.DictReader(handle))
    done = {(row["ticker"], row["title"]) for row in existing}
    todo = [row for row in rows if (row["ticker"], row["title"]) not in done]
    print(f"total={len(rows)} scored={len(existing)} todo={len(todo)}")

    scored = list(existing)
    for index, row in enumerate(todo, 1):
        try:
            scored.append(score(row))
        except Exception as exc:  # noqa: BLE001
            print(f"{index} failed: {row['title'][:50]} ({exc})")
            continue
        if index % 25 == 0:
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
