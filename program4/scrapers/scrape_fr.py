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
MAX_PER_EVENT = 6        # raised from 4 to grow the corpus
GLOBAL_CAP = 140         # raised from 80; merge/dedup is the real gate
SEARCH_PAGES = 2          # pages of search results per query (each ~10-12 items)
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


_WB_PREFIX_RE = re.compile(r"https?://web\.archive\.org/web/\d+(?:id_)?/", re.I)


def canonical_url(url):
    """Reduce any URL to its original diplomatie.gouv.fr form for dedup:
    strip a leading web.archive.org/web/<ts>id_/ wrapper, drop the query
    string and trailing slash, and normalise the scheme/host casing."""
    if not url:
        return ""
    u = _WB_PREFIX_RE.sub("", url)
    u = u.split("#", 1)[0].split("?", 1)[0].rstrip("/")
    # normalise scheme + host so http/https and www variants collapse
    u = re.sub(r"^https?://", "", u, flags=re.I)
    u = u.lower()
    return u


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
WB_MAX_FETCH_PER_EVENT = 22   # cap raw fetches per event (budget control)
WB_CACHE = os.path.join(OUT_DIR, ".wayback_cdx_cache_v2.json")
CDX_FROM = "20220101"
CDX_TO = "20250630"   # extend past 2024 so wide 2025 windows can be recovered

# URL prefixes to enumerate via CDX (article pages hold dated statements).
# A single broad "/en/country-files/*" glob is alphabetically truncated by the
# CDX `limit` before it ever reaches Russia/Ukraine, so we enumerate the
# topic-relevant country files individually, plus the general foreign-policy
# tree (official statements/speeches/communiqués + the daily "Point de presse"
# press briefings). This is the change that recovers MANY more 2022-2024 docs.
CDX_PREFIXES = [
    "diplomatie.gouv.fr/en/country-files/ukraine/*",
    "diplomatie.gouv.fr/en/country-files/russia/*",
    "diplomatie.gouv.fr/en/country-files/israel-palestinian-territories/*",
    "diplomatie.gouv.fr/en/country-files/israel/*",
    "diplomatie.gouv.fr/en/country-files/palestinian-territories/*",
    "diplomatie.gouv.fr/en/french-foreign-policy/*",
]

# keywords that must appear in the slug for a candidate to be worth fetching.
# Broadened to catch communiqués, joint statements and daily press briefings
# ("Point de presse" / "press-briefing") that comment on Ukraine or Gaza.
WB_SLUG_KW = [
    "ukraine", "ukrainian", "russia", "russian", "kyiv", "kherson",
    "kakhovka", "bucha", "donbass", "crimea", "zaporizhzhia",
    "gaza", "israel", "israeli", "palestin", "hamas", "rafah", "hostage",
    "ceasefire", "humanitarian",
    "artificial-intelligence", "intelligence",
    "press-briefing", "point-de-presse",
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
            "from": CDX_FROM, "to": CDX_TO,
            "filter": "statuscode:200", "collapse": "urlkey",
            "limit": "30000",
        }, timeout=120)
        if not r or not r.text.strip():
            print(f"  [cdx] FAILED {prefix}")
            continue
        try:
            rows = r.json()
        except Exception:
            print(f"  [cdx] non-JSON response for {prefix}")
            continue
        before = len(by_slug)
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
        print(f"  [cdx]   +{len(by_slug) - before} candidates "
              f"({len(rows) - 1} rows scanned)", flush=True)
        time.sleep(1.5)

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


_EVENT_ORDER = {e[1]: i for i, e in enumerate(EVENTS)}


def finalize(docs):
    """Dedup by canonical (original diplomatie.gouv.fr) url, drop too-short
    bodies, renumber ids per event (FR-<event_id>-<n>) and emit schema-exact
    dicts. Returns the cleaned list."""
    seen = set()
    cleaned = []
    for d in docs:
        cu = canonical_url(d.get("url", ""))
        if not cu or cu in seen:
            continue
        if len((d.get("text") or "")) < MIN_TEXT:
            continue
        seen.add(cu)
        cleaned.append(d)
    # stable order: by event order, then by date
    cleaned.sort(key=lambda d: (_EVENT_ORDER.get(d.get("event_id", ""), 999),
                                d.get("date", "")))
    per_event = {}
    out = []
    for d in cleaned:
        ev = d.get("event_id", "")
        per_event[ev] = per_event.get(ev, 0) + 1
        d = dict(d)
        d["id"] = f"FR-{ev}-{per_event[ev]}"
        d["source"] = "FR"
        d["lang"] = "en"
        d.setdefault("collected_via", "live_scrape")
        out.append({k: d.get(k, "") for k in DOCUMENT_SCHEMA})
    return out


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
    # dedup on the ORIGINAL diplomatie.gouv.fr url (wayback prefix stripped)
    seen_urls = {canonical_url(d.get("url", "")) for d in docs}
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
            if canonical_url(url) in seen_urls:
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

        # respect a TOTAL per-event ceiling (existing live docs + wayback adds),
        # so strong events don't balloon past MAX_PER_EVENT after a merge.
        have = sum(1 for d in docs if d.get("event_id") == event_id)
        kept = 0
        fetched = 0
        lo_x = center - timedelta(days=window)   # exact event window
        hi_x = center + timedelta(days=window)
        for ts, url in ranked:
            if have + kept >= MAX_PER_EVENT or fetched >= WB_MAX_FETCH_PER_EVENT:
                break
            if canonical_url(url) in seen_urls:
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
                seen_urls.add(canonical_url(url))
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

    docs = finalize(docs)
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

    # LOAD + MERGE existing docs so the live scraper grows (not replaces) the
    # corpus. Dedup is by canonical original url.
    existing = []
    if os.path.exists(OUT_PATH):
        try:
            with open(OUT_PATH, encoding="utf-8") as f:
                existing = json.load(f)
        except Exception:
            existing = []
    docs = list(existing)
    seen_urls = {canonical_url(d.get("url", "")) for d in docs}
    topic_counts = {}
    for d in docs:
        topic_counts[d.get("topic", "")] = topic_counts.get(d.get("topic", ""), 0) + 1
    zero_events = []

    print(f"France Diplomatie scraper — {len(EVENTS)} events")
    print(f"Loaded {len(docs)} existing docs to merge into")
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
            if len(candidate_urls) >= 40:
                break

        # how many docs this event already has (from a prior merge); only add
        # up to MAX_PER_EVENT total.
        have = sum(1 for d in docs if d.get("event_id") == event_id)
        kept = 0
        fetched = 0
        for url in candidate_urls:
            if have + kept >= MAX_PER_EVENT or fetched >= 24:
                break
            fetched += 1
            if canonical_url(url) in seen_urls:
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

                seen_urls.add(canonical_url(url))
                docs.append({
                    "id": f"FR-{event_id}-{have + kept + 1}",
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

        total_for_event = have + kept
        status = f"+{kept} (now {total_for_event})" if kept else \
                 (f"0 new ({have} existing)" if have else "0 docs")
        print(f"[{event_id}] {name[:42]:42s} {status}", flush=True)
        if total_for_event == 0:
            zero_events.append(f"{event_id} ({name})")

        # incremental save (schema-exact) so partial progress survives
        snap = [{k: d.get(k, "") for k in DOCUMENT_SCHEMA} for d in docs]
        with open(OUT_PATH, "w", encoding="utf-8") as f:
            json.dump(snap, f, ensure_ascii=False, indent=2)

        if len(docs) >= GLOBAL_CAP:
            print(f"\nReached global cap {GLOBAL_CAP}, stopping.")
            break

    # dedup + renumber + schema-exact
    docs = finalize(docs)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(docs, f, ensure_ascii=False, indent=2)

    topic_counts = {}
    for d in docs:
        topic_counts[d["topic"]] = topic_counts.get(d["topic"], 0) + 1

    print("\n===== SUMMARY =====")
    print(f"Total docs: {len(docs)}")
    for t in ("ukraine", "gaza", "ai_governance"):
        print(f"  {t:16s} {topic_counts.get(t, 0)}")
    print(f"Events with 0 docs ({len(zero_events)}): "
          + (", ".join(zero_events) if zero_events else "none"))
    print(f"Saved -> {os.path.abspath(OUT_PATH)}")


if __name__ == "__main__":
    # `python scrape_fr.py wayback` -> recover 2022-2024 from the Archive and
    #     MERGE into FR.json (preserves + grows existing docs).
    # `python scrape_fr.py all`     -> run live search THEN wayback (full build).
    # bare `python scrape_fr.py`    -> the live-search scraper (2025+).
    mode = sys.argv[1] if len(sys.argv) > 1 else "live"
    if mode == "wayback":
        recover_wayback()
    elif mode == "all":
        main()
        print("\n--- now running Wayback recovery ---\n")
        recover_wayback()
    else:
        main()
