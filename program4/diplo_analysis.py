"""
diplo_analysis.py — 외교 성명문 정량 분석 툴킷 (6개 차원)

세션 2~3에서 학생이 직접 만드는 함수들을 패키지로 정리한 것.
세션 4부터(가자·과제) 이 모듈을 import 해서 재사용한다.

6개 차원
  1. directness_index   직설성   (능동/수동 + 우회표현)        ← spaCy
  2. verb_strength      동사 강도 사다리                        ← spaCy lemma
  3. subject_pattern    주어 패턴 분포                          ← spaCy
  4. mutuality_index    상호성(양면적 표현 밀도)                 ← 사전
  5. hedging_density    완곡어 밀도                             ← 사전
  6. silence_map        침묵 지도(코퍼스 레벨)                  ← coverage

설계 원칙(계획서): "계산은 코드(결정론), 의미 해석은 LLM, 판단은 인간."
규칙 기반 5개는 여기서 결정론적으로 계산하고, claude_semantic()은
LLM 교차검증(framing/미묘한 hedging)을 별도로 제공한다.
"""
import re, json, functools

# ── spaCy 로더 (1회 로드 캐시) ───────────────────────────────────────
@functools.lru_cache(maxsize=1)
def get_nlp(model="en_core_web_sm"):
    import spacy
    return spacy.load(model, disable=["ner", "lemmatizer"]) if False else spacy.load(model)


# ── 1. Directness Index ─────────────────────────────────────────────
CIRCUMLOCUTIONS = [
    "it is regrettable", "cannot but", "one cannot", "it is to be",
    "it should be noted", "it is worth noting", "it is unfortunate",
    "it would appear", "it is hoped", "regrettably", "we are saddened",
]

def directness_index(text, nlp=None):
    """능동절 비율 - 우회표현 페널티. 0(우회적)~1(직설적)."""
    nlp = nlp or get_nlp()
    doc = nlp(text[:100000])
    active = passive = 0
    for tok in doc:
        if tok.dep_ == "nsubjpass" or tok.dep_ == "auxpass":
            passive += 1
        elif tok.dep_ == "nsubj" and tok.head.pos_ in ("VERB", "AUX"):
            active += 1
    base = active / (active + passive) if (active + passive) else 0.5
    low = text.lower()
    circ = sum(low.count(p) for p in CIRCUMLOCUTIONS)
    words = max(len(low.split()), 1)
    penalty = min(0.3, circ / words * 100)  # 우회표현 많을수록 직설성 감점
    return {
        "directness_index": round(max(0, base - penalty), 3),
        "active_clauses": active, "passive_clauses": passive,
        "circumlocutions": circ,
    }


# ── 2. Verb Strength Ladder ─────────────────────────────────────────
VERB_LADDER = {
    "note": 1, "observe": 1, "take note": 1,
    "acknowledge": 2, "recognize": 2, "recognise": 2,
    "regret": 3, "lament": 3,
    "concern": 4, "worry": 4, "trouble": 4,
    "deplore": 5, "denounce": 5, "decry": 5,
    "condemn": 6, "censure": 6,
    "demand": 7, "insist": 7, "require": 7,
}

def verb_strength(text, nlp=None):
    """외교 동사 강도(1 note ~ 7 demand). max/mean + 등장 동사."""
    nlp = nlp or get_nlp()
    doc = nlp(text[:100000])
    hits = []
    for tok in doc:
        lemma = tok.lemma_.lower()
        if lemma in VERB_LADDER and tok.pos_ in ("VERB", "NOUN", "ADJ"):
            hits.append((lemma, VERB_LADDER[lemma]))
    scores = [s for _, s in hits]
    return {
        "verb_strength_max": max(scores) if scores else 0,
        "verb_strength_mean": round(sum(scores) / len(scores), 2) if scores else 0,
        "verbs_found": sorted(set(l for l, _ in hits)),
        "n_strength_verbs": len(hits),
    }


# ── 3. Subject Pattern ──────────────────────────────────────────────
INTL_TERMS = ["international community", "united nations", "security council",
              "general assembly", "the un", "world"]
ALLPARTY_TERMS = ["all parties", "both sides", "all sides", "the parties",
                  "all relevant parties", "both parties", "the two sides"]
NATIONS = ["china", "france", "korea", "russia", "ukraine", "israel",
           "palestine", "the united states", "washington", "moscow",
           "beijing", "the government"]

def _classify_subject(span_text):
    s = span_text.lower().strip()
    if s in ("we", "i", "our", "us"):
        return "first_person"
    if any(t in s for t in ALLPARTY_TERMS):
        return "all_parties"
    if any(t in s for t in INTL_TERMS):
        return "intl_community"
    if any(t in s for t in NATIONS):
        return "national_actor"
    if s in ("it", "there", "this", "that"):
        return "impersonal"
    return "other"

def subject_pattern(text, nlp=None):
    """주절 주어 분포: first_person/national_actor/intl_community/all_parties/impersonal/other."""
    nlp = nlp or get_nlp()
    doc = nlp(text[:100000])
    from collections import Counter
    c = Counter()
    for tok in doc:
        if tok.dep_ in ("nsubj", "nsubjpass"):
            # 주어 명사구 텍스트
            span = doc[tok.left_edge.i: tok.right_edge.i + 1].text
            c[_classify_subject(span if len(span) < 40 else tok.text)] += 1
    total = sum(c.values()) or 1
    dist = {k: round(v / total, 3) for k, v in c.items()}
    return {"subject_dist": dist, "subject_counts": dict(c), "n_subjects": total}


# ── 4. Mutuality Index ──────────────────────────────────────────────
MUTUALITY_TERMS = [
    "mutual", "both sides", "all sides", "all parties", "shared",
    "common interest", "common ground", "win-win", "dialogue",
    "cooperation", "consultation", "peaceful", "negotiation",
    "political settlement", "all relevant parties", "common security",
]

def mutuality_index(text):
    """양면적/상호적 표현 밀도 (1000단어당)."""
    low = text.lower()
    words = max(len(low.split()), 1)
    hits = {t: low.count(t) for t in MUTUALITY_TERMS if low.count(t)}
    total = sum(hits.values())
    return {
        "mutuality_index": round(total / words * 1000, 2),
        "mutuality_hits": hits, "n_mutuality": total,
    }


# ── 5. Hedging Density ──────────────────────────────────────────────
HEDGES = [
    "may ", "might ", "could ", "appears to", "seems to", "possibly",
    "perhaps", "allegedly", "reportedly", "we believe", "it is hoped",
    "would ", "likely", "potentially", "to some extent", "in some cases",
    "it seems", "arguably", "presumably", "apparently",
]

def hedging_density(text):
    """완곡/유보 표현 밀도 (1000단어당)."""
    low = " " + text.lower() + " "
    words = max(len(low.split()), 1)
    hits = {h.strip(): low.count(h) for h in HEDGES if low.count(h)}
    total = sum(hits.values())
    return {
        "hedging_density": round(total / words * 1000, 2),
        "hedging_hits": hits, "n_hedges": total,
    }


# ── 6. Silence Map ──────────────────────────────────────────────────
def silence_map(docs, events, sources=("UN", "KR", "CN", "FR")):
    """사건×소스 커버리지. 0이면 침묵. (event_id, source)->count."""
    from collections import Counter
    cnt = Counter((d["event_id"], d["source"]) for d in docs)
    rows = []
    for topic, eid, name, date, *_ in events:
        row = {"topic": topic, "event_id": eid, "event_name": name, "date": date}
        for s in sources:
            row[s] = cnt.get((eid, s), 0)
        row["silent_sources"] = [s for s in sources if cnt.get((eid, s), 0) == 0]
        rows.append(row)
    return rows


# ── 통합: 한 문서의 규칙기반 5차원 ──────────────────────────────────
def analyze_document(doc, nlp=None):
    nlp = nlp or get_nlp()
    t = doc["text"]
    r = {"id": doc["id"], "source": doc["source"], "topic": doc["topic"],
         "event_id": doc["event_id"], "date": doc["date"]}
    r.update(directness_index(t, nlp))
    r.update(verb_strength(t, nlp))
    r.update(mutuality_index(t))
    r.update(hedging_density(t))
    sp = subject_pattern(t, nlp)
    r["subject_first_person"] = sp["subject_dist"].get("first_person", 0)
    r["subject_all_parties"] = sp["subject_dist"].get("all_parties", 0)
    r["subject_national"] = sp["subject_dist"].get("national_actor", 0)
    return r


# ── Claude 의미 분석 (LLM 교차검증, 키 필요) ────────────────────────
SEMANTIC_SCHEMA = {
    "framing": "한 문장: 이 성명이 사건을 어떻게 규정하는가(누가 가해자/피해자/중립)",
    "blame_target": "가해 주체를 명시했는가? (named / implied / none)",
    "stance_strength": "1(완곡)~5(강경) 정수",
    "mutuality_tone": "양측 균형 강조 정도 1(일방적)~5(매우 양면적) 정수",
    "subtle_hedging": "규칙으로 못 잡는 미묘한 유보가 있으면 인용",
}

def claude_semantic(text, client, model="claude-sonnet-4-6"):
    """Claude로 framing/blame/강도/상호성 의미 분석. client=anthropic.Anthropic()."""
    schema_desc = "\n".join(f"- {k}: {v}" for k, v in SEMANTIC_SCHEMA.items())
    prompt = (
        "다음 외교 성명문을 분석해 JSON으로만 답하라. 키:\n" + schema_desc +
        "\n\n성명문:\n\"\"\"\n" + text[:6000] + "\n\"\"\"\n"
        "반드시 JSON 객체 하나만 출력."
    )
    msg = client.messages.create(
        model=model, max_tokens=600,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = msg.content[0].text
    m = re.search(r"\{.*\}", raw, re.S)
    return json.loads(m.group(0)) if m else {"_raw": raw}


if __name__ == "__main__":
    import os
    here = os.path.dirname(os.path.abspath(__file__))
    docs = json.load(open(os.path.join(here, "data/backup/corpus_clean.json"), encoding="utf-8"))
    nlp = get_nlp()
    print("샘플 분석 (소스별 1건):")
    seen = set()
    for d in docs:
        if d["source"] in seen or d["topic"] != "ukraine":
            continue
        seen.add(d["source"])
        r = analyze_document(d, nlp)
        print(f"\n[{d['source']}] {d['event_id']} {d['date']}")
        print(f"  directness={r['directness_index']} verb_max={r['verb_strength_max']}"
              f"({','.join(r['verbs_found'][:4])}) mutuality={r['mutuality_index']}"
              f" hedging={r['hedging_density']} we={r['subject_first_person']}")
        if len(seen) == 4:
            break
