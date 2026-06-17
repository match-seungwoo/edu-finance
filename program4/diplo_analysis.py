"""
diplo_analysis.py — 외교 성명문 정량 분석 툴킷 (9개 차원)

세션 2~3에서 학생이 직접 만드는 함수들을 패키지로 정리한 것.
세션 4부터(가자·과제) 이 모듈을 import 해서 재사용한다.

핵심 6개 차원
  1. directness_index    직설성   (능동/수동 + 우회표현)        ← spaCy
  2. verb_strength       동사 강도 사다리                       ← spaCy lemma
  3. subject_pattern     주어 패턴 분포                         ← spaCy
  4. mutuality_index     상호성(양면적 표현 밀도, 부정처리)      ← 사전 + 부정범위
  5. hedging_density     완곡어 밀도 (부정처리)                  ← 사전 + 부정범위
  6. silence_map         침묵 지도(코퍼스 레벨)                 ← coverage

확장 3개 차원 (v2)
  7. event_naming        완곡명명 — 사건을 뭐라 부르나           ← 다국어 사전
  8. blame_attribution   귀속 — 누구를 가해자로 지목했나         ← 의존구문 SVO(+coref)
  9. targeted_sentiment  대상별 태도 — 행위자별 감정 비대칭      ← 다국어 사전

기법 강화 (v2)
  · 부정·범위 처리(negation scope): "no mutual interest" 같은 오탐 제거
  · 의존구문 SVO 추출 + 경량 coreference: 직설성·주어·귀속을 "누가-무엇을" 그래프로
  · 원어 분석(cross-lingual): en/ko/zh/fr 사전·모델로 원문 직접 측정

설계 원칙(계획서): "계산은 코드(결정론), 의미 해석은 LLM, 판단은 인간."
규칙 기반 차원은 결정론적으로 계산하고, claude_semantic()은 LLM 교차검증을 제공한다.
"""
import re, json, functools

# ── spaCy 로더 (1회 로드 캐시) ───────────────────────────────────────
@functools.lru_cache(maxsize=1)
def get_nlp(model="en_core_web_sm"):
    import spacy
    return spacy.load(model)


# 원어 분석용 다국어 모델 로더 (cross-lingual)
#   사용 전 모델 설치 필요:
#     python -m spacy download fr_core_news_sm zh_core_web_sm ko_core_news_sm
_LANG_MODEL = {"en": "en_core_web_sm", "fr": "fr_core_news_sm",
               "zh": "zh_core_web_sm", "ko": "ko_core_news_sm"}

@functools.lru_cache(maxsize=4)
def get_nlp_multi(lang="en"):
    """언어별 spaCy 모델. 미설치 시 안내 메시지와 함께 None 반환."""
    import spacy
    name = _LANG_MODEL.get(lang, "en_core_web_sm")
    try:
        return spacy.load(name)
    except OSError:
        print(f"⚠️ '{name}' 미설치 — `python -m spacy download {name}` 후 사용 (lang={lang})")
        return None


# ── 부정·범위 처리 (negation scope) ─────────────────────────────────
# 사전 매칭 시 바로 앞 구간에 부정어가 있으면 카운트에서 제외한다.
# 띄어쓰기 없는 언어(zh/ko)는 글자 단위 좁은 창을 쓴다.
NEGATORS = {
    "en": [" not ", " no ", "n't", " never ", " without ", " neither ", " nor ",
           " fails to ", " lack of ", " far from ", " no longer ", " cannot ",
           " refuse", " rejects ", " denies "],
    "fr": [" ne ", " pas ", " non ", " jamais ", " sans ", " aucun", " ni ", " refuse"],
    "ko": ["않", "못", "없", "아니", "결코", "거부", "부정"],
    "zh": ["不", "没", "无", "未", "非", "拒", "否认"],
}
_NEG_WINDOW = {"en": 32, "fr": 32, "ko": 8, "zh": 8}

def _count_nonneg(low, term, lang="en", handle_negation=True):
    """low(소문자 텍스트)에서 term 출현 중 '부정되지 않은' 횟수."""
    if not handle_negation:
        return low.count(term)
    negs = NEGATORS.get(lang, NEGATORS["en"])
    win = _NEG_WINDOW.get(lang, 32)
    n, i = 0, low.find(term)
    while i != -1:
        pre = low[max(0, i - win):i]
        if not any(g in pre for g in negs):
            n += 1
        i = low.find(term, i + len(term))
    return n


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


# ── 4. Mutuality Index (다국어 + 부정처리) ──────────────────────────
MUTUALITY_TERMS = [  # en 기본 (s2/s3 노트북 호환 유지)
    "mutual", "both sides", "all sides", "all parties", "shared",
    "common interest", "common ground", "win-win", "dialogue",
    "cooperation", "consultation", "peaceful", "negotiation",
    "political settlement", "all relevant parties", "common security",
]
MUTUALITY_LEX = {
    "en": MUTUALITY_TERMS,
    "ko": ["상호", "양측", "모든 당사자", "공동", "대화", "협력", "협의",
           "평화적", "협상", "관련 당사자", "함께", "공동이익"],
    "zh": ["相互", "双方", "各方", "共同", "对话", "合作", "协商",
           "和平", "谈判", "共赢", "有关各方", "共同利益"],
    "fr": ["mutuel", "les deux parties", "toutes les parties", "commun",
           "dialogue", "coopération", "consultation", "pacifique",
           "négociation", "intérêt commun", "ensemble"],
}

def _word_count(text, lang):
    return max(len(text) // 2, 1) if lang in ("zh",) else max(len(text.split()), 1)

def mutuality_index(text, lang="en", handle_negation=True):
    """양면적/상호적 표현 밀도 (1000단어당). 부정범위 처리 + 다국어."""
    low = " " + (text.lower() if lang != "zh" else text) + " "
    words = _word_count(low, lang)
    terms = MUTUALITY_LEX.get(lang, MUTUALITY_TERMS)
    hits = {}
    for t in terms:
        c = _count_nonneg(low, t, lang, handle_negation)
        if c:
            hits[t] = c
    total = sum(hits.values())
    return {
        "mutuality_index": round(total / words * 1000, 2),
        "mutuality_hits": hits, "n_mutuality": total,
    }


# ── 5. Hedging Density (다국어 + 부정처리) ──────────────────────────
HEDGES = [  # en 기본 (노트북 호환)
    "may ", "might ", "could ", "appears to", "seems to", "possibly",
    "perhaps", "allegedly", "reportedly", "we believe", "it is hoped",
    "would ", "likely", "potentially", "to some extent", "in some cases",
    "it seems", "arguably", "presumably", "apparently",
]
HEDGE_LEX = {
    "en": HEDGES,
    "ko": ["수 있", "것으로 보", "아마", "듯", "가능성", "추정", "보인다", "예상"],
    "zh": ["可能", "也许", "似乎", "或许", "据称", "据报道", "看来", "大概", "应该"],
    "fr": ["peut-être", "pourrait", "semble", "il paraît", "probablement",
           "apparemment", "vraisemblablement", "éventuellement"],
}

def hedging_density(text, lang="en", handle_negation=True):
    """완곡/유보 표현 밀도 (1000단어당). 부정범위 처리 + 다국어."""
    low = " " + (text.lower() if lang != "zh" else text) + " "
    words = _word_count(low, lang)
    terms = HEDGE_LEX.get(lang, HEDGES)
    hits = {}
    for h in terms:
        c = _count_nonneg(low, h, lang, handle_negation)
        if c:
            hits[h.strip()] = c
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


# ── 7. Event Naming (완곡명명, 다국어) ──────────────────────────────
# 같은 사건을 뭐라 부르나? 가중치 3=강한 규정(invasion/genocide) … 0=완곡(situation/operation)
EVENT_NAMING = {
    "ukraine": {
        "en": {"war of aggression": 3, "invasion": 3, "aggression": 3, "war": 2,
               "assault": 2, "offensive": 2, "attack": 2, "hostilities": 1,
               "conflict": 1, "crisis": 1, "situation": 0,
               "special military operation": 0, "military operation": 0},
        "ko": {"침공": 3, "침략": 3, "전쟁": 2, "공세": 2, "공격": 2,
               "분쟁": 1, "위기": 1, "사태": 0, "특별군사작전": 0, "군사작전": 0},
        "zh": {"入侵": 3, "侵略": 3, "战争": 2, "进攻": 2, "袭击": 2,
               "冲突": 1, "危机": 1, "局势": 0, "特别军事行动": 0, "军事行动": 0},
        "fr": {"invasion": 3, "agression": 3, "guerre": 2, "offensive": 2,
               "attaque": 2, "hostilités": 1, "conflit": 1, "crise": 1,
               "situation": 0, "opération militaire": 0},
    },
    "gaza": {
        "en": {"genocide": 3, "ethnic cleansing": 3, "war crime": 3, "massacre": 3,
               "atrocity": 3, "invasion": 2, "war": 2, "offensive": 2,
               "bombardment": 2, "attack": 2, "escalation": 1, "hostilities": 1,
               "conflict": 1, "crisis": 1, "situation": 0, "operation": 0},
        "ko": {"학살": 3, "대량학살": 3, "전쟁범죄": 3, "만행": 3, "전쟁": 2,
               "공습": 2, "공격": 2, "공세": 2, "분쟁": 1, "위기": 1,
               "사태": 0, "작전": 0},
        "zh": {"种族灭绝": 3, "屠杀": 3, "战争罪": 3, "暴行": 3, "战争": 2,
               "轰炸": 2, "袭击": 2, "进攻": 2, "冲突": 1, "危机": 1,
               "局势": 0, "行动": 0},
        "fr": {"génocide": 3, "crime de guerre": 3, "massacre": 3, "atrocité": 3,
               "guerre": 2, "offensive": 2, "bombardement": 2, "attaque": 2,
               "hostilités": 1, "conflit": 1, "crise": 1, "situation": 0, "opération": 0},
    },
    # AI 거버넌스: 위협 프레임(threat/risk) vs 기회 프레임(opportunity/benefit)
    "ai_governance": {
        "en": {"existential risk": 3, "threat": 2, "danger": 2, "risk": 1,
               "challenge": 1, "safety": 1, "opportunity": 0, "benefit": 0,
               "potential": 0},
    },
}

def event_naming(text, topic, lang="en"):
    """사건 명명 등록(register). escalation 0(완곡)~3(강한 규정)."""
    lex = EVENT_NAMING.get(topic, {}).get(lang, {})
    low = text.lower() if lang != "zh" else text
    found = {}
    for term, w in lex.items():
        c = low.count(term if lang in ("zh", "ko") else term)
        if c:
            found[term] = c
    if not found:
        return {"naming_escalation": None, "naming_max": None,
                "naming_dominant": None, "naming_terms": {}}
    weighted = sum(lex[t] * c for t, c in found.items()) / sum(found.values())
    dominant = max(found, key=lambda t: (found[t], lex[t]))
    return {
        "naming_escalation": round(weighted, 2),
        "naming_max": max(lex[t] for t in found),
        "naming_dominant": dominant, "naming_terms": found,
    }


# ── 의존구문 SVO 추출 + 경량 coreference ────────────────────────────
def _coref_map(doc):
    """경량 coref: 대명사(it/they/he/she)를 직전 등장 개체(GPE/ORG/PERSON)로."""
    ents = [(e.start, e.text) for e in doc.ents
            if e.label_ in ("GPE", "ORG", "PERSON", "NORP")]
    PRON = {"it", "they", "he", "she", "them", "this country"}
    m = {}
    for tok in doc:
        if tok.text.lower() in PRON:
            prev = [t for (s, t) in ents if s < tok.i]
            if prev:
                m[tok.i] = prev[-1]
    return m

def extract_svo(text, nlp=None, resolve_coref=True):
    """(주어, 동사, 목적어) 삼항 추출. resolve_coref 시 대명사 주어 치환."""
    nlp = nlp or get_nlp()
    doc = nlp(text[:100000])
    cmap = _coref_map(doc) if resolve_coref else {}
    out = []
    for tok in doc:
        if tok.pos_ != "VERB":
            continue
        subj = [w for w in tok.children if w.dep_ == "nsubj"]
        subjp = [w for w in tok.children if w.dep_ == "nsubjpass"]
        agent = []
        for w in tok.children:
            if w.dep_ == "agent":
                agent += [c for c in w.children if c.dep_ == "pobj"]
        obj = [w for w in tok.children if w.dep_ in ("dobj", "obj")]
        def _txt(w):
            return cmap.get(w.i, doc[w.left_edge.i:w.right_edge.i + 1].text)
        out.append({
            "verb": tok.lemma_.lower(),
            "subject": _txt(subj[0]) if subj else (_txt(agent[0]) if agent else None),
            "passive": bool(subjp) and not agent,
            "object": _txt(obj[0]) if obj else (_txt(subjp[0]) if subjp else None),
        })
    return out


# ── 8. Blame Attribution (귀속, SVO 기반) ───────────────────────────
AGGRESSIVE_VERBS = {
    "ukraine": {"en": ["attack", "invade", "strike", "bomb", "shell", "kill",
                       "occupy", "annex", "seize", "violate", "displace", "target",
                       "destroy", "launch", "threaten", "abduct", "deport", "shell"]},
    "gaza": {"en": ["attack", "strike", "bomb", "kill", "besiege", "occupy",
                    "displace", "target", "destroy", "massacre", "abduct", "fire",
                    "raid", "starve", "bombard", "violate"]},
}
PERPETRATORS = {
    "ukraine": {"en": ["russia", "russian", "moscow", "kremlin", "putin"],
                "ko": ["러시아", "모스크바", "푸틴"], "zh": ["俄罗斯", "俄方", "莫斯科"],
                "fr": ["russie", "russe", "moscou", "poutine"]},
    "gaza": {"en": ["israel", "israeli", "idf", "hamas"],
             "ko": ["이스라엘", "하마스"], "zh": ["以色列", "哈马斯"],
             "fr": ["israël", "israélien", "hamas"]},
}

def blame_attribution(text, nlp=None, topic="ukraine", lang="en", resolve_coref=True):
    """가해 행위의 귀속. named=가해주체 명시, obscured=행위자 가린 수동.
       blame_directness = named/(named+obscured), 1=가해자 직접 지목."""
    verbs = set(AGGRESSIVE_VERBS.get(topic, {}).get("en", []))
    perps = PERPETRATORS.get(topic, {}).get(lang, PERPETRATORS.get(topic, {}).get("en", []))
    named, obscured = 0, 0
    actors = {}
    for tr in extract_svo(text, nlp, resolve_coref):
        if tr["verb"] not in verbs:
            continue
        subj = (tr["subject"] or "").lower()
        if tr["passive"] and not subj:
            obscured += 1                       # "civilians were killed" (행위자 가림)
        elif any(p in subj for p in perps):
            named += 1                          # "Russia attacked …" (직접 지목)
            for p in perps:
                if p in subj:
                    actors[p] = actors.get(p, 0) + 1
                    break
    total = named + obscured
    return {
        "blame_named": named, "blame_obscured": obscured,
        "blame_directness": round(named / total, 2) if total else None,
        "actors_blamed": actors,
    }


# ── 9. Targeted Sentiment (대상별 태도, 다국어) ─────────────────────
ACTORS = {
    "ukraine": {"en": {"Russia": ["russia", "russian", "moscow", "kremlin", "putin"],
                       "Ukraine": ["ukraine", "ukrainian", "kyiv", "zelensky"]}},
    "gaza": {"en": {"Israel": ["israel", "israeli", "idf", "netanyahu"],
                    "Palestinians": ["palestin", "gaza", "hamas"]}},
}
SENT_NEG = {"en": ["condemn", "violat", "illegal", "brutal", "atrocit", "aggress",
                   "unacceptable", "kill", "attack", "crime", "occupation", "terror",
                   "threat", "destroy", "deplore", "massacre", "abduct",
                   "indiscriminate", "disproportionate", "deliberate"]}
SENT_POS = {"en": ["support", "solidarity", "defend", "legitimate", "protect",
                   "sovereignty", "right to", "welcome", "commend", "assist", "aid",
                   "self-defen", "territorial integrity"]}

def _split_sents(text, lang):
    return re.split(r"[.!?。！？\n]+", text)

def targeted_sentiment(text, topic, lang="en"):
    """행위자별 감정(-1~+1)과 비대칭. most_criticized = 가장 부정적으로 다룬 행위자."""
    actors = ACTORS.get(topic, {}).get(lang, ACTORS.get(topic, {}).get("en", {}))
    neg = SENT_NEG.get(lang, SENT_NEG["en"])
    pos = SENT_POS.get(lang, SENT_POS["en"])
    res = {}
    for sent in _split_sents(text.lower(), lang):
        for actor, aliases in actors.items():
            if any(a in sent for a in aliases):
                p = sum(sent.count(w) for w in pos)
                n = sum(sent.count(w) for w in neg)
                d = res.setdefault(actor, [0, 0, 0])
                d[0] += p; d[1] += n; d[2] += 1
    sentiment = {}
    for actor, (p, n, m) in res.items():
        if p + n:
            sentiment[actor] = round((p - n) / (p + n), 2)
    vals = [v for v in sentiment.values()]
    most_crit = min(sentiment, key=sentiment.get) if sentiment else None
    return {
        "targeted_sentiment": sentiment,
        "most_criticized": most_crit,
        "sentiment_gap": round(max(vals) - min(vals), 2) if len(vals) > 1 else None,
    }


# ── 통합: 한 문서의 9개 차원 ────────────────────────────────────────
def analyze_document(doc, nlp=None):
    nlp = nlp or get_nlp()
    t = doc["text"]
    lang = doc.get("lang", "en")
    r = {"id": doc["id"], "source": doc["source"], "topic": doc["topic"],
         "event_id": doc["event_id"], "date": doc["date"]}
    # 핵심 6차원
    r.update(directness_index(t, nlp))
    r.update(verb_strength(t, nlp))
    r.update(mutuality_index(t, lang))
    r.update(hedging_density(t, lang))
    sp = subject_pattern(t, nlp)
    r["subject_first_person"] = sp["subject_dist"].get("first_person", 0)
    r["subject_all_parties"] = sp["subject_dist"].get("all_parties", 0)
    r["subject_national"] = sp["subject_dist"].get("national_actor", 0)
    # 확장 3차원
    en = event_naming(t, doc["topic"], lang)
    r["naming_escalation"] = en["naming_escalation"]
    r["naming_dominant"] = en["naming_dominant"]
    bl = blame_attribution(t, nlp, doc["topic"], lang)
    r["blame_directness"] = bl["blame_directness"]
    r["blame_named"] = bl["blame_named"]
    r["blame_obscured"] = bl["blame_obscured"]
    ts = targeted_sentiment(t, doc["topic"], lang)
    r["most_criticized"] = ts["most_criticized"]
    r["sentiment_gap"] = ts["sentiment_gap"]
    # 행위자별 세부 점수는 targeted_sentiment()로 별도 조회 (행은 평탄 유지)
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
    print("샘플 분석 — 9개 차원 (우크라이나, 소스별 1건):")
    seen = set()
    for d in docs:
        if d["source"] in seen or d["topic"] != "ukraine":
            continue
        seen.add(d["source"])
        r = analyze_document(d, nlp)
        print(f"\n[{d['source']}] {d['event_id']} {d['date']}")
        print(f"  directness={r['directness_index']} verb_max={r['verb_strength_max']}"
              f" mutuality={r['mutuality_index']} hedging={r['hedging_density']}")
        ts = targeted_sentiment(d["text"], d["topic"], d.get("lang", "en"))
        print(f"  naming={r['naming_dominant']}({r['naming_escalation']})"
              f" blame_directness={r['blame_directness']}"
              f"(named {r['blame_named']}/obscured {r['blame_obscured']})"
              f" most_criticized={r['most_criticized']} ts={ts['targeted_sentiment']}")
        if len(seen) == 4:
            break

    # ── 부정처리 검증 ──
    print("\n부정처리(negation) 검증:")
    pos = "We seek mutual cooperation and dialogue."
    neg = "There is no mutual interest and no cooperation here."
    print(f"  긍정문 mutuality n={mutuality_index(pos)['n_mutuality']} (기대 ≥2)")
    print(f"  부정문 mutuality n={mutuality_index(neg)['n_mutuality']} "
          f"vs 부정무시 n={mutuality_index(neg, handle_negation=False)['n_mutuality']}")

    # ── 원어(cross-lingual) 검증: 실제 외교 표현으로 사전 동작 확인 ──
    print("\n원어(cross-lingual) 사전 검증 — 실제 외교 표현:")
    samples = [
        ("zh", "ukraine", "中方呼吁有关各方through对话与谈判和平解决乌克兰危机，反对战争。"),
        ("fr", "ukraine", "La France condamne l'invasion et l'agression de la Russie en Ukraine."),
        ("ko", "gaza", "정부는 모든 당사자에게 대화를 통한 평화적 해결을 촉구하며 학살을 규탄한다."),
    ]
    for lang, topic, txt in samples:
        m = mutuality_index(txt, lang)
        nm = event_naming(txt, topic, lang)
        print(f"  [{lang}] mutuality={m['mutuality_index']} hits={list(m['mutuality_hits'])} "
              f"| naming={nm['naming_dominant']}({nm['naming_escalation']})")
