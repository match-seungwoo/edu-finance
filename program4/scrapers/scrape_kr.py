"""
scrape_kr.py — ROK MOFA (Ministry of Foreign Affairs) English statements scraper.

Collects official English press releases / spokesperson statements / briefings /
minister speeches from the ROK MOFA English site for the 30 diplomatic events
defined in events.py and writes them to data/raw/KR.json (DOCUMENT_SCHEMA).

Source boards (all list.do support server-side date-range filtering via
srchFr / srchTo as YYYYMMDD; detail pages: view.do?seq=<seq>):
  - m_5676  Press Releases (incl. spokesperson statements)   [primary]
  - m_5674  Ministry News (FM/VM meetings, phone calls, statements)
  - m_5679  Press Briefings (spokesperson briefings, often Q&A on hot topics)
  - m_5689  Minister Speeches & Published Materials (statements / remarks)
The board search is unreliable, so we pull the date-range listing for each event
window across all boards and filter titles by keyword client-side, then merge.

Behaviour:
  - LOADS any existing data/raw/KR.json, MERGES new results, DEDUPS by url,
    and re-numbers ids per event (KR-<event_id>-<n>). Final count never shrinks.

Engineering: requests.Session (cookie), browser UA, polite sleeps, retry w/
backoff, generous timeouts, dedup by URL, per-item try/except.
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

# Boards to scrape and merge.  m_5676 first so its (often canonical) statements
# get the lowest doc numbers per event.
BOARDS = ["m_5676", "m_5674", "m_5679", "m_5689"]

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
PER_EVENT_CAP = 6           # raised from 3 to grow the corpus
TOTAL_CAP = 90              # raised from 60
MAX_LIST_PAGES = 5          # safety cap on pagination per window
EXTRA_MARGIN_DAYS = 5       # small extra margin added to each event's ±window

# Extra/simpler fallback keyword terms per topic (Korea phrases things its way).
TOPIC_FALLBACK = {
    "ukraine": ["ukraine", "ukrainian", "russia", "russian", "kyiv", "zelensky"],
    "gaza": [
        "gaza", "israel", "israeli", "hamas", "palestin", "middle east",
        "rafah", "two-state", "hostage",
    ],
    # AI terms must be specific: generic words like "summit"/"digital" and the
    # bare token "ai" produce false positives (e.g. "humanitarian AID").
    "ai_governance": [
        "artificial intelligence", "reaim", "bletchley", "ai safety",
        "ai summit", "ai action", "digital compact", "ai governance",
        "ai seoul", "ai global", "responsible ai", "ai in the military",
        "hiroshima ai",
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


def fetch_listing(board, fr, to):
    """Return list of (seq, title, date) within the YYYYMMDD date range."""
    list_url = f"{BASE}/eng/brd/{board}/list.do"
    items = []
    for page in range(1, MAX_LIST_PAGES + 1):
        r = get(list_url, params=list_params(page, fr, to))
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
        time.sleep(1.0)
    return items


def clean_title(t):
    # m_5689 prefixes "[Former]"/"[Incumbent]" and pads with newlines/tabs.
    t = re.sub(r"\s+", " ", t).strip()
    t = re.sub(r"^\[(?:Former|Incumbent)\]\s*", "", t)
    return t


def fetch_detail(board, seq):
    """Return (title, date, text) for a detail page, or None."""
    view_url = f"{BASE}/eng/brd/{board}/view.do"
    r = get(view_url, params={"seq": seq})
    if not r:
        return None
    soup = BeautifulSoup(r.text, "html.parser")
    detail = soup.select_one(".board_detail") or soup
    h2 = detail.select_one("h2")
    title = clean_title(h2.get_text(" ", strip=True)) if h2 else ""

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
        text = text.replace("﻿", "").strip()
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


def text_has_topic(text, terms):
    """Word-boundary aware containment check used for body validation and as
    a secondary filter so briefings (broad titles) still match on content."""
    low = text.lower()
    for term in terms:
        if " " in term:
            if term in low:
                return True
        elif re.search(r"\b" + re.escape(term) + r"\b", low):
            return True
    return False


def title_matches(title, terms):
    low = title.lower()
    padded = " " + low + " "
    for term in terms:
        if term in WORD_BOUNDARY_TERMS:
            if re.search(r"\b" + re.escape(term) + r"\b", low):
                return True
        elif " " in term:
            if term in low:
                return True
        elif term in padded:
            return True
    return False


def load_existing():
    if not os.path.exists(OUT_PATH):
        return []
    try:
        with open(OUT_PATH, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception as e:
        print(f"[!] could not load existing KR.json: {e}")
        return []


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    existing = load_existing()
    print(f"[i] loaded {len(existing)} existing docs from KR.json")

    # docs keyed by url -> doc dict; seed with existing (preserved).
    by_url = {}
    for d in existing:
        url = d.get("url")
        if url and url not in by_url:
            by_url[url] = dict(d)

    seen_urls = set(by_url)
    per_event_existing = {}
    for d in existing:
        per_event_existing.setdefault(d.get("event_id"), 0)
        per_event_existing[d["event_id"]] += 1

    for event in EVENTS:
        topic, event_id, event_name, date_str, window, _kws = event
        center = datetime.strptime(date_str, "%Y-%m-%d")
        margin = window + EXTRA_MARGIN_DAYS
        fr = (center - timedelta(days=margin)).strftime("%Y%m%d")
        to = (center + timedelta(days=margin)).strftime("%Y%m%d")
        terms = keywords_for(event)

        print(f"\n[{event_id}] {event_name}  ({fr}..{to})")

        # gather candidates across all boards, tagged with board.
        candidates = []  # (board, seq, title, date)
        for board in BOARDS:
            listing = fetch_listing(board, fr, to)
            matched = [(board, s, t, d) for (s, t, d) in listing
                       if title_matches(t, terms)]
            if listing:
                print(f"    {board}: {len(listing)} in window, "
                      f"{len(matched)} title-match")
            candidates.extend(matched)
            time.sleep(0.6)

        # spokesperson statements first; press briefings last (broad titles).
        def score(item):
            board, _seq, title, _d = item
            s = 0
            tl = title.lower()
            if "spokesperson" in tl or "statement" in tl:
                s += 2
            if board == "m_5676":
                s += 1
            if board == "m_5679":
                s -= 1
            return s

        candidates.sort(key=score, reverse=True)

        n_existing = per_event_existing.get(event_id, 0)
        n = 0
        for board, seq, title, list_date in candidates:
            if n_existing + n >= PER_EVENT_CAP:
                break
            if len(by_url) >= TOTAL_CAP:
                break
            url = f"{BASE}/eng/brd/{board}/view.do?seq={seq}"
            if url in seen_urls:
                continue
            try:
                detail = fetch_detail(board, seq)
                time.sleep(1.1)
                if not detail:
                    continue
                d_title, d_date, text = detail
                if not text or len(text) < MIN_TEXT_LEN:
                    print(f"    - skip (short {len(text) if text else 0}): {title[:50]}")
                    continue
                # secondary content check: ensure the body really is on-topic.
                if not text_has_topic(text, terms):
                    print(f"    - skip (off-topic body): {title[:50]}")
                    continue
                seen_urls.add(url)
                by_url[url] = {
                    "id": f"KR-{event_id}-X",   # renumbered below
                    "source": "KR",
                    "topic": topic,
                    "event_id": event_id,
                    "event_name": event_name,
                    "date": d_date or list_date,
                    "title": d_title or clean_title(title),
                    "url": url,
                    "lang": "en",
                    "text": text,
                    "collected_via": "live_scrape",
                }
                n += 1
                print(f"    + [{board}] {by_url[url]['date']}  {by_url[url]['title'][:55]}")
            except Exception as e:
                print(f"    ! item error {board} seq={seq}: {e}")

        if len(by_url) >= TOTAL_CAP:
            print("\n[!] total cap reached")
            break

    # ---- drop cross-board content duplicates ----
    # The same statement is often cross-posted on m_5676 and m_5674 under
    # different seqs (=different urls).  Collapse them by a normalized text key,
    # preferring the board listed earliest in BOARDS (m_5676 canonical).
    def board_of(url):
        m = re.search(r"/brd/(m_\d+)/", url)
        return m.group(1) if m else ""

    def body_key(d):
        return re.sub(r"\s+", " ", d.get("text", "")).strip().lower()[:400]

    best_by_body = {}
    for d in by_url.values():
        k = body_key(d)
        if not k:
            continue
        cur = best_by_body.get(k)
        if cur is None:
            best_by_body[k] = d
        else:
            rank_new = BOARDS.index(board_of(d["url"])) if board_of(d["url"]) in BOARDS else 99
            rank_cur = BOARDS.index(board_of(cur["url"])) if board_of(cur["url"]) in BOARDS else 99
            if rank_new < rank_cur:
                best_by_body[k] = d
    keep_urls = {d["url"] for d in best_by_body.values()}
    dropped = len(by_url) - len(keep_urls)
    if dropped:
        print(f"[i] dropped {dropped} cross-board content duplicates")
    by_url = {u: d for u, d in by_url.items() if u in keep_urls}

    # ---- assemble, renumber per event, schema-exact keys ----
    docs = list(by_url.values())

    # group by event_id preserving event order; preserve existing-first order
    # (existing docs keep their relative order, new ones appended after).
    event_order = [e[1] for e in EVENTS]

    def event_rank(d):
        eid = d.get("event_id")
        return event_order.index(eid) if eid in event_order else len(event_order)

    docs.sort(key=event_rank)

    counters = {}
    final = []
    for d in docs:
        eid = d.get("event_id")
        counters[eid] = counters.get(eid, 0) + 1
        d["id"] = f"KR-{eid}-{counters[eid]}"
        final.append({k: d.get(k, "") for k in DOCUMENT_SCHEMA})

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(final, f, ensure_ascii=False, indent=2)

    # ---- report ----
    from collections import Counter
    per_topic = Counter(d["topic"] for d in final)
    per_event = Counter(d["event_id"] for d in final)
    zero_events = [e[1] for e in EVENTS if per_event.get(e[1], 0) == 0]

    print("\n" + "=" * 60)
    print(f"TOTAL DOCS: {len(final)}  (was {len(existing)})  ->  {OUT_PATH}")
    print("Per-topic:")
    for t in ("ukraine", "gaza", "ai_governance"):
        print(f"  {t:16s} {per_topic.get(t, 0)}")
    print(f"Events with 0 docs ({len(zero_events)}): {', '.join(zero_events)}")


if __name__ == "__main__":
    main()
