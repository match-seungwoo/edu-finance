"""
data/raw/{UN,KR,CN,FR}.json 을 하나의 코퍼스로 병합하고 백업을 만든다.

산출물 (data/backup/):
  corpus.json        — 전체 문서 (스키마 정렬)
  corpus.csv         — 동일 내용 CSV (utf-8-sig, 엑셀 호환)
  coverage.csv       — 사건 × 소스 문서 수 매트릭스 (침묵 지도 원천)
  manifest.json      — 수집 요약 (소스별/주제별 카운트, 생성 메타)

이 파일들이 '백업'이다. 라이브 스크래핑이 막히면 노트북은 여기서 로드한다.
"""
import json, csv, glob, os, collections
from events import DOCUMENT_SCHEMA, EVENTS, TOPICS, SOURCES

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "..", "data", "raw")
BACKUP = os.path.join(HERE, "..", "data", "backup")
os.makedirs(BACKUP, exist_ok=True)

# 1) 병합 ---------------------------------------------------------------
docs = []
seen = set()
for f in sorted(glob.glob(os.path.join(RAW, "*.json"))):
    for d in json.load(open(f, encoding="utf-8")):
        key = (d.get("source"), d.get("url"))
        if key in seen:
            continue
        seen.add(key)
        # 스키마 정렬 + 누락 키 방어
        docs.append({k: d.get(k, "") for k in DOCUMENT_SCHEMA})

# 정렬: 주제 → 사건 → 소스
topic_order = {t: i for i, t in enumerate(TOPICS)}
event_order = {e[1]: i for i, e in enumerate(EVENTS)}
src_order = {s: i for i, s in enumerate(SOURCES)}
docs.sort(key=lambda d: (topic_order.get(d["topic"], 9),
                          event_order.get(d["event_id"], 99),
                          src_order.get(d["source"], 9)))

# 2) corpus.json ------------------------------------------------------
with open(os.path.join(BACKUP, "corpus.json"), "w", encoding="utf-8") as fp:
    json.dump(docs, fp, ensure_ascii=False, indent=2)

# 3) corpus.csv -------------------------------------------------------
with open(os.path.join(BACKUP, "corpus.csv"), "w", encoding="utf-8-sig", newline="") as fp:
    w = csv.DictWriter(fp, fieldnames=DOCUMENT_SCHEMA)
    w.writeheader()
    for d in docs:
        row = dict(d)
        row["text"] = row["text"].replace("\r", " ")  # CSV 안전
        w.writerow(row)

# 4) coverage.csv (사건 × 소스) --------------------------------------
counts = collections.Counter((d["event_id"], d["source"]) for d in docs)
with open(os.path.join(BACKUP, "coverage.csv"), "w", encoding="utf-8-sig", newline="") as fp:
    w = csv.writer(fp)
    w.writerow(["topic", "event_id", "event_name", "date"] + list(SOURCES) + ["total"])
    for topic, eid, name, date, _win, _kw in EVENTS:
        row = [topic, eid, name, date]
        tot = 0
        for s in SOURCES:
            n = counts.get((eid, s), 0)
            row.append(n)
            tot += n
        row.append(tot)
        w.writerow(row)

# 5) manifest.json ----------------------------------------------------
by_source = collections.Counter(d["source"] for d in docs)
by_topic = collections.Counter(d["topic"] for d in docs)
events_covered = len(set(d["event_id"] for d in docs))
manifest = {
    "total_docs": len(docs),
    "events_total": len(EVENTS),
    "events_covered": events_covered,
    "by_source": dict(by_source),
    "by_topic": dict(by_topic),
    "sources": {s: SOURCES[s]["name"] for s in SOURCES},
    "schema": DOCUMENT_SCHEMA,
    "note": "라이브 스크래핑 폴백용 백업. scrapers/scrape_*.py 로 재수집 가능.",
}
with open(os.path.join(BACKUP, "manifest.json"), "w", encoding="utf-8") as fp:
    json.dump(manifest, fp, ensure_ascii=False, indent=2)

# 콘솔 요약 -----------------------------------------------------------
print(f"병합 완료: {len(docs)} docs / 사건 {events_covered}/{len(EVENTS)} 커버")
print("소스별:", dict(by_source))
print("주제별:", dict(by_topic))
print("백업 →", os.path.relpath(BACKUP, os.path.join(HERE, "..")))
