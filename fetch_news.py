#!/usr/bin/env python3
"""News agent: pulls RSS feeds for every section, cleans and dedupes them,
optionally asks Claude for a short briefing per section, and writes news.json
which the website (index.html) reads.

Run:  python fetch_news.py
Optional AI briefing: set the ANTHROPIC_API_KEY environment variable.
"""
import html
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path

import feedparser

HERE = Path(__file__).parent
MAX_PER_FEED = 25
MAX_PER_SECTION = 120
MAX_AGE_HOURS = 72
AI_MODEL = "claude-haiku-5-5"

TAG_RE = re.compile(r"<[^>]+>")
SPACE_RE = re.compile(r"\s+")


def clean(text, limit=280):
    text = html.unescape(TAG_RE.sub(" ", text or ""))
    text = SPACE_RE.sub(" ", text).strip()
    text = re.sub(r"\s+([.,;:!?])", r"\1", text)
    return text if len(text) <= limit else text[: limit - 1].rsplit(" ", 1)[0] + "…"


def entry_time(entry):
    for key in ("published_parsed", "updated_parsed"):
        t = entry.get(key)
        if t:
            return datetime(*t[:6], tzinfo=timezone.utc)
    return None


def entry_image(entry):
    for key in ("media_content", "media_thumbnail"):
        items = entry.get(key) or []
        for item in items:
            if item.get("url"):
                return item["url"]
    for link in entry.get("links", []):
        if link.get("type", "").startswith("image") and link.get("href"):
            return link["href"]
    return None


def fetch_feed(feed):
    try:
        parsed = feedparser.parse(
            feed["url"],
            agent="Mozilla/5.0 (compatible; PersonalNewsAgent/1.0)",
        )
        items = []
        for e in parsed.entries[:MAX_PER_FEED]:
            title = clean(e.get("title"), 200)
            link = e.get("link")
            if not title or not link:
                continue
            when = entry_time(e)
            items.append(
                {
                    "title": title,
                    "link": link,
                    "summary": clean(e.get("summary") or e.get("description")),
                    "source": feed["source"],
                    "image": entry_image(e),
                    "time": (when or datetime.now(timezone.utc)).isoformat(),
                }
            )
        print(f"  ok   {feed['source']:<22} {len(items)} items")
        return items
    except Exception as exc:  # one broken feed must never stop the rest
        print(f"  FAIL {feed['source']:<22} {exc}", file=sys.stderr)
        return []


def dedupe(items):
    """Drop stories with near-identical headlines (same story from many outlets
    is kept once, with the other outlets listed under 'also')."""
    kept = []
    for item in items:
        norm = item["title"].lower()
        match = None
        for k in kept:
            if SequenceMatcher(None, norm, k["_norm"]).ratio() > 0.82:
                match = k
                break
        if match:
            if item["source"] != match["source"] and item["source"] not in match["also"]:
                match["also"].append(item["source"])
        else:
            item["_norm"] = norm
            item["also"] = []
            kept.append(item)
    for k in kept:
        k.pop("_norm", None)
    return kept


def build_section(name, cfg):
    print(f"[{name}]")
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(fetch_feed, cfg["feeds"]))
    items = [i for group in results for i in group]
    cutoff = datetime.now(timezone.utc).timestamp() - MAX_AGE_HOURS * 3600
    items = [i for i in items if datetime.fromisoformat(i["time"]).timestamp() >= cutoff]
    items.sort(key=lambda i: i["time"], reverse=True)
    items = dedupe(items)[:MAX_PER_SECTION]
    return {"label": cfg["label"], "items": items}


def ai_briefing(sections):
    """Optional: one short briefing per section written by Claude."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return {}
    try:
        import anthropic
    except ImportError:
        print("anthropic package missing; skipping briefing", file=sys.stderr)
        return {}
    client = anthropic.Anthropic(api_key=key)
    out = {}
    for name, sec in sections.items():
        heads = "\n".join(f"- {i['title']} ({i['source']})" for i in sec["items"][:15])
        if not heads:
            continue
        try:
            msg = client.messages.create(
                model=AI_MODEL,
                max_tokens=400,
                messages=[
                    {
                        "role": "user",
                        "content": (
                            f"These are the latest {sec['label']} headlines. Write a "
                            "briefing of exactly 3 short bullet points (start each with '• ') "
                            "covering the most important developments. Use only the headlines "
                            "below, do not add facts.\n\n" + heads
                        ),
                    }
                ],
            )
            out[name] = msg.content[0].text.strip()
        except Exception as exc:
            print(f"briefing failed for {name}: {exc}", file=sys.stderr)
    return out


def main():
    config = json.loads((HERE / "feeds.json").read_text(encoding="utf-8"))
    sections = {n: build_section(n, c) for n, c in config["sections"].items()}
    briefings = ai_briefing(sections)
    for name, text in briefings.items():
        sections[name]["briefing"] = text
    data = {
        "updated": datetime.now(timezone.utc).isoformat(),
        "sections": sections,
    }
    (HERE / "news.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    total = sum(len(s["items"]) for s in sections.values())
    print(f"\nWrote news.json with {total} stories")


if __name__ == "__main__":
    t0 = time.time()
    main()
    print(f"Done in {time.time() - t0:.1f}s")
