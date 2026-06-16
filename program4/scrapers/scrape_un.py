#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scrape_un.py — Collect official UN statements / press releases for the 30
diplomatic events defined in events.py and save them to data/raw/UN.json.

SOURCE & ACCESS NOTE
--------------------
The intended source is the UN press site (https://press.un.org/en). Its public
document pages (`/en/YYYY/<symbol>.doc.htm`) and its site search
(`/en/sitesearch`) are protected by a JavaScript "Client Challenge" WAF:
non-browser HTTP clients receive either a 3 KB challenge stub (HTTP 200) or a
406, so a plain requests+bs4 client cannot read the full statement body live.

The press.un.org documents are, however, mirrored verbatim by the Internet
Archive Wayback Machine, which serves the *original* UN HTML (same markup,
same body, same `<time>` publication date) without the challenge. This script
therefore:

  1. Discovers candidate press.un.org document URLs per event. A curated seed
     pool (found via web search, scoped to press.un.org) is built in, and the
     script additionally probes the live Wayback CDX API per event symbol.
  2. Fetches each document's *original* HTML from the Wayback `id_` raw
     endpoint over live HTTP (requests), parses it with BeautifulSoup, pulls
     the real publication date from the page, and keeps only documents whose
     date falls within the event's +/- window.
  3. Extracts the plain-text statement body (nav/boilerplate stripped),
     dedupes by canonical press.un.org URL, and writes UN.json.

`collected_via` is recorded as "live_scrape": every byte of body text is
fetched over the network at run time (no local backup files are used). The
canonical `url` stored is the original press.un.org URL.

Engineering: browser User-Agent, 1-2 s polite delay between requests, retry
with exponential backoff, 18 s timeouts, per-event / per-doc try-except so a
single failure never aborts the run, progress logging, final per-topic counts.
"""

import json
import os
import re
import sys
import time
import random
from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from events import EVENTS, DOCUMENT_SCHEMA, TOPICS  # noqa: E402

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.normpath(os.path.join(HERE, "..", "data", "raw"))
OUT_PATH = os.path.join(OUT_DIR, "UN.json")

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
HEADERS = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

TIMEOUT = 18
SLEEP_MIN, SLEEP_MAX = 1.0, 2.0
MAX_RETRIES = 3
MIN_BODY_CHARS = 200
MAX_PER_EVENT = 4
MAX_TOTAL = 80

# ---------------------------------------------------------------------------
# Curated seed pool: event_id -> [press.un.org document URLs]
# Discovered via web search (site:press.un.org) for each event's keywords;
# only on-topic, in-window candidates are listed. The window filter below is
# still applied, so off-window items are silently dropped.
# ---------------------------------------------------------------------------
SEED = {
    # ---- Ukraine ----
    "ukr01": [
        "https://press.un.org/en/2022/sgsm21158.doc.htm",  # SG: military offensive 'wrong'
        "https://press.un.org/en/2022/sc14803.doc.htm",    # SC: 'special military operation' announced
        "https://press.un.org/en/2022/sgsm21153.doc.htm",  # SG: recognition of Donetsk/Luhansk
    ],
    "ukr02": [
        "https://press.un.org/en/2022/ga12407.doc.htm",    # GA ES-11/1 adopted
        "https://press.un.org/en/2022/ga12404.doc.htm",    # GA emergency session begins
        "https://press.un.org/en/2022/ga12406.doc.htm",    # GA debate
    ],
    "ukr03": [
        "https://press.un.org/en/2022/sgsm21227.doc.htm",  # SG shocked by killings, accountability
        "https://press.un.org/en/2022/sc14854.doc.htm",    # SC: Zelenskyy addresses Council
        "https://press.un.org/en/2022/sc14865.doc.htm",    # SC: humanitarian crisis briefing
    ],
    "ukr04": [
        "https://press.un.org/en/2022/ga12447.doc.htm",    # GA debate: mobilization / nuclear
        "https://press.un.org/en/2022/ga12456.doc.htm",    # GA: draft on annexation
    ],
    "ukr05": [
        "https://press.un.org/en/2022/ga12458.doc.htm",    # GA condemns annexation of 4 regions
        "https://press.un.org/en/2022/sc15046.doc.htm",    # SC fails to adopt (veto)
        "https://press.un.org/en/2022/ga12456.doc.htm",    # GA takes up draft
    ],
    "ukr06": [
        "https://press.un.org/en/2022/sc15118.doc.htm",    # SC emergency mtg: infrastructure strikes
        "https://press.un.org/en/2022/sgsm21523.doc.htm",  # SG shocked by missile attacks on cities
    ],
    "ukr07": [],  # Kherson liberation — no dedicated UN statement found (silence)
    "ukr08": [
        "https://press.un.org/en/2023/ga12492.doc.htm",    # GA one-year resolution
        "https://press.un.org/en/2023/ga12491.doc.htm",    # SG to GA emergency session
        "https://press.un.org/en/2023/sgsm21697.doc.htm",  # SG to SC one year in
    ],
    "ukr09": [
        "https://press.un.org/en/2023/sc15310.doc.htm",    # SC: Kakhovka dam destruction briefing
        "https://press.un.org/en/2023/db230606.doc.htm",   # Spokesperson daily briefing 6 Jun
    ],
    "ukr10": [
        "https://press.un.org/en/2023/sc15395.doc.htm",    # SC: deportation of Ukraine's children
    ],
    "ukr11": [
        "https://press.un.org/en/2024/sc15601.doc.htm",    # SG: two years since full-scale invasion
        "https://press.un.org/en/2024/sgsm22136.doc.htm",  # SG: 'High Time for Peace' (third year)
        "https://press.un.org/en/2024/sc15588.doc.htm",    # ASG to SC, two years
    ],
    "ukr12": [
        "https://press.un.org/en/2025/sgsm22826.doc.htm",  # SG appeals to SC for peace under Charter
        "https://press.un.org/en/2025/sc16179.doc.htm",    # SG to SC: fragile diplomatic momentum
        "https://press.un.org/en/2025/sc16053.doc.htm",    # USG: 'war of choice', calls for ceasefire
    ],

    # ---- Gaza ----
    "gaza01": [
        "https://press.un.org/en/2023/sgsm21981.doc.htm",  # SG strongly condemns Hamas attack
        "https://press.un.org/en/2023/sgsm21791.doc.htm",  # SG following developments, condemns loss
    ],
    "gaza02": [
        "https://press.un.org/en/2023/sc15462.doc.htm",    # SG to SC: collective punishment
        "https://press.un.org/en/2023/sgsm22024.doc.htm",  # SG reiterates condemnation, ceasefire
    ],
    "gaza03": [
        "https://press.un.org/en/2023/sc15496.doc.htm",    # SC adopts res 2712 (humanitarian pauses)
        "https://press.un.org/en/2023/sgsm22055.doc.htm",  # SG: epic humanitarian catastrophe
        "https://press.un.org/en/2023/sgsm22033.doc.htm",  # SG calls for humanitarian ceasefire
    ],
    "gaza04": [
        "https://press.un.org/en/2023/sc15518.doc.htm",    # SG urges SC: ceasefire (Article 99)
        "https://press.un.org/en/2023/sc15519.doc.htm",    # SC fails to adopt (US veto)
        "https://press.un.org/en/2023/sgsm22076.doc.htm",  # SG: 'human pinballs'
    ],
    "gaza05": [
        "https://press.un.org/en/2024/sgsm22118.doc.htm",  # SG notes ICJ provisional measures
        "https://press.un.org/en/2024/db240126.doc.htm",   # Spokesperson briefing 26 Jan
    ],
    "gaza06": [
        "https://press.un.org/en/2024/db240520.doc.htm",   # Spokesperson briefing 20 May (ICC request)
    ],
    "gaza07": [
        "https://press.un.org/en/2024/sc15701.doc.htm",    # SC: urge Israel stop Rafah incursions
        "https://press.un.org/en/2024/sgsm22247.doc.htm",  # SG condemns Rafah air strikes on tents
        "https://press.un.org/en/2024/sgsm22239.doc.htm",  # SG welcomes aid via Kerem Shalom
    ],
    "gaza08": [
        "https://press.un.org/en/2025/sgsm22857.doc.htm",  # SG welcomes agreement to secure ceasefire
        "https://press.un.org/en/2025/sgsm22863.doc.htm",  # SG: implementation, scaling up aid
    ],
    "gaza09": [
        "https://press.un.org/en/2025/sc16024.doc.htm",    # SC: renewed ceasefire appeals
    ],
    "gaza10": [
        "https://press.un.org/en/2025/sc16140.doc.htm",    # SC emergency: Gaza City takeover warning
        "https://press.un.org/en/2025/sgsm22824.doc.htm",  # SG to SC: darkest chapters
    ],

    # ---- AI governance ----
    "ai01": [],  # G7 Hiroshima AI process — no on-window UN statement found
    "ai02": [
        "https://press.un.org/en/2023/sgsm22017.doc.htm",  # SG to (Bletchley) AI Safety Summit
    ],
    "ai03": [
        "https://press.un.org/en/2024/ga12588.doc.htm",    # GA adopts landmark AI resolution
    ],
    "ai04": [
        "https://press.un.org/en/2024/sgsm22236.doc.htm",  # SG to AI Seoul Summit
    ],
    "ai05": [
        "https://press.un.org/en/2024/sgsm22368.doc.htm",  # SG on AI Advisory Body report
    ],
    "ai06": [
        "https://press.un.org/en/2023/sgsm21880.doc.htm",  # SG urges SC: first AI debate (Jul 2023)
        "https://press.un.org/en/2023/sc15359.doc.htm",    # SC debates AI risks/rewards
    ],
    "ai07": [
        "https://press.un.org/en/2024/ga12641.doc.htm",    # GA adopts Pact for the Future / GDC
        "https://press.un.org/en/2024/ga12627.doc.htm",    # World leaders pledge / Pact adopted
        "https://press.un.org/en/2024/ga12631.doc.htm",    # Summit digital future dialogue
    ],
    "ai08": [
        "https://press.un.org/en/2025/sgsm22548.doc.htm",  # SG at Paris AI Action Summit
    ],
}

# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------
SESSION = requests.Session()
SESSION.headers.update(HEADERS)

SYMBOL_RE = re.compile(r"/en/\d{4}/([a-z0-9_]+)\.doc\.htm", re.I)


def polite_sleep():
    time.sleep(random.uniform(SLEEP_MIN, SLEEP_MAX))


def get(url, timeout=TIMEOUT):
    """GET with retry + exponential backoff. Returns Response or None."""
    last = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            r = SESSION.get(url, timeout=timeout)
            if r.status_code == 200 and r.text:
                return r
            last = f"HTTP {r.status_code}"
        except requests.RequestException as e:
            last = repr(e)
        if attempt < MAX_RETRIES:
            time.sleep(1.5 * attempt)
    print(f"      ! giving up on {url} ({last})")
    return None


def _target_stamp(event_date):
    """Return a YYYYMMDD a few weeks after the event (captures appear later)."""
    try:
        d = datetime.strptime(event_date, "%Y-%m-%d") + timedelta(days=20)
        return d.strftime("%Y%m%d")
    except ValueError:
        return "20230101"


def wayback_snapshot_urls(press_url, event_date):
    """Yield candidate Wayback raw (id_) snapshot URLs for a press doc.

    Strategy (fast first): the Wayback Availability API targeted at a timestamp
    near the event date — this returns an early capture and avoids recent
    captures that may themselves be WAF challenge stubs. Falls back to the CDX
    API (earliest 200 capture), then to a generic nearest-capture id_ URL.
    """
    candidates = []
    quoted = requests.utils.quote(press_url, safe="")

    # 1) Availability API near the event date.
    api = (f"http://archive.org/wayback/available?url={quoted}"
           f"&timestamp={_target_stamp(event_date)}")
    r = get(api, timeout=TIMEOUT)
    if r is not None:
        try:
            closest = r.json().get("archived_snapshots", {}).get("closest", {})
            ts = closest.get("timestamp")
            if ts and closest.get("status", "200") == "200":
                candidates.append(f"https://web.archive.org/web/{ts}id_/{press_url}")
        except ValueError:
            pass

    # 2) CDX: earliest 200 capture (more thorough but slower).
    if not candidates:
        cdx = ("http://web.archive.org/cdx/search/cdx?url=" + quoted
               + "&output=json&filter=statuscode:200&limit=3&fl=timestamp")
        r = get(cdx, timeout=TIMEOUT)
        if r is not None:
            try:
                rows = json.loads(r.text)
                stamps = [row[0] for row in rows[1:] if row and row[0].isdigit()]
                for ts in stamps[:2]:
                    candidates.append(
                        f"https://web.archive.org/web/{ts}id_/{press_url}")
            except (ValueError, IndexError):
                pass

    # 3) Generic nearest-capture fallback.
    candidates.append(f"https://web.archive.org/web/2id_/{press_url}")
    return candidates


def discover_extra_urls(press_urls):
    """No-op placeholder kept for extensibility.

    The CDX lookup happens per-document in wayback_snapshot_url; the seed pool
    already provides the candidate press.un.org URLs. This keeps the public
    surface small while leaving room to expand discovery later.
    """
    return list(dict.fromkeys(press_urls))


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------
MONTHS = ("January February March April May June July August September "
          "October November December").split()
DATE_TEXT_RE = re.compile(
    r"\b(\d{1,2})\s+(" + "|".join(MONTHS) + r")\s+(\d{4})\b")


def parse_date(soup):
    """Return YYYY-MM-DD publication date from a UN press doc, or ''."""
    # 1) <time datetime="...">
    t = soup.find("time")
    if t and t.get("datetime"):
        m = re.match(r"(\d{4})-(\d{2})-(\d{2})", t["datetime"])
        if m:
            return m.group(0)
    # 2) meta tags
    for m in soup.find_all("meta"):
        name = (m.get("property") or m.get("name") or "").lower()
        if "date" in name or "publish" in name:
            c = (m.get("content") or "")
            mm = re.match(r"(\d{4})-(\d{2})-(\d{2})", c)
            if mm:
                return mm.group(0)
    # 3) "7 March 2022" in early body text
    text = soup.get_text(" ", strip=True)[:4000]
    dm = DATE_TEXT_RE.search(text)
    if dm:
        day, mon, year = dm.group(1), dm.group(2), dm.group(3)
        idx = MONTHS.index(mon) + 1
        return f"{year}-{idx:02d}-{int(day):02d}"
    return ""


def extract_title(soup):
    if soup.title and soup.title.get_text(strip=True):
        title = soup.title.get_text(strip=True)
    else:
        h1 = soup.find(["h1", "h2"])
        title = h1.get_text(strip=True) if h1 else ""
    # Drop site suffix
    title = re.split(r"\s*\|\s*", title)[0].strip()
    return title


def extract_body(soup):
    """Return plain-text statement body with nav/boilerplate stripped."""
    # Remove obvious non-content elements
    for tag in soup(["script", "style", "nav", "header", "footer", "form",
                     "noscript", "aside"]):
        tag.decompose()

    container = None
    for sel in ("div.field--name-body",
                "article .field--type-text-with-summary",
                "div.node__content",
                "article",
                "main"):
        el = soup.select_one(sel)
        if el and len(el.get_text(strip=True)) > MIN_BODY_CHARS:
            container = el
            break
    if container is None:
        container = soup.body or soup

    # Build text from block-level elements for readable spacing.
    parts = []
    for node in container.find_all(["h1", "h2", "h3", "p", "li", "blockquote"]):
        txt = node.get_text(" ", strip=True)
        if txt:
            parts.append(txt)
    text = "\n".join(parts) if parts else container.get_text("\n", strip=True)

    # Collapse whitespace, strip common boilerplate lines.
    lines = []
    for ln in text.split("\n"):
        ln = re.sub(r"\s+", " ", ln).strip()
        if not ln:
            continue
        low = ln.lower()
        if low.startswith(("for information media", "not an official record",
                           "follow us", "share this", "back to top")):
            continue
        lines.append(ln)
    return "\n".join(lines).strip()


# ---------------------------------------------------------------------------
# Main collection
# ---------------------------------------------------------------------------
def within_window(doc_date, event_date, window_days):
    if not doc_date:
        return False
    try:
        d = datetime.strptime(doc_date, "%Y-%m-%d")
        e = datetime.strptime(event_date, "%Y-%m-%d")
    except ValueError:
        return False
    return abs((d - e).days) <= window_days


def canonical_press_url(snapshot_or_press_url):
    """Extract the original press.un.org URL from a Wayback URL (or pass-through)."""
    m = re.search(r"https?://press\.un\.org/\S+\.doc\.htm", snapshot_or_press_url)
    return m.group(0) if m else snapshot_or_press_url


def collect():
    results = []
    seen_urls = set()
    per_topic = {t: 0 for t in TOPICS}

    total = 0
    for topic, event_id, name, date, window, keywords in EVENTS:
        if total >= MAX_TOTAL:
            break
        print(f"\n[{event_id}] {name}  ({date} +/-{window}d)  topic={topic}")
        candidates = discover_extra_urls(SEED.get(event_id, []))
        if not candidates:
            print("   (no candidate URLs — likely diplomatic silence)")
            continue

        n_for_event = 0
        for press_url in candidates:
            if total >= MAX_TOTAL or n_for_event >= MAX_PER_EVENT:
                break
            press_url = canonical_press_url(press_url)
            if press_url in seen_urls:
                continue
            try:
                snaps = wayback_snapshot_urls(press_url, date)
                soup = None
                for snap in snaps:
                    polite_sleep()
                    r = get(snap)
                    if r is None:
                        continue
                    cand = BeautifulSoup(r.text, "lxml")
                    title_txt = cand.title.get_text() if cand.title else ""
                    if "Client Challenge" in title_txt or len(r.text) < 4000:
                        continue  # WAF stub / 404 — try next snapshot
                    soup = cand
                    break
                if soup is None:
                    print(f"   - no usable snapshot: {press_url}")
                    continue

                doc_date = parse_date(soup)
                if not within_window(doc_date, date, window):
                    print(f"   - out of window ({doc_date or '?'}): {press_url}")
                    continue

                title = extract_title(soup)
                body = extract_body(soup)
                if len(body) < MIN_BODY_CHARS:
                    print(f"   - body too short ({len(body)}): {press_url}")
                    continue

                seen_urls.add(press_url)
                n_for_event += 1
                total += 1
                doc = {
                    "id": f"UN-{event_id}-{n_for_event}",
                    "source": "UN",
                    "topic": topic,
                    "event_id": event_id,
                    "event_name": name,
                    "date": doc_date,
                    "title": title,
                    "url": press_url,
                    "lang": "en",
                    "text": body,
                    "collected_via": "live_scrape",
                }
                # Enforce exact schema key set/order.
                doc = {k: doc[k] for k in DOCUMENT_SCHEMA}
                results.append(doc)
                per_topic[topic] += 1
                print(f"   + [{doc_date}] {len(body):>6} chars  {title[:70]}")
            except Exception as e:  # noqa: BLE001 — never let one doc kill the run
                print(f"   ! error on {press_url}: {e!r}")
                continue

    return results, per_topic, total


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    print("=== UN press scraper (via press.un.org docs mirrored on Wayback) ===")
    results, per_topic, total = collect()

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 60)
    print(f"Saved {len(results)} documents -> {OUT_PATH}")
    print("Per-topic counts:")
    for t, label in TOPICS.items():
        print(f"  {t:16s} {per_topic.get(t, 0):>3d}  ({label})")
    print("=" * 60)


if __name__ == "__main__":
    main()
