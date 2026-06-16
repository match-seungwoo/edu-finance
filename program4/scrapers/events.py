"""
외교 성명문 문화코드 분석 프로젝트 — 사건(이벤트) 정의 + 문서 스키마

세 주제군(코퍼스 3종)에 대한 주요 변곡점 사건과, 각 소스 스크래핑에 쓸
검색 키워드/날짜창(±days)을 한 곳에 모은다. 모든 스크래퍼와 노트북은
이 파일을 단일 진실 공급원(single source of truth)으로 사용한다.

문서 스키마 (DOCUMENT_SCHEMA):
  id            : "<source>-<event_id>-<n>"  전역 유일 ID
  source        : UN | KR | CN | FR
  topic         : ukraine | gaza | ai_governance
  event_id      : 사건 식별자 (ukr01 ...)
  event_name    : 사건명(영문)
  date          : 문서 발표일 YYYY-MM-DD (미상이면 "")
  title         : 문서 제목
  url           : 원문 링크
  lang          : 원문 언어 (en/ko/zh/fr)
  text          : 본문 전문(plain text)
  collected_via : live_scrape | backup | archive
"""

DOCUMENT_SCHEMA = [
    "id", "source", "topic", "event_id", "event_name",
    "date", "title", "url", "lang", "text", "collected_via",
]

SOURCES = {
    "UN": {"name": "United Nations",        "base": "https://press.un.org/en",       "lang": "en"},
    "KR": {"name": "ROK MOFA",              "base": "https://www.mofa.go.kr/eng",    "lang": "en"},
    "CN": {"name": "PRC MFA",               "base": "https://www.fmprc.gov.cn/eng",  "lang": "en"},
    "FR": {"name": "France Diplomatie",     "base": "https://www.diplomatie.gouv.fr/en", "lang": "en"},
}

# topic, event_id, name(en), 대표일(YYYY-MM-DD), window(±days), 검색 키워드들
EVENTS = [
    # ── 주제1: 우크라이나 전쟁 (12) — 2022-02-24~ ──────────────────────────
    ("ukraine", "ukr01", "Russian invasion begins",            "2022-02-24", 14, ["Ukraine invasion", "Russia Ukraine military operation"]),
    ("ukraine", "ukr02", "UNGA ES-11/1 resolution",            "2022-03-02", 10, ["General Assembly Ukraine resolution aggression"]),
    ("ukraine", "ukr03", "Bucha civilian killings",            "2022-04-04", 14, ["Bucha civilians Ukraine"]),
    ("ukraine", "ukr04", "Partial mobilization & nuclear rhetoric", "2022-09-21", 14, ["Putin mobilization nuclear Ukraine"]),
    ("ukraine", "ukr05", "Annexation of four regions",         "2022-09-30", 14, ["Russia annexation Ukraine regions referendum"]),
    ("ukraine", "ukr06", "Mass strikes on energy infrastructure", "2022-10-10", 14, ["Ukraine missile strikes infrastructure civilian"]),
    ("ukraine", "ukr07", "Kherson liberation",                 "2022-11-11", 14, ["Kherson Ukraine withdrawal"]),
    ("ukraine", "ukr08", "One-year mark / UNGA resolution",    "2023-02-23", 10, ["Ukraine anniversary General Assembly resolution peace"]),
    ("ukraine", "ukr09", "Kakhovka dam destruction",           "2023-06-06", 14, ["Kakhovka dam Ukraine"]),
    ("ukraine", "ukr10", "ICC arrest warrant (Putin)",         "2023-03-17", 14, ["ICC arrest warrant Putin deportation children"]),
    ("ukraine", "ukr11", "Two-year mark",                      "2024-02-24", 14, ["Ukraine two years war"]),
    ("ukraine", "ukr12", "Peace / ceasefire negotiations",     "2025-03-01", 30, ["Ukraine ceasefire peace negotiations"]),

    # ── 주제2: 가자 / 이스라엘-팔레스타인 (10) — 2023-10-07~ ───────────────
    ("gaza", "gaza01", "October 7 attack",                     "2023-10-07", 10, ["Israel Hamas attack October", "Israel Gaza"]),
    ("gaza", "gaza02", "Gaza ground operation begins",         "2023-10-27", 14, ["Gaza ground operation Israel"]),
    ("gaza", "gaza03", "First truce & hostage release",        "2023-11-24", 10, ["Gaza truce hostage release humanitarian pause"]),
    ("gaza", "gaza04", "Humanitarian crisis declaration",      "2023-12-08", 14, ["Gaza humanitarian crisis ceasefire Security Council"]),
    ("gaza", "gaza05", "ICJ provisional measures",             "2024-01-26", 10, ["ICJ South Africa Israel genocide provisional measures"]),
    ("gaza", "gaza06", "ICC arrest warrant applications",      "2024-05-20", 14, ["ICC arrest warrant Netanyahu Hamas"]),
    ("gaza", "gaza07", "Rafah operation",                      "2024-05-06", 14, ["Rafah operation Gaza Israel"]),
    ("gaza", "gaza08", "Ceasefire deal",                       "2025-01-15", 14, ["Gaza ceasefire deal hostage"]),
    ("gaza", "gaza09", "Ceasefire collapse / renewed strikes", "2025-03-18", 14, ["Gaza ceasefire collapse strikes"]),
    ("gaza", "gaza10", "Gaza City military operation",         "2025-08-01", 21, ["Gaza City military operation"]),

    # ── 주제3(과제): AI 거버넌스 (8) — 2023~ ──────────────────────────────
    ("ai_governance", "ai01", "G7 Hiroshima AI Process",       "2023-05-19", 21, ["G7 Hiroshima AI process artificial intelligence"]),
    ("ai_governance", "ai02", "Bletchley Declaration",         "2023-11-01", 14, ["Bletchley AI Safety Summit declaration"]),
    ("ai_governance", "ai03", "UN AI resolution A/RES/78/265", "2024-03-21", 14, ["UN General Assembly artificial intelligence resolution"]),
    ("ai_governance", "ai04", "AI Seoul Summit",               "2024-05-21", 14, ["AI Seoul Summit safety"]),
    ("ai_governance", "ai05", "UN High-Level Advisory Body on AI", "2024-09-19", 21, ["UN advisory body artificial intelligence governance"]),
    ("ai_governance", "ai06", "Security Council AI briefing",  "2024-07-02", 21, ["Security Council artificial intelligence briefing"]),
    ("ai_governance", "ai07", "Global Digital Compact",        "2024-09-22", 14, ["Global Digital Compact Summit of the Future"]),
    ("ai_governance", "ai08", "Paris AI Action Summit",        "2025-02-10", 14, ["Paris AI Action Summit"]),
]

TOPICS = {
    "ukraine":        "우크라이나 전쟁",
    "gaza":           "가자 / 이스라엘-팔레스타인",
    "ai_governance":  "AI 거버넌스",
}


def events_for(topic):
    return [e for e in EVENTS if e[0] == topic]


if __name__ == "__main__":
    from collections import Counter
    c = Counter(e[0] for e in EVENTS)
    print("총 사건:", len(EVENTS))
    for t, n in c.items():
        print(f"  {t:16s} {n}건 — {TOPICS[t]}")
