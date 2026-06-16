"""
정제 패스: data/backup/corpus.json(raw 병합) → corpus_clean.json + 정제 백업.

raw 스크래핑 데이터의 두 가지 현실 문제를 처리한다.
  (1) false positive: 주제 키워드가 본문에 전혀 없는 문서 (키워드 매칭 노이즈) → 제거
  (2) 거대 문서: 중국 외교부 '일일 정례 브리핑'은 한 페이지에 우크라이나·가자·
      AI·양자관계가 다 섞여 있다(평균 1.8만 자). 주제 관련 문단만 추출해
      다른 소스와 비교 가능한 길이로 만든다.

이 정제 로직 자체가 session1(수집·정제) 강의의 핵심 교보재다:
"공개 데이터를 그대로 쓰면 안 된다. 무엇을 남기고 무엇을 버릴지가 분석의 시작이다."
"""
import json, os, re, csv, collections
from events import DOCUMENT_SCHEMA, EVENTS, TOPICS, SOURCES

HERE = os.path.dirname(os.path.abspath(__file__))
BACKUP = os.path.join(HERE, "..", "data", "backup")

# 주제별 관련성 판정 키워드 (소문자)
TOPIC_KW = {
    "ukraine":        r"ukrain|russia|kyiv|kharkiv|kherson|bucha|donbas|donetsk|luhansk|zaporizh|crimea|moscow",
    "gaza":           r"gaza|israel|palestin|hamas|rafah|hostage|west bank|\bidf\b|jabalia|unrwa|netanyahu",
    "ai_governance":  r"artificial intelligence|\bai\b|machine learning|frontier|algorithm|digital compact|autonomous weapon",
}

LONG_DOC = 6000  # 이보다 길면 주제 문단만 추출


def topical(text, topic):
    return re.search(TOPIC_KW[topic], text.lower()) is not None


def extract_segments(text, topic, ctx=1):
    """긴 브리핑에서 주제 키워드가 든 문단 + 앞쪽 ctx개(질문 캡처)만 추출."""
    paras = [p.strip() for p in re.split(r"\n{1,}", text) if p.strip()]
    pat = re.compile(TOPIC_KW[topic])
    keep = set()
    for i, p in enumerate(paras):
        if pat.search(p.lower()):
            for j in range(max(0, i - ctx), i + 1):
                keep.add(j)
    if not keep:
        return text  # 안전장치(여기 오면 topical()에서 이미 걸러짐)
    return "\n\n".join(paras[i] for i in sorted(keep))


def main():
    docs = json.load(open(os.path.join(BACKUP, "corpus.json"), encoding="utf-8"))
    out, dropped, trimmed = [], 0, 0
    for d in docs:
        if not topical(d["text"], d["topic"]):
            dropped += 1
            continue
        d = dict(d)
        if len(d["text"]) > LONG_DOC:
            seg = extract_segments(d["text"], d["topic"])
            if topical(seg, d["topic"]) and len(seg) >= 200:
                if len(seg) < len(d["text"]):
                    trimmed += 1
                d["text"] = seg
        out.append({k: d.get(k, "") for k in DOCUMENT_SCHEMA})

    # 저장: clean json/csv + 갱신된 coverage/manifest
    with open(os.path.join(BACKUP, "corpus_clean.json"), "w", encoding="utf-8") as fp:
        json.dump(out, fp, ensure_ascii=False, indent=2)
    with open(os.path.join(BACKUP, "corpus_clean.csv"), "w", encoding="utf-8-sig", newline="") as fp:
        w = csv.DictWriter(fp, fieldnames=DOCUMENT_SCHEMA)
        w.writeheader()
        for d in out:
            r = dict(d); r["text"] = r["text"].replace("\r", " ")
            w.writerow(r)

    # coverage_clean.csv
    counts = collections.Counter((d["event_id"], d["source"]) for d in out)
    with open(os.path.join(BACKUP, "coverage_clean.csv"), "w", encoding="utf-8-sig", newline="") as fp:
        w = csv.writer(fp)
        w.writerow(["topic", "event_id", "event_name", "date"] + list(SOURCES) + ["total"])
        for topic, eid, name, date, _w, _k in EVENTS:
            row = [topic, eid, name, date]
            tot = 0
            for s in SOURCES:
                n = counts.get((eid, s), 0); row.append(n); tot += n
            row.append(tot); w.writerow(row)

    by_s = collections.Counter(d["source"] for d in out)
    by_t = collections.Counter(d["topic"] for d in out)
    L = collections.defaultdict(list)
    for d in out: L[d["source"]].append(len(d["text"]))
    print(f"정제: {len(docs)} → {len(out)} docs  (제거 {dropped}, 문단추출 {trimmed})")
    print("소스별:", dict(by_s))
    print("주제별:", dict(by_t))
    print("정제 후 평균 길이:", {s: sum(v)//len(v) for s, v in L.items()})
    print("사건 커버:", len(set(d['event_id'] for d in out)), "/", len(EVENTS))


if __name__ == "__main__":
    main()
