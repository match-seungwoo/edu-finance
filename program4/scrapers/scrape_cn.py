#!/usr/bin/env python3
"""
PRC MFA (Ministry of Foreign Affairs) English statement scraper.

Source: https://www.fmprc.gov.cn/eng/
Primary section: Spokesperson's Regular Press Conferences
    listing: /eng/xw/fyrbt/lxjzh/index_<N>.html
    details: /eng/xw/fyrbt/lxjzh/<YYYYMM>/t<YYYYMMDD>_<num>.html

The listing pages carry the FULL title (incl. real conference date) so we build a
date-indexed catalogue first, then for each event in events.py we fetch only the
press conferences whose date falls inside the event's ±window and whose body text
mentions any of the topic keywords. The relevant Q&A paragraphs are extracted
(falling back to the full transcript) and saved to data/raw/CN.json.

requests + bs4, browser UA, polite sleeps, retry-with-backoff, encoding-safe.
"""

import json
import os
import re
import sys
import time
import random
from collections import Counter, defaultdict
from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from events import EVENTS, DOCUMENT_SCHEMA  # noqa: E402

# ── config ───────────────────────────────────────────────────────────────────
BASE = "https://www.fmprc.gov.cn/eng"
LISTING = BASE + "/xw/fyrbt/lxjzh/{}"          # index.html / index_N.html
LISTING_FIRST = "index.html"
MAX_PAGES = 150                                # archive is ~143 pages (Apr 2022→now)
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "raw")
OUT_PATH = os.path.abspath(os.path.join(OUT_DIR, "CN.json"))
CAP_TOTAL = 80
PER_EVENT = 2  # keep breadth: every event gets a fair share under the cap

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
HEADERS = {"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"}
TIMEOUT = 20

# Per-topic extra plain search terms to widen keyword matching.
TOPIC_TERMS = {
    "ukraine": ["ukraine", "russia", "russian", "kyiv", "crisis", "ceasefire",
                "peace talks", "negotiation", "nuclear"],
    "gaza": ["gaza", "palestine", "palestinian", "israel", "israeli", "hamas",
             "ceasefire", "humanitarian", "rafah", "two-state", "west bank"],
    "ai_governance": ["artificial intelligence", "ai governance", " ai ",
                      "global governance of ai", "digital", "technology"],
}

# Hand-verified migrated archive URLs for events the listing catalogue cannot
# reach (the lxjzh listing only paginates back to ~2022-03-16, so the very first
# Ukraine events fall back to these known-good detail pages).
SEED_URLS = {
    "ukr01": [  # Russian invasion begins (2022-02-24, ±14d)
        "https://www.fmprc.gov.cn/eng/xw/fyrbt/lxjzh/202405/t20240530_11347225.html",  # Feb 16, 2022
        "https://www.fmprc.gov.cn/eng/xw/fyrbt/lxjzh/202405/t20240530_11347234.html",  # Mar 1, 2022
    ],
    "ukr02": [  # UNGA ES-11/1 resolution (2022-03-02, ±10d)
        "https://www.fmprc.gov.cn/eng/xw/fyrbt/lxjzh/202407/t20240730_11463275.html",  # Mar 2, 2022
        "https://www.fmprc.gov.cn/eng/xw/fyrbt/lxjzh/202405/t20240530_11347236.html",  # Mar 3, 2022
    ],
}

DATE_RE = re.compile(
    r"Regular Press Conference on\s+([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})", re.I)
MONTHS = {m.lower(): i for i, m in enumerate(
    ["", "January", "February", "March", "April", "May", "June", "July",
     "August", "September", "October", "November", "December"])}

session = requests.Session()
session.headers.update(HEADERS)


# ── http helpers ─────────────────────────────────────────────────────────────
def fetch(url, tries=3):
    """GET with retry/backoff. Returns decoded text or None."""
    for i in range(tries):
        try:
            r = session.get(url, timeout=TIMEOUT)
            if r.status_code == 200 and r.content:
                # fmprc pages are sometimes charset-quirky: prefer apparent
                # encoding, then try a few common ones, guard against mojibake.
                raw = r.content
                # fmprc /eng pages are UTF-8 but often mis-declare charset
                # (requests then guesses latin-1 -> mojibake). Try real
                # encodings first, validate against mojibake markers.
                for enc in ("utf-8", "gb18030", "gb2312",
                            r.apparent_encoding, r.encoding):
                    if not enc:
                        continue
                    try:
                        txt = raw.decode(enc)
                    except (LookupError, UnicodeDecodeError):
                        continue
                    # reject mojibake: replacement chars or tell-tale Ã/â runs
                    if txt.count("�") < 5 and txt.count("Ã") < 5:
                        return txt
                return raw.decode("utf-8", "replace")
            if r.status_code in (403, 404):
                return None
        except requests.RequestException:
            pass
        time.sleep(1.5 * (i + 1) + random.random())
    return None


def parse_real_date(title):
    m = DATE_RE.search(title or "")
    if not m:
        return None
    mon = MONTHS.get(m.group(1).lower())
    if not mon:
        return None
    try:
        return datetime(int(m.group(3)), mon, int(m.group(2)))
    except ValueError:
        return None


def abs_url(href, page_url):
    if href.startswith("http"):
        return href
    # resolve relative to the listing page URL (handles ./YYYYMM/t...)
    return urljoin(page_url, href)


# ── catalogue ────────────────────────────────────────────────────────────────
def build_catalogue():
    """Crawl all listing pages -> list of (date, title, url)."""
    cat = {}            # url -> (date, title)
    print("Building press-conference catalogue ...")
    for p in range(MAX_PAGES):
        page = LISTING_FIRST if p == 0 else f"index_{p}.html"
        url = LISTING.format(page)
        html = fetch(url)
        if not html:
            # one miss is fine; two consecutive misses near the end -> stop
            if p > 5:
                break
            continue
        soup = BeautifulSoup(html, "html.parser")
        found = 0
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if not re.search(r"t20\d{6}_\d+\.s?html", href):
                continue
            title = a.get_text(strip=True)
            if "Conference" not in title:
                continue
            d = parse_real_date(title)
            if not d:
                continue
            u = abs_url(href, url)
            cat.setdefault(u, (d, title))
            found += 1
        if found == 0 and p > 3:
            # empty tail page
            break
        if p % 20 == 0:
            print(f"  ...page {p}: catalogue size {len(cat)}")
        time.sleep(1.0 + random.random())
    items = sorted(((d, t, u) for u, (d, t) in cat.items()), key=lambda x: x[0])
    if items:
        print(f"  catalogue: {len(items)} conferences, "
              f"{items[0][0].date()} .. {items[-1][0].date()}")
    return items


# ── body extraction ──────────────────────────────────────────────────────────
def extract_body(html):
    soup = BeautifulSoup(html, "html.parser")
    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.split("_Ministry")[0].strip()
    el = (soup.select_one(".content_text") or soup.select_one("#News_Body_Txt_A")
          or soup.select_one(".news_content") or soup.select_one("#printBody"))
    if not el:
        return title, []
    for bad in el.select("script, style"):
        bad.decompose()
    paras = []
    for node in el.find_all(["p", "div"]):
        t = node.get_text(" ", strip=True)
        if t:
            paras.append(t)
    if not paras:
        whole = el.get_text("\n", strip=True)
        paras = [s for s in whole.split("\n") if s.strip()]
    # de-dup nested-div repeats while preserving order
    seen, out = set(), []
    for pgh in paras:
        k = pgh[:120]
        if k in seen:
            continue
        seen.add(k)
        out.append(pgh)
    return title, out


def relevant_text(paras, terms):
    """Keep paragraph blocks (Q + following answer) that mention a term.

    A press conference is a sequence of paras; a question often precedes the
    answer. We keep any matching paragraph plus its immediate neighbours so the
    Q&A reads coherently. If matches are dense, fall back to the full transcript.
    """
    low = [p.lower() for p in paras]
    hit = [any(t in lp for t in terms) for lp in low]
    if not any(hit):
        return None
    if sum(hit) >= max(3, len(paras) * 0.4):
        return "\n\n".join(paras)
    keep = set()
    for i, h in enumerate(hit):
        if h:
            for j in (i - 1, i, i + 1):
                if 0 <= j < len(paras):
                    keep.add(j)
    return "\n\n".join(paras[i] for i in sorted(keep))


# ── main ─────────────────────────────────────────────────────────────────────
def main():
    catalogue = build_catalogue()
    if not catalogue:
        print("FATAL: empty catalogue; aborting.")
        sys.exit(1)

    docs = []
    seen_urls = set()
    per_topic = Counter()
    per_event = Counter()
    zero_events = []
    start = time.time()
    budget = 7 * 60  # seconds

    for topic, eid, ename, datestr, window, keywords in EVENTS:
        if len(docs) >= CAP_TOTAL:
            break
        ev_date = datetime.strptime(datestr, "%Y-%m-%d")
        lo = ev_date - timedelta(days=window)
        hi = ev_date + timedelta(days=window)
        terms = [k.lower() for k in keywords] + TOPIC_TERMS.get(topic, [])
        # event-specific topic anchor must also appear (avoids false positives)
        anchors = {"ukraine": ["ukraine", "russia", "kyiv", "crisis", "moscow"],
                   "gaza": ["gaza", "palestin", "israel", "hamas", "rafah"],
                   "ai_governance": ["artificial intelligence", " ai ",
                                     "ai "]}[topic]

        cands = [(d, t, u) for (d, t, u) in catalogue if lo <= d <= hi]
        # prepend any hand-verified seed URLs for hard-to-reach events
        seed = [(ev_date, "", su) for su in SEED_URLS.get(eid, [])
                if su not in {c[2] for c in cands}]
        cands = seed + cands
        n = 0
        for d, t, u in cands:
            if n >= PER_EVENT or len(docs) >= CAP_TOTAL:
                break
            if time.time() - start > budget:
                print("  (time budget hit; stopping fetch loop)")
                break
            if u in seen_urls:
                continue
            try:
                html = fetch(u)
                if not html:
                    continue
                title, paras = extract_body(html)
                full = "\n".join(paras).lower()
                if not any(a in full for a in anchors):
                    continue
                text = relevant_text(paras, terms)
                if not text or len(text) < 200:
                    continue
                seen_urls.add(u)
                n += 1
                real = parse_real_date(title) or d  # trust the page's own date
                doc = {
                    "id": f"CN-{eid}-{n}",
                    "source": "CN",
                    "topic": topic,
                    "event_id": eid,
                    "event_name": ename,
                    "date": real.strftime("%Y-%m-%d"),
                    "title": title or t,
                    "url": u,
                    "lang": "en",
                    "text": text,
                    "collected_via": "live_scrape",
                }
                docs.append(doc)
                per_topic[topic] += 1
                per_event[eid] += 1
                print(f"  [{eid}] +1  {d.date()}  ({len(text)} chars)")
                time.sleep(1.0 + random.random())
            except Exception as e:  # noqa: BLE001 - per-item resilience
                print(f"  [{eid}] item error on {u}: {e}")
                continue
        if per_event[eid] == 0:
            zero_events.append(eid)
            print(f"  [{eid}] 0 docs (candidates in window: {len(cands)})")

    os.makedirs(OUT_DIR, exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(docs, f, ensure_ascii=False, indent=2)

    # validate schema
    bad = [d["id"] for d in docs if list(d.keys()) != DOCUMENT_SCHEMA]
    print("\n" + "=" * 60)
    print(f"TOTAL docs: {len(docs)}  -> {OUT_PATH}")
    print("Per-topic:")
    for tp in ("ukraine", "gaza", "ai_governance"):
        print(f"  {tp:16s} {per_topic[tp]}")
    print(f"Events with 0 docs ({len(zero_events)}): {', '.join(zero_events) or 'none'}")
    if bad:
        print(f"SCHEMA MISMATCH on: {bad}")
    print(f"Elapsed: {time.time() - start:.0f}s")


if __name__ == "__main__":
    main()
