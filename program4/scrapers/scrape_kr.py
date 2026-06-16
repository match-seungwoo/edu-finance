"""
scrape_kr.py — ROK MOFA (Ministry of Foreign Affairs) English statements scraper.

Collects official English press releases / spokesperson statements from the
ROK MOFA English site for the 30 diplomatic events defined in events.py and
writes them to data/raw/KR.json following DOCUMENT_SCHEMA.

Source board: https://www.mofa.go.kr/eng/brd/m_5676/list.do  (Press Releases)
  - list.do supports server-side date-range filtering via srchFr / srchTo
    (YYYYMMDD). Detail pages: view.do?seq=<seq>.
  - The board's own keyword search is unreliable, so we pull the date-range
    listing for each event window and filter titles by keyword client-side.

Engineering: requests + bs4, browser UA, polite sleeps, retry w/ backoff,
generous timeouts, dedup by URL, per-item try/except.
"""

import json
import os
import re
import sys
import time
from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from events import EVENTS, DOCUMENT_SCHEMA  # noqa: E402

# ---------------------------------------------------------------------------
BASE = "https://www.mofa.go.kr"
BOARD = "/eng/brd/m_5676"          # Press Releases (incl. spokesperson statements)
LIST_URL = BASE + BOARD + "/list.do"
VIEW_URL = BASE + BOARD + "/view.do"

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "raw")
OUT_PATH = os.path.abspath(os.path.join(OUT_DIR, "KR.json"))

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

MIN_TEXT_LEN = 150
PER_EVENT_CAP = 3
TOTAL_CAP = 60
MAX_LIST_PAGES = 4          # safety cap on pagination per window

# Extra/simpler fallback keyword terms per topic (Korea phrases things its way).
TOPIC_FALLBACK = {
    "ukraine": ["ukraine", "russia", "russian"],
    "gaza": ["gaza", "israel", "hamas", "palestin", "middle east", "rafah"],
    # AI terms must be specific: generic words like "summit"/"digital" and the
    # bare token "ai" produce false positives (e.g. "humanitarian AID").
    "ai_governance": [
        "artificial intelligence", "reaim", "bletchley", "ai safety",
        "ai summit", "ai action", "digital compact", "ai governance",
    ],
}

# Words that, if present in the title, must be a whole-word match (avoids the
# "ai" inside "aid"/"said"/"main" problem).
WORD_BOUNDARY_TERMS = {"ai"}

session = requests.Session()
session.headers.update(HEADERS)


def get(url, params=None, tries=3):
    """GET with retry + exponential backoff. The board needs the session
    cookie returned on the first (307) hit, which requests.Session handles."""
    last = None
    for i in range(tries):
        try:
            r = session.get(url, params=params, timeout=20)
            if r.status_code == 200 and len(r.text) > 500:
                return r
            last = f"HTTP {r.status_code} len {len(r.text)}"
        except requests.RequestException as e:
            last = repr(e)
        time.sleep(1.5 * (i + 1))
    print(f"    ! GET failed ({last}): {url} {params or ''}")
    return None


def list_params(page, fr, to):
    return {
        "page": page,
        "srchFr": fr,
        "srchTo": to,
        "srchWord": "",
        "srchTp": "",
        "multi_itm_seq": "0",
        "itm_seq_1": "0",
        "itm_seq_2": "0",
        "company_cd": "",
        "company_nm": "",
    }


def fetch_listing(fr, to):
    """Return list of (seq, title, date) within the YYYYMMDD date range."""
    items = []
    for page in range(1, MAX_LIST_PAGES + 1):
        r = get(LIST_URL, params=list_params(page, fr, to))
        if not r:
            break
        soup = BeautifulSoup(r.text, "html.parser")
        rows = soup.select("table tbody tr")
        page_seqs = []
        for tr in rows:
            try:
                a = tr.find("a", onclick=re.compile(r"f_view"))
                if not a:
                    continue
                m = re.search(r"f_view\('(\d+)'\)", a.get("onclick", ""))
                if not m:
                    continue
                seq = m.group(1)
                tds = tr.find_all("td")
                title = a.get_text(" ", strip=True)
                date = ""
                for td in reversed(tds):
                    txt = td.get_text(strip=True)
                    if re.match(r"\d{4}-\d{2}-\d{2}", txt):
                        date = txt[:10]
                        break
                items.append((seq, title, date))
                page_seqs.append(seq)
            except Exception as e:
                print(f"    ! row parse error: {e}")
        if not page_seqs:
            break
        # No next page if fewer than a full page of results.
        if len(page_seqs) < 10:
            break
        time.sleep(1.2)
    return items


def fetch_detail(seq):
    """Return (title, date, text) for a detail page, or None."""
    r = get(VIEW_URL, params={"seq": seq})
    if not r:
        return None
    soup = BeautifulSoup(r.text, "html.parser")
    detail = soup.select_one(".board_detail") or soup
    h2 = detail.select_one("h2")
    title = h2.get_text(" ", strip=True) if h2 else ""

    date = ""
    head = detail.select_one(".bo_head")
    if head:
        m = re.search(r"(\d{4}-\d{2}-\d{2})", head.get_text(" ", strip=True))
        if m:
            date = m.group(1)

    body_el = detail.select_one(".se-contents") or detail.select_one(".bo_con")
    text = ""
    if body_el:
        for tag in body_el.select("script, style"):
            tag.decompose()
        text = body_el.get_text("\n", strip=True)
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return title, date, text


# Generic words that must never be used alone as match terms (too noisy).
STOPWORDS = {
    "resolution", "general", "assembly", "council", "security", "summit",
    "process", "declaration", "safety", "governance", "advisory", "body",
    "briefing", "compact", "future", "action", "agreement", "deal", "force",
    "military", "operation", "civilian", "civilians", "infrastructure",
    "strikes", "withdrawal", "regions", "referendum", "anniversary",
    "negotiations", "ceasefire", "peace", "war", "years", "year", "pause",
    "humanitarian", "crisis", "provisional", "measures", "warrant", "arrest",
    "children", "deportation", "phone", "telephone", "minister", "foreign",
    "nuclear", "mobilization", "annexation", "renewed", "collapse",
}


def keywords_for(event):
    topic, _eid, _name, _date, _win, kws = event
    terms = set()
    # For AI governance, generic word-splitting is too noisy: use curated
    # phrases only. For ukraine/gaza, country/actor words are distinctive.
    if topic != "ai_governance":
        for k in kws:
            for w in re.split(r"\s+", k):
                w = w.strip().lower()
                if len(w) >= 4 and w not in STOPWORDS:
                    terms.add(w)
    for f in TOPIC_FALLBACK.get(topic, []):
        terms.add(f.strip().lower())
    return terms


def title_matches(title, terms):
    low = title.lower()
    padded = " " + low + " "
    for term in terms:
        if term in WORD_BOUNDARY_TERMS:
            if re.search(r"\b" + re.escape(term) + r"\b", low):
                return True
        elif term in padded:
            return True
    return False


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    docs = []
    seen_urls = set()
    per_topic = {}
    zero_events = []

    for event in EVENTS:
        topic, event_id, event_name, date_str, window, _kws = event
        center = datetime.strptime(date_str, "%Y-%m-%d")
        fr = (center - timedelta(days=window)).strftime("%Y%m%d")
        to = (center + timedelta(days=window)).strftime("%Y%m%d")
        terms = keywords_for(event)

        print(f"\n[{event_id}] {event_name}  ({fr}..{to})")
        listing = fetch_listing(fr, to)
        print(f"    {len(listing)} items in window")

        # Prefer titles that match keywords; spokesperson statements first.
        def score(item):
            _seq, title, _d = item
            s = 0
            if title_matches(title, terms):
                s += 2
            if "spokesperson" in title.lower() or "statement" in title.lower():
                s += 1
            return s

        candidates = [it for it in listing if title_matches(it[1], terms)]
        candidates.sort(key=score, reverse=True)

        n = 0
        for seq, title, list_date in candidates:
            if n >= PER_EVENT_CAP:
                break
            if len(docs) >= TOTAL_CAP:
                break
            url = f"{VIEW_URL}?seq={seq}"
            if url in seen_urls:
                continue
            try:
                detail = fetch_detail(seq)
                time.sleep(1.3)
                if not detail:
                    continue
                d_title, d_date, text = detail
                if not text or len(text) < MIN_TEXT_LEN:
                    print(f"    - skip (short {len(text) if text else 0}): {title[:50]}")
                    continue
                seen_urls.add(url)
                n += 1
                docs.append({
                    "id": f"KR-{event_id}-{n}",
                    "source": "KR",
                    "topic": topic,
                    "event_id": event_id,
                    "event_name": event_name,
                    "date": d_date or list_date,
                    "title": d_title or title,
                    "url": url,
                    "lang": "en",
                    "text": text,
                    "collected_via": "live_scrape",
                })
                print(f"    + {docs[-1]['date']}  {docs[-1]['title'][:60]}")
            except Exception as e:
                print(f"    ! item error seq={seq}: {e}")

        per_topic.setdefault(topic, 0)
        per_topic[topic] += n
        if n == 0:
            zero_events.append(event_id)
        if len(docs) >= TOTAL_CAP:
            print("\n[!] total cap reached")
            break

    # ensure schema-exact keys/order
    docs = [{k: d.get(k, "") for k in DOCUMENT_SCHEMA} for d in docs]
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(docs, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 60)
    print(f"TOTAL DOCS: {len(docs)}  ->  {OUT_PATH}")
    print("Per-topic:")
    for t, c in sorted(per_topic.items()):
        print(f"  {t:16s} {c}")
    print(f"Events with 0 docs ({len(zero_events)}): {', '.join(zero_events)}")


if __name__ == "__main__":
    main()
