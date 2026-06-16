#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
France Diplomatie (Ministry for Europe and Foreign Affairs) — English statements scraper.

Source: https://www.diplomatie.gouv.fr/en/
Strategy:
  - The site is a Drupal install. /en/rss/ is 404. There is no working RSS feed
    on the English news pages, BUT there is a full-text search endpoint:
        /en/search?search_api_fulltext=<terms>&page=<n>
    (the form field is `search_api_fulltext`; a plain `search` param is ignored).
  - For each event we run several keyword queries (event keywords + plain terms),
    collect candidate article URLs, fetch each article, parse the publication date
    from the `.diplomatie--hdp-date` block, and keep articles whose date falls
    within the event's ±window and whose text matches the keywords.

Article URL pattern (English content, French slugs):
    /en/presse-et-ressources/decouvrir-et-informer/actualites/<slug>

Output: ../data/raw/FR.json  (DOCUMENT_SCHEMA keys only)
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
from events import EVENTS, DOCUMENT_SCHEMA  # noqa: E402

BASE = "https://www.diplomatie.gouv.fr"
SEARCH = BASE + "/en/search"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "raw")
OUT_PATH = os.path.join(OUT_DIR, "FR.json")

TIMEOUT = 20
MAX_PER_EVENT = 4
GLOBAL_CAP = 80
SEARCH_PAGES = 1          # pages of search results per query (each ~10-12 items)
MIN_TEXT = 150

MONTHS = {m: i for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july",
     "august", "september", "october", "november", "december"], 1)}

# Extra plain terms to broaden recall per topic.
TOPIC_TERMS = {
    "ukraine": ["Ukraine", "Russia"],
    "gaza": ["Gaza", "Israel"],
    "ai_governance": ["artificial intelligence", "AI Action Summit"],
}

# Topic-specific relevance gate: a doc must contain one of these strings
# (case-insensitive) in title+text to count for the topic. Prevents bilateral
# meeting readouts that merely mention "AI" once from matching ai_governance.
TOPIC_REQUIRE = {
    "ukraine": ["ukraine", "russia"],
    "gaza": ["gaza", "israel", "palestin"],
    "ai_governance": ["artificial intelligence", "ai action summit",
                      "ai safety", "ai governance"],
}

_session = requests.Session()
_session.headers.update(HEADERS)


def fetch(url, params=None, tries=3):
    """GET with retry + exponential backoff. Returns response or None."""
    for attempt in range(tries):
        try:
            r = _session.get(url, params=params, timeout=TIMEOUT, allow_redirects=True)
            if r.status_code == 200:
                r.encoding = "utf-8"
                return r
            if r.status_code in (403, 404):
                return None
        except requests.RequestException:
            pass
        time.sleep((2 ** attempt) + random.uniform(0, 0.5))
    return None


def polite_sleep():
    time.sleep(random.uniform(0.6, 1.0))


def parse_date(text):
    """Parse 'On : March 31st 2025' / 'Published on : June 15th 2026' -> date."""
    if not text:
        return None
    m = re.search(r"([A-Za-z]+)\s+(\d{1,2})[a-z]{0,2}\s+(\d{4})", text)
    if not m:
        return None
    mon = MONTHS.get(m.group(1).lower())
    if not mon:
        return None
    try:
        return datetime(int(m.group(3)), mon, int(m.group(2))).date()
    except ValueError:
        return None


def search_urls(query, pages=SEARCH_PAGES):
    """Run a full-text search; return ordered list of article URLs."""
    found = []
    seen = set()
    for page in range(pages):
        r = fetch(SEARCH, params={"search_api_fulltext": query, "page": page})
        if not r:
            break
        soup = BeautifulSoup(r.text, "html.parser")
        page_hrefs = []
        for a in soup.select("a[href*='actualites/']"):
            href = a.get("href", "")
            if "/actualites/" not in href:
                continue
            if href.startswith("/"):
                href = BASE + href
            href = href.split("#")[0].split("?")[0]
            if href not in seen:
                seen.add(href)
                page_hrefs.append(href)
                found.append(href)
        polite_sleep()
        if not page_hrefs:
            break
    return found


def parse_article(url):
    """Fetch article; return (date, title, text) or None."""
    r = fetch(url)
    if not r:
        return None
    soup = BeautifulSoup(r.text, "html.parser")

    art = soup.select_one("article") or soup.select_one("main")
    if not art:
        return None

    # title
    h1 = soup.find("h1")
    title = h1.get_text(" ", strip=True) if h1 else ""

    # date
    date_el = art.select_one(".diplomatie--hdp-date") or soup.select_one(".diplomatie--hdp-date")
    d = parse_date(date_el.get_text(" ", strip=True)) if date_el else None

    # body: remove header block (title/date/share), breadcrumb, nav, scripts
    for sel in [".diplomatie--hdp", "nav", "script", "style", "header",
                ".fr-breadcrumb", "[class*='breadcrumb']", "[class*='partage']",
                "[class*='share']", "figure"]:
        for el in art.select(sel):
            el.decompose()

    text = art.get_text("\n", strip=True)
    # collapse whitespace, drop obvious boilerplate lines
    lines = []
    for ln in text.split("\n"):
        ln = " ".join(ln.split())
        if not ln:
            continue
        low = ln.lower()
        if low in ("home", "news", "voir le fil d'ariane", "accéder au contenu",
                   "share", "print", "imprimer"):
            continue
        lines.append(ln)
    text = "\n".join(lines).strip()
    # if title is duplicated as first line, drop it once
    if text.startswith(title) and title:
        text = text[len(title):].strip()

    return d, title, text


def keyword_match(text, title, keywords, topic):
    """True if the doc passes the topic relevance gate AND matches a keyword set."""
    hay = (title + " " + text).lower()
    tl = title.lower()
    # hard topic gate: must mention a core topic term
    gate = TOPIC_REQUIRE.get(topic, [])
    if gate and not any(g in hay for g in gate):
        return False
    # AI governance is stricter: the doc must be *about* AI, not merely held
    # "on the sidelines of" the AI summit. Require AI in the title, or the AI
    # term appearing substantively (>=2x) and not only as a meeting venue.
    if topic == "ai_governance":
        ai_terms = ("artificial intelligence", "ai action summit",
                    "ai safety", "ai governance")
        in_title = any(t in tl for t in ai_terms)
        body = text.lower()
        count = sum(body.count(t) for t in ai_terms)
        venue_only = ("sidelines of" in body or "on the margins of" in body) and count <= 1
        if not in_title and (count < 2 or venue_only):
            return False
    for kw in keywords:
        toks = [t for t in re.split(r"\s+", kw.lower()) if len(t) > 2]
        if toks and sum(1 for t in toks if t in hay) >= max(1, len(toks) // 2):
            return True
    return False


# ===========================================================================
# Wayback Machine recovery (2022-2024 historical statements)
# ---------------------------------------------------------------------------
# France Diplomatie's LIVE search index only covers 2025+, so the main()
# scraper above returns 0 for every 2022-2024 event. To recover those years
# we use the Internet Archive CDX API to enumerate archived English statement
# pages (the old site filed them under /en/country-files/<c>/news/article/...
# and /en/french-foreign-policy/.../article/...), then fetch each via the raw
# snapshot endpoint  http://web.archive.org/web/<ts>id_/<originalurl>  which
# returns the original HTML verbatim (no Wayback chrome). We parse the real
# publication date (from the slug or the H1) and assign each doc to the nearest
# event window, reusing keyword_match() above.
# ===========================================================================

CDX = "http://web.archive.org/cdx/search/cdx"
WB_RAW = "http://web.archive.org/web/{ts}id_/{url}"
WB_TIMEOUT = 25
WB_MAX_FETCH_PER_EVENT = 16   # cap raw fetches per event (budget control)
WB_CACHE = os.path.join(OUT_DIR, ".wayback_cdx_cache.json")

# url prefixes to enumerate via CDX (article pages hold dated statements)
CDX_PREFIXES = [
    "diplomatie.gouv.fr/en/country-files/*",
    "diplomatie.gouv.fr/en/french-foreign-policy/*",
]

# keywords that must appear in the slug for a candidate to be worth fetching
WB_SLUG_KW = [
    "ukraine", "russia", "russian",
    "gaza", "israel", "israeli", "palestin", "hamas", "rafah",
    "artificial-intelligence", "intelligence",
]

_MON3 = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul",
     "aug", "sep", "oct", "nov", "dec"], 1)}


def wb_fetch(url, params=None, tries=4, timeout=WB_TIMEOUT):
    """GET against archive.org with patient retry/backoff (it is slow/flaky)."""
    for attempt in range(tries):
        try:
            r = _session.get(url, params=params, timeout=timeout,
                             allow_redirects=True)
            if r.status_code == 200:
                r.encoding = "utf-8"
                return r
            if r.status_code in (403, 404):
                return None
            # 429 / 5xx -> back off and retry
        except requests.RequestException:
            pass
        time.sleep((2 ** attempt) + random.uniform(0.5, 1.5))
    return None


def cdx_enumerate():
    """Return {canonical_slug: (timestamp, clean_original_url)} for relevant
    /article/ pages, cached to disk so re-runs are cheap."""
    if os.path.exists(WB_CACHE):
        try:
            with open(WB_CACHE, encoding="utf-8") as f:
                cached = json.load(f)
            if cached:
                print(f"  [cdx] loaded {len(cached)} candidates from cache")
                return {k: tuple(v) for k, v in cached.items()}
        except Exception:
            pass

    by_slug = {}
    for prefix in CDX_PREFIXES:
        print(f"  [cdx] querying {prefix} ...", flush=True)
        r = wb_fetch(CDX, params={
            "url": prefix, "output": "json",
            "from": "20220101", "to": "20241231",
            "filter": "statuscode:200", "collapse": "urlkey",
            "limit": "30000",
        }, timeout=120)
        if not r:
            print(f"  [cdx] FAILED {prefix}")
            continue
        try:
            rows = r.json()
        except Exception:
            continue
        for row in rows[1:]:
            ts, original = row[1], row[2]
            if "/article/" not in original:
                continue
            low = original.lower()
            if not any(k in low for k in WB_SLUG_KW):
                continue
            slug = original.split("/article/", 1)[1].split("?")[0].rstrip("/")
            clean = original.split("?")[0]
            if slug not in by_slug or ts < by_slug[slug][0]:
                by_slug[slug] = (ts, clean)
        time.sleep(1.0)

    print(f"  [cdx] {len(by_slug)} unique relevant article candidates")
    try:
        with open(WB_CACHE, "w", encoding="utf-8") as f:
            json.dump(by_slug, f, ensure_ascii=False)
    except Exception:
        pass
    return by_slug


def date_from_slug(slug):
    """Extract a date from a trailing  -dd-mm-yy / -dd-mon-yyyy  slug suffix."""
    s = slug.lower()
    m = re.search(r"-(\d{1,2})-([a-z]{3,9})-(\d{2,4})$", s)
    if m:
        mon = _MON3.get(m.group(2)[:3])
        if mon:
            y = int(m.group(3))
            y = y + 2000 if y < 100 else y
            try:
                return datetime(y, mon, int(m.group(1))).date()
            except ValueError:
                pass
    m = re.search(r"-(\d{1,2})-(\d{1,2})-(\d{2,4})$", s)
    if m:
        y = int(m.group(3))
        y = y + 2000 if y < 100 else y
        try:
            return datetime(y, int(m.group(2)), int(m.group(1))).date()
        except ValueError:
            pass
    return None


def date_from_title(title):
    """Extract '(5 october 2023)' / '5 October 2023' style date from a title."""
    if not title:
        return None
    m = re.search(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", title)
    if m:
        mon = _MON3.get(m.group(2).lower()[:3])
        if mon:
            try:
                return datetime(int(m.group(3)), mon, int(m.group(1))).date()
            except ValueError:
                pass
    # also accept 'October 5 2023' order
    return parse_date(title)


def parse_wayback(ts, original_url):
    """Fetch the raw snapshot, return (date, title, text) or None."""
    r = wb_fetch(WB_RAW.format(ts=ts, url=original_url))
    if not r:
        return None
    soup = BeautifulSoup(r.text, "html.parser")

    h1 = soup.find("h1")
    title = h1.get_text(" ", strip=True) if h1 else ""

    art = soup.select_one("article") or soup.select_one("main") or soup.body
    if not art:
        return None

    for sel in ["nav", "script", "style", "header", "footer",
                ".diplomatie--hdp", ".fr-breadcrumb", "[class*='breadcrumb']",
                "[class*='partage']", "[class*='share']", "figure"]:
        for el in art.select(sel):
            el.decompose()

    text = art.get_text("\n", strip=True)
    lines = []
    for ln in text.split("\n"):
        ln = " ".join(ln.split())
        if not ln:
            continue
        low = ln.lower()
        if low in ("home", "news", "share", "print", "imprimer",
                   "share on twitter", "share on facebook",
                   "partager sur linkedin", "voir le fil d'ariane",
                   "accéder au contenu"):
            continue
        lines.append(ln)
    text = "\n".join(lines).strip()
    if title and text.startswith(title):
        text = text[len(title):].strip()

    d = date_from_title(title) or date_from_slug(
        original_url.rstrip("/").split("/")[-1])
    return d, title, text


def recover_wayback():
    """Recover 2022-2024 France statements from the Wayback Machine and APPEND
    them to FR.json (preserving the existing live-scraped docs)."""
    os.makedirs(OUT_DIR, exist_ok=True)

    # load existing docs, build dedup + per-event counters
    existing = []
    if os.path.exists(OUT_PATH):
        try:
            with open(OUT_PATH, encoding="utf-8") as f:
                existing = json.load(f)
        except Exception:
            existing = []
    docs = list(existing)
    seen_urls = {d.get("url", "") for d in docs}
    per_event_n = {}
    for d in docs:
        ev = d.get("event_id", "")
        per_event_n[ev] = max(per_event_n.get(ev, 0),
                              int(d.get("id", "FR--0").rsplit("-", 1)[-1] or 0))

    print(f"Wayback recovery — starting from {len(docs)} existing docs")
    candidates = cdx_enumerate()
    if not candidates:
        print("  no candidates; aborting")
        return

    # pre-resolve a date hint for each candidate (slug date if present)
    cand_list = []
    for slug, (ts, url) in candidates.items():
        cand_list.append((date_from_slug(slug), ts, url, slug))

    added_total = 0
    for topic, event_id, name, date_str, window, keywords in EVENTS:
        center = datetime.strptime(date_str, "%Y-%m-%d").date()
        # widen window a touch for the date-hint pre-filter (final gate is exact)
        lo = center - timedelta(days=window + 10)
        hi = center + timedelta(days=window + 10)
        all_kw = list(keywords) + TOPIC_TERMS.get(topic, [])

        # topic slug gate
        slug_gate = {
            "ukraine": ("ukraine", "russia", "russian"),
            "gaza": ("gaza", "israel", "palestin", "hamas", "rafah"),
            "ai_governance": ("artificial-intelligence", "intelligence"),
        }[topic]

        # rank candidates: those whose slug-date falls in window first, then
        # date-unknown slugs that match the topic gate (we'll check body date).
        in_window, unknown = [], []
        for d_hint, ts, url, slug in cand_list:
            if url in seen_urls:
                continue
            if not any(g in slug.lower() for g in slug_gate):
                continue
            if d_hint is not None:
                if lo <= d_hint <= hi:
                    in_window.append((abs((d_hint - center).days), ts, url))
            else:
                unknown.append((ts, url))
        in_window.sort()
        ranked = [(ts, url) for _, ts, url in in_window] + unknown

        kept = 0
        fetched = 0
        lo_x = center - timedelta(days=window)   # exact event window
        hi_x = center + timedelta(days=window)
        for ts, url in ranked:
            if kept >= MAX_PER_EVENT or fetched >= WB_MAX_FETCH_PER_EVENT:
                break
            if url in seen_urls:
                continue
            fetched += 1
            try:
                res = parse_wayback(ts, url)
                if not res:
                    continue
                d, title, text = res
                if d is None or not (lo_x <= d <= hi_x):
                    continue
                if len(text) < MIN_TEXT:
                    continue
                if not keyword_match(text, title, all_kw, topic):
                    continue
                seen_urls.add(url)
                per_event_n[event_id] = per_event_n.get(event_id, 0) + 1
                docs.append({
                    "id": f"FR-{event_id}-{per_event_n[event_id]}",
                    "source": "FR",
                    "topic": topic,
                    "event_id": event_id,
                    "event_name": name,
                    "date": d.isoformat(),
                    "title": title,
                    "url": url,
                    "lang": "en",
                    "text": text,
                    "collected_via": "live_scrape",
                })
                kept += 1
                added_total += 1
                time.sleep(random.uniform(1.0, 2.0))
            except Exception as e:
                print(f"    ! error on {url[:70]}: {e}")
                continue

        if kept:
            print(f"[{event_id}] {name[:40]:40s} +{kept} from wayback",
                  flush=True)
            # incremental save
            snap = [{k: x.get(k, "") for k in DOCUMENT_SCHEMA} for x in docs]
            with open(OUT_PATH, "w", encoding="utf-8") as f:
                json.dump(snap, f, ensure_ascii=False, indent=2)

    docs = [{k: x.get(k, "") for k in DOCUMENT_SCHEMA} for x in docs]
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(docs, f, ensure_ascii=False, indent=2)

    print(f"\n===== WAYBACK RECOVERY SUMMARY =====")
    print(f"Added {added_total} new docs; total now {len(docs)}")
    tc, ev = {}, set()
    for d in docs:
        tc[d["topic"]] = tc.get(d["topic"], 0) + 1
        ev.add(d["event_id"])
    for t in ("ukraine", "gaza", "ai_governance"):
        print(f"  {t:16s} {tc.get(t, 0)}")
    print(f"Events covered: {len(ev)}/{len(EVENTS)}")
    print(f"Saved -> {os.path.abspath(OUT_PATH)}")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    docs = []
    seen_urls = set()
    topic_counts = {}
    zero_events = []

    print(f"France Diplomatie scraper — {len(EVENTS)} events")
    print(f"Search endpoint: {SEARCH}?search_api_fulltext=...\n")

    for topic, event_id, name, date_str, window, keywords in EVENTS:
        center = datetime.strptime(date_str, "%Y-%m-%d").date()
        lo = center - timedelta(days=window)
        hi = center + timedelta(days=window)
        all_kw = list(keywords) + TOPIC_TERMS.get(topic, [])

        # build query list: each keyword phrase + plain topic terms
        queries = []
        for kw in keywords:
            queries.append(kw)
        for t in TOPIC_TERMS.get(topic, []):
            queries.append(t)

        candidate_urls = []
        cu_seen = set(seen_urls)  # don't reconsider already-used URLs
        for q in queries:
            for u in search_urls(q):
                if u not in cu_seen:
                    cu_seen.add(u)
                    candidate_urls.append(u)
            if len(candidate_urls) >= 25:
                break

        kept = 0
        fetched = 0
        for url in candidate_urls:
            if kept >= MAX_PER_EVENT or fetched >= 18:
                break
            fetched += 1
            if url in seen_urls:
                continue
            try:
                res = parse_article(url)
                if not res:
                    continue
                d, title, text = res
                if d is None or not (lo <= d <= hi):
                    continue
                if len(text) < MIN_TEXT:
                    continue
                if not keyword_match(text, title, all_kw, topic):
                    continue

                seen_urls.add(url)
                n = kept + 1
                docs.append({
                    "id": f"FR-{event_id}-{n}",
                    "source": "FR",
                    "topic": topic,
                    "event_id": event_id,
                    "event_name": name,
                    "date": d.isoformat(),
                    "title": title,
                    "url": url,
                    "lang": "en",
                    "text": text,
                    "collected_via": "live_scrape",
                })
                kept += 1
                topic_counts[topic] = topic_counts.get(topic, 0) + 1
                polite_sleep()
            except Exception as e:
                print(f"    ! error on {url[:70]}: {e}")
                continue

        status = f"{kept} doc(s)" if kept else "0 docs"
        print(f"[{event_id}] {name[:42]:42s} {status}", flush=True)
        if kept == 0:
            zero_events.append(f"{event_id} ({name})")

        # incremental save (schema-exact) so partial progress survives
        snap = [{k: d.get(k, "") for k in DOCUMENT_SCHEMA} for d in docs]
        with open(OUT_PATH, "w", encoding="utf-8") as f:
            json.dump(snap, f, ensure_ascii=False, indent=2)

        if len(docs) >= GLOBAL_CAP:
            print(f"\nReached global cap {GLOBAL_CAP}, stopping.")
            break

    # ensure schema-exact dicts
    docs = [{k: doc.get(k, "") for k in DOCUMENT_SCHEMA} for doc in docs]

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(docs, f, ensure_ascii=False, indent=2)

    print("\n===== SUMMARY =====")
    print(f"Total docs: {len(docs)}")
    for t in ("ukraine", "gaza", "ai_governance"):
        print(f"  {t:16s} {topic_counts.get(t, 0)}")
    print(f"Events with 0 docs ({len(zero_events)}): "
          + (", ".join(zero_events) if zero_events else "none"))
    print(f"Saved -> {os.path.abspath(OUT_PATH)}")


if __name__ == "__main__":
    # `python scrape_fr.py wayback` -> recover 2022-2024 from the Archive and
    # APPEND to FR.json. Bare `python scrape_fr.py` -> the live-search scraper.
    if len(sys.argv) > 1 and sys.argv[1] == "wayback":
        recover_wayback()
    else:
        main()
