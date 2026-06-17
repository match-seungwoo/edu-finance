# -*- coding: utf-8 -*-
"""session2.ipynb 빌더 — 구조 분석 (주제1: 우크라이나, spaCy)"""
from nb import md, code, save

SETUP = r'''# ── 프로젝트 환경 자동 설정 (Colab / 로컬 공용) ───────────────────────
# 이 셀은 모든 세션 노트북 맨 위에 동일하게 들어간다. 그냥 실행만 하면 된다.
import os, sys, json, glob

def find_project():
    """data/backup/corpus_clean.json 이 있는 program4 폴더를 찾는다."""
    cands = [".", "program4", "..", "../program4", "/content/program4",
             "/content/edu/program4", os.path.expanduser("~/program4")]
    for c in cands:
        if os.path.exists(os.path.join(c, "data", "backup", "corpus_clean.json")):
            return os.path.abspath(c)
    return None

PROJECT = find_project()
if PROJECT is None:
    print("⚠️  데이터를 찾지 못했습니다. 아래 둘 중 하나로 해결하세요:")
    print("  (A) Colab: 좌측 파일창에 program4 폴더를 통째로 업로드")
    print("  (B) Colab: !git clone <이 강의 repo 주소>  후 다시 실행")
else:
    sys.path.insert(0, PROJECT)
    os.chdir(PROJECT)
    print("✅ 프로젝트 경로:", PROJECT)
'''

cells = [
md("""# Session 2 — 외교 성명문, *어떻게* 말했나
### 주제 1: 우크라이나 전쟁 · 구조 분석 (spaCy)

> **오늘 한 문장:** "지난주는 *누가* 말했나(침묵 지도)였다. 오늘은 **어떻게 말했나**.
> `Russia attacked civilians` 와 `civilians were attacked` —
> **능동/수동의 차이를 숫자로** 잡아낸다."

지난 세션(S1) 복습 2줄:
1. 4개 소스(UN·한국·중국·프랑스) 우크라이나 성명문 **157건**을 정제해 `data/ukraine_working.json` 에 저장했다.
2. **침묵 지도** — 누가 어떤 사건에 말하지 않았는지 — 를 그렸다. "침묵도 데이터다."

오늘의 목표 — **문장의 *구조*를 자동으로 읽는다.** 손으로 만들 세 가지 지표 + 확장 한 차원:

1. **Directness Index (직설성)** — 능동절 vs 수동절 + 우회표현 페널티. 0~1.
2. **Verb Strength Ladder (동사 강도)** — note(1) < ... < condemn(6) < demand(7).
3. **Subject Pattern (주어 패턴)** — 누가 문장의 주어로 등장하나 (우리/국가/국제사회/...).
4. **(확장) Blame Attribution (귀속)** — 의존구문 SVO로 "가해자를 명시했나, 가렸나"를 잰다 (9개 차원 중 8번).

> 💡 **운영 방식:** 셀을 위에서 아래로 하나씩 실행한다.
> `# TODO` 가 보이면 직접 채우고, 바로 아래 `# CHECK` 셀을 실행해 `✅` 가 떠야 다음으로."""),

md("## Step 0 — 환경 설정\n라이브러리를 설치하고, 프로젝트 폴더를 찾는다. (S1과 동일한 셀)"),
code('!pip install spacy plotly -q\n!python -m spacy download en_core_web_sm -q'),
code(SETUP),

md("""## Step 1 — 오늘의 데이터 불러오기 + 안전망
S1이 저장한 `data/ukraine_working.json`(우크라이나 157건)을 쓴다.
혹시 그 파일이 없어도(노트북을 따로 돌렸어도) **백업 코퍼스에서 직접 우크라이나만 걸러** 동작하게 한다.
분석은 항상 "데이터가 진짜 있나"부터 확인한다."""),
code(r'''import pandas as pd, json, os

working = os.path.join(PROJECT, "data", "ukraine_working.json")
if os.path.exists(working):
    ukr = pd.read_json(working)
    print("✅ S1 산출물 사용:", working)
else:
    # 안전망: 백업 코퍼스에서 ukraine 만 필터
    docs = json.load(open(os.path.join(PROJECT, "data", "backup", "corpus_clean.json"), encoding="utf-8"))
    ukr = pd.DataFrame([d for d in docs if d["topic"] == "ukraine"])
    print("ℹ️  S1 파일이 없어 백업에서 ukraine 필터로 복원했다.")

print("우크라이나 문서:", len(ukr), "건")
print(ukr.groupby("source").size().to_dict())'''),
code(r'''# CHECK Step1 — 데이터가 실제로 있고 4개 소스가 다 들어있는지
try:
    assert len(ukr) > 50, "문서가 너무 적다"
    assert set(ukr["source"].unique()) >= {"UN","KR","CN","FR"}, "소스 4종이 안 보인다"
    assert set(ukr["topic"].unique()) == {"ukraine"}, "ukraine 외 주제가 섞였다"
    print("✅ PASS — 우크라이나", len(ukr), "건, 4개 소스 확보")
except AssertionError as e:
    print("❌ FAIL —", e)'''),

md("""## Step 2 — spaCy 소개: 문장을 '쪼개서' 본다

지금까지 텍스트는 그냥 **글자 덩어리**였다. spaCy는 문장을 읽어 각 단어(token)에
**품사·기본형·문법역할**을 붙여준다. 우리가 볼 세 가지 속성:

| 속성 | 뜻 | 예 |
|---|---|---|
| `token.text` | 단어 원형 그대로 | `condemned` |
| `token.lemma_` | **기본형(lemma)** | `condemn` ← 시제/변화 제거 |
| `token.pos_` | 품사 (VERB/NOUN/...) | `VERB` |
| `token.dep_` | **문법 역할** (의존관계) | `nsubj`(주어) / `nsubjpass`(수동 주어) |

`nsubj`(능동 주어)와 `nsubjpass`(수동태 주어) — 이 둘의 차이가 오늘의 핵심이다."""),
code(r'''import spacy
nlp = spacy.load("en_core_web_sm")   # 영어 소형 모델 (빠름)

# 같은 사건, 두 가지 말하기 — 능동 vs 수동
s_active  = "Russia attacked Ukrainian civilians."
s_passive = "Civilians were attacked."

for label, sent in [("능동(active)", s_active), ("수동(passive)", s_passive)]:
    print(f"\n=== {label}: {sent}")
    doc = nlp(sent)
    print(f"  {'text':12}{'lemma':12}{'pos':8}{'dep'}")
    for t in doc:
        print(f"  {t.text:12}{t.lemma_:12}{t.pos_:8}{t.dep_}")'''),
md("""> **눈으로 확인하자.**
> - 능동: `Russia` 의 `dep_` 가 **`nsubj`** → "러시아가 (무엇을) 했다". 행위자가 드러난다.
> - 수동: `Civilians` 의 `dep_` 가 **`nsubjpass`**, `were` 가 **`auxpass`** → "당했다". **누가** 했는지 사라진다.
>
> 외교 성명에서 수동태는 종종 **책임 주체를 흐리는** 장치다.
> 우리는 이 `nsubj` vs `nsubjpass` 비율을 세어 **직설성**을 측정할 것이다."""),

md("""## Step 3 — 지표 ①: Directness Index (직설성)

**아이디어:** 능동절이 많을수록 직설적, 수동절·우회표현이 많을수록 우회적.

$$\\text{base} = \\frac{\\text{능동절}}{\\text{능동절}+\\text{수동절}}$$

여기서 우회표현(circumlocution) 페널티를 빼서 0~1로 만든다.
- 능동절 = `dep_ == "nsubj"` 이고 그 단어가 걸린 머리(head)가 동사/조동사(VERB/AUX)
- 수동절 = `dep_ == "nsubjpass"` 또는 `dep_ == "auxpass"`
- 우회표현 = `"it is regrettable"`, `"cannot but"` 같은 빙빙 도는 관용구 → 페널티

> **먼저 우회표현 사전을 정의한다** (툴킷 `diplo_analysis.CIRCUMLOCUTIONS` 와 동일)."""),
code(r'''# 우회표현 사전 (diplo_analysis.py 의 CIRCUMLOCUTIONS 와 동일)
CIRCUMLOCUTIONS = [
    "it is regrettable", "cannot but", "one cannot", "it is to be",
    "it should be noted", "it is worth noting", "it is unfortunate",
    "it would appear", "it is hoped", "regrettably", "we are saddened",
]
print("우회표현", len(CIRCUMLOCUTIONS), "종 등록")'''),
md("""이제 핵심 함수. **수동절을 감지하는 조건**을 네가 채운다.
수동태의 신호는 두 개의 `dep_` 라벨 — Step 2에서 봤다."""),
code(r'''def directness_index(text, nlp):
    """능동절 비율 - 우회표현 페널티. 0(우회적)~1(직설적)."""
    doc = nlp(text[:100000])     # 너무 긴 문서 방어 (CN 브리핑 대비)
    active = passive = 0
    for tok in doc:
        # TODO: 수동절 신호 두 가지(_____, _____)면 passive += 1
        if tok.dep_ == "_______" or tok.dep_ == "_______":
            passive += 1
        elif tok.dep_ == "nsubj" and tok.head.pos_ in ("VERB", "AUX"):
            active += 1
    base = active / (active + passive) if (active + passive) else 0.5
    low = text.lower()
    circ = sum(low.count(p) for p in CIRCUMLOCUTIONS)
    words = max(len(low.split()), 1)
    penalty = min(0.3, circ / words * 100)   # 우회표현 많을수록 감점 (최대 0.3)
    return {
        "directness_index": round(max(0, base - penalty), 3),
        "active_clauses": active, "passive_clauses": passive,
        "circumlocutions": circ,
    }'''),
code(r'''# CHECK Step3 — 능동/수동 두 문장으로 검증
a = directness_index("Russia attacked Ukrainian civilians.", nlp)
p = directness_index("Civilians were attacked.", nlp)
print("능동 문장:", a)
print("수동 문장:", p)
try:
    assert a["active_clauses"] == 1 and a["passive_clauses"] == 0, "능동 감지 실패"
    assert p["passive_clauses"] >= 1, "수동 감지 실패 (nsubjpass/auxpass 조건 확인)"
    assert a["directness_index"] > p["directness_index"], "능동이 더 직설적이어야 한다"
    print("✅ PASS — 능동이 수동보다 직설적으로 측정됐다.")
except AssertionError as e:
    print("❌ FAIL —", e)'''),
md("""<details><summary>💡 힌트 / 정답</summary>

```python
if tok.dep_ == "nsubjpass" or tok.dep_ == "auxpass":
    passive += 1
```
- `nsubjpass` = 수동태의 주어 (`Civilians were attacked` 의 `Civilians`)
- `auxpass` = 수동태 조동사 (`were attacked` 의 `were`)
- 둘 중 하나라도 보이면 그 절은 수동절이다.
</details>"""),

md("""## Step 4 — 지표 ②: Verb Strength Ladder (동사 강도)

외교는 **동사 선택**으로 강도를 조절한다. `note`(주목한다)는 가장 약하고
`demand`(요구한다)는 가장 세다. 7단 사다리를 만든다 (툴킷 `VERB_LADDER` 와 동일):

| 강도 | 동사들 |
|---|---|
| 1 | note, observe, take note |
| 2 | acknowledge, recognize |
| 3 | regret, lament |
| 4 | concern, worry, trouble |
| 5 | deplore, denounce, decry, reject, oppose |
| 6 | **condemn**, censure, urge |
| 7 | **demand**, insist, require |

**핵심:** `token.lemma_`(기본형)로 매칭한다. `condemned`/`condemns`/`condemning` → 전부 `condemn`."""),
code(r'''# 동사 강도 사다리 (diplo_analysis.py 의 VERB_LADDER 와 동일)
VERB_LADDER = {
    "note": 1, "observe": 1, "take note": 1,
    "acknowledge": 2, "recognize": 2, "recognise": 2,
    "regret": 3, "lament": 3,
    "concern": 4, "worry": 4, "trouble": 4,
    "deplore": 5, "denounce": 5, "decry": 5, "reject": 5, "oppose": 5,
    "condemn": 6, "censure": 6, "urge": 6,
    "demand": 7, "insist": 7, "require": 7,
}

def verb_strength(text, nlp):
    """외교 동사 강도(1 note ~ 7 demand). max/mean + 등장 동사."""
    doc = nlp(text[:100000])
    hits = []
    for tok in doc:
        lemma = tok.lemma_.lower()
        # 사다리에 있고, 동사/명사/형용사로 쓰였으면 채집
        if lemma in VERB_LADDER and tok.pos_ in ("VERB", "NOUN", "ADJ"):
            hits.append((lemma, VERB_LADDER[lemma]))
    scores = [s for _, s in hits]
    return {
        "verb_strength_max": max(scores) if scores else 0,
        "verb_strength_mean": round(sum(scores) / len(scores), 2) if scores else 0,
        "verbs_found": sorted(set(l for l, _ in hits)),
        "n_strength_verbs": len(hits),
    }'''),
code(r'''# CHECK Step4 — lemma 매칭이 시제를 넘어 작동하는지
r1 = verb_strength("We strongly condemn the aggression and demand withdrawal.", nlp)
r2 = verb_strength("The Secretary-General condemned the strikes.", nlp)  # 과거형
r3 = verb_strength("We note the developments with concern.", nlp)
print("condemn+demand:", r1["verb_strength_max"], r1["verbs_found"])
print("condemned(과거):", r2["verb_strength_max"], r2["verbs_found"])
print("note+concern  :", r3["verb_strength_max"], r3["verbs_found"])
try:
    assert r1["verb_strength_max"] == 7, "demand=7 이 max여야"
    assert "condemn" in r2["verbs_found"], "lemma가 과거형을 못 잡았다"
    assert r3["verb_strength_max"] == 4, "concern=4"
    print("✅ PASS — lemma 기반 강도 측정 정상.")
except AssertionError as e:
    print("❌ FAIL —", e)'''),

md("""## Step 5 — 지표 ③: Subject Pattern (주어 패턴)

**누가 문장의 주어로 등장하나?** 같은 사건도 "**우리(We)** 규탄한다" 와
"**모든 당사자(all parties)** 가 자제해야 한다" 는 정치적 의미가 다르다.
주어를 6개 범주로 분류한다 (툴킷의 분류와 동일):

- `first_person` — we, i, our, us (직접 화자)
- `national_actor` — china, russia, the government ... (특정 국가/정부)
- `intl_community` — international community, the UN, security council ...
- `all_parties` — all parties, both sides, the two sides ... (양면 균형 화법)
- `impersonal` — it, there, this, that (비인칭)
- `other` — 그 외"""),
code(r'''# 주어 분류용 사전 (diplo_analysis.py 와 동일)
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

# 빠른 점검
for w in ["we", "all parties", "the international community", "Russia", "it", "the report"]:
    print(f"  {w:32} -> {_classify_subject(w)}")'''),
md("""주어 명사구는 한 단어가 아니라 **구(phrase)** 일 수 있다(`the international community`).
spaCy의 `tok.left_edge` ~ `tok.right_edge` 로 명사구 전체 범위를 잡는다.
아래 함수에서 **주어인지 판단하는 `dep_` 조건**을 네가 채운다(능동 주어 + 수동 주어 둘 다)."""),
code(r'''from collections import Counter

def subject_pattern(text, nlp):
    """주절 주어 분포: first_person/national_actor/intl_community/all_parties/impersonal/other."""
    doc = nlp(text[:100000])
    c = Counter()
    for tok in doc:
        # TODO: 능동 주어와 수동 주어 둘 다 잡는다 → dep_ in ("____", "____")
        if tok.dep_ in ("_____", "_______"):
            # 주어 명사구 전체 텍스트 (너무 길면 핵심 토큰만)
            span = doc[tok.left_edge.i: tok.right_edge.i + 1].text
            c[_classify_subject(span if len(span) < 40 else tok.text)] += 1
    total = sum(c.values()) or 1
    dist = {k: round(v / total, 3) for k, v in c.items()}
    return {"subject_dist": dist, "subject_counts": dict(c), "n_subjects": total}'''),
code(r'''# CHECK Step5
t = ("We condemn the invasion. All parties must show restraint. "
     "The international community is concerned. Russia continued its strikes.")
sp = subject_pattern(t, nlp)
print("counts:", sp["subject_counts"])
print("dist  :", sp["subject_dist"])
try:
    assert sp["n_subjects"] >= 4, "주어를 충분히 못 잡았다 (dep_ 조건 확인)"
    assert sp["subject_counts"].get("first_person", 0) >= 1, "We 를 first_person 으로 못 잡음"
    assert sp["subject_counts"].get("all_parties", 0) >= 1, "all parties 미감지"
    print("✅ PASS — 주어 패턴 분류 정상.")
except AssertionError as e:
    print("❌ FAIL —", e)'''),
md("""<details><summary>💡 힌트 / 정답</summary>

```python
if tok.dep_ in ("nsubj", "nsubjpass"):
```
주어는 **능동 주어(`nsubj`)** 와 **수동 주어(`nsubjpass`)** 두 가지다.
둘 다 잡아야 "당했다"류 문장의 주어도 분포에 들어간다.
</details>"""),

md("""## Step 6 — 157건 전체에 적용 → 소스별 비교표 📊

세 함수를 우크라이나 157건에 모두 돌려 한 행 = 한 문서인 표를 만든다.
spaCy가 157개 문서를 파싱하므로 **몇 초 걸린다.** 진행 표시를 같이 본다."""),
code(r'''rows = []
for i, d in enumerate(ukr.to_dict("records")):
    t = d["text"]
    r = {"source": d["source"], "event_id": d["event_id"], "date": d["date"]}
    r.update(directness_index(t, nlp))
    r.update(verb_strength(t, nlp))
    sp = subject_pattern(t, nlp)
    r["subject_first_person"] = sp["subject_dist"].get("first_person", 0)
    r["subject_all_parties"]  = sp["subject_dist"].get("all_parties", 0)
    rows.append(r)
    if (i + 1) % 20 == 0:
        print(f"  ...{i+1}/{len(ukr)} 처리")
feat = pd.DataFrame(rows)
print("✅ 완료:", feat.shape)
feat.head(3)'''),
md("""이제 **소스별 평균**을 낸다. `groupby("source")` 로 묶고 평균.
아래 TODO에서 `groupby` 대상 컬럼을 채운다."""),
code(r'''# TODO: source 별로 묶어 평균을 낸다 (힌트: feat.groupby("____"))
cols = ["directness_index", "verb_strength_max", "verb_strength_mean",
        "subject_first_person", "subject_all_parties"]
summary = feat.groupby("______")[cols].mean().round(3)
summary = summary.sort_values("verb_strength_max", ascending=False)
summary'''),
code(r'''# CHECK Step6
try:
    summary = feat.groupby("source")[cols].mean().round(3).sort_values(
        "verb_strength_max", ascending=False)
    assert set(summary.index) >= {"UN","KR","CN","FR"}, "소스 4종이 표에 없다"
    top = summary.index[0]
    assert top in ("CN", "UN"), "동사강도 1~2위는 CN/UN 이어야 (현실 데이터)"
    print("✅ PASS — 소스별 비교표 완성")
    print("동사강도 max 순위:", list(summary.index))
except Exception as e:
    print("❌ FAIL —", e, '\n힌트: feat.groupby("source")')'''),
md("""<details><summary>💡 힌트 / 정답</summary>

```python
summary = feat.groupby("source")[cols].mean().round(3)
```
`groupby("source")` 는 소스가 같은 행끼리 묶고, `[cols].mean()` 으로 각 그룹 평균을 낸다.
</details>"""),

md("""## Step 7 — 무엇이 보이나 (그리고 무엇을 조심해야 하나) 🔍

표를 읽어보자. 우리가 실제로 얻는 패턴:

**① 동사 강도 (verb_strength_max 평균):** 대략 **CN ≈ 6.2 > UN ≈ 5.6 > KR ≈ 2.8 > FR ≈ 2.5**
- 중국·UN이 `condemn/deplore` 급 강한 동사를 더 쓴다.
- 프랑스·한국은 `note/acknowledge` 급 약한 동사에 머문다.

> ⚠️ **함정 경고 (정직하게):** 이 숫자는 **문서 길이에 오염(length-confounded)** 돼 있다.
> 중국 문서는 정례 브리핑이라 **길다** → 길면 강한 동사가 한 번이라도 나올 확률이 올라간다.
> `verb_strength_max`(최댓값)는 특히 길이에 약하다. **이건 4주차(S4) 검증에서 길이를 통제**해 다시 본다.
> 오늘은 "패턴이 보인다, 그러나 아직 결론이 아니다"까지만.

**② 직설성 (directness_index 평균):** 대략 **CN 0.85, UN 0.81, KR 0.79, FR 0.73**
- 차이가 **작다.** 솔직하게: 네 소스 모두 꽤 직설적(능동절 위주)이다. "미묘한 차이"가 정직한 결론.

**③ 주어 1인칭(subject_first_person):** **중국이 가장 높고, 한국은 0.**
- 한국은 "We condemn" 보다 "The Republic of Korea / The Ministry ..." 같은 **기관 목소리**로 쓴다.
- 중국은 "We(중국)" 를 주어로 더 자주 내세운다."""),
code(r'''# 주어 1인칭 비율만 따로 — "기관 목소리 vs 1인칭" 대비
fp = feat.groupby("source")["subject_first_person"].mean().round(3).sort_values(ascending=False)
print("주어가 1인칭(we/our/us)인 비율 평균:")
for s, v in fp.items():
    bar = "█" * int(v * 60)
    print(f"  {s}  {v:.3f}  {bar}")
print("\n→ 한국은 거의 0: '우리'가 아니라 '대한민국/외교부'라는 기관 주어로 말한다.")'''),

md("""## Step 8 — 의존구문 SVO 추출 → Blame Attribution (귀속) 🎯 새 차원

### 지금까지 vs 오늘 한 걸음 더
Step 2~3에서 우리는 `nsubj`(능동 주어) / `nsubjpass`(수동 주어) / `auxpass`(수동 조동사)를 **세기**만 했다.
이제 한 걸음 더 들어가, 한 동사를 중심으로 **"누가-무엇을"(주어-동사-목적어, SVO)** 삼항을 통째로 뽑는다.
여기에 의존관계 라벨이 하나 더 등장한다:

| `dep_` 라벨 | 뜻 | 예 |
|---|---|---|
| `nsubj` | 능동 주어 (행위자) | **Russia** attacked civilians |
| `nsubjpass` | 수동 주어 (당한 쪽) | **Civilians** were killed |
| `agent` | 수동문의 "by ..." 행위자 | civilians were killed **by Russia** |

> **핵심 질문(Blame Attribution = 귀속):**
> 가해 행위(attack/strike/kill…)를 서술할 때, 외교 성명은 **가해자를 *명시*** 하는가, 아니면 **행위자를 *가리는*** 가?
> - `Russia attacked civilians` → 주어가 `Russia`(가해자) = **명시(named)**.
> - `Civilians were killed` → 수동, `by ...` 없음 = **행위자 가림(obscured)**.
>
> 이건 Step 1의 직설성(수동태 세기)을 **"가해 동사에 한정해, 가해자가 누구로 채워졌나"** 까지 끌어올린 차원이다."""),

md("""### 툴킷에서 두 함수 가져오기
지금까지는 함수를 노트북에서 직접 짰다. 이번 차원은 SVO 추출 + 경량 coreference(대명사→개체 치환)가
얽혀 있어 길다. 그래서 **이미 검증된 툴킷**(`diplo_analysis.py`)에서 두 함수를 가져와 쓴다.
- `extract_svo(text, nlp)` — 문장에서 `{verb, subject, passive, object}` 삼항 리스트를 뽑는다.
- `blame_attribution(text, nlp, topic=...)` — 가해 동사만 골라 named/obscured 를 세고 `blame_directness` 를 낸다."""),
code(r'''from diplo_analysis import extract_svo, blame_attribution

# 같은 사건, 두 가지 말하기 — 가해자 명시 vs 가림
for sent in ["Russia attacked Ukrainian civilians.",
             "Civilians were killed in the strike."]:
    print(sent)
    for tr in extract_svo(sent, nlp):
        print(f"   verb={tr['verb']:8} subject={tr['subject']!s:18} "
              f"passive={tr['passive']!s:6} object={tr['object']}")
    print()'''),
md("""> **눈으로 확인.**
> - `Russia attacked …` → `subject="Russia"`, `passive=False` → 가해자가 **주어로 살아있다.**
> - `Civilians were killed` → `subject=None`, `passive=True` → 가해자가 **사라졌다**(목적어 자리에 피해자만).
>
> `blame_attribution` 은 이 둘을 각각 **named / obscured** 로 센다.
> `blame_directness = named / (named + obscured)` → **1에 가까울수록 가해자를 직접 지목**한다."""),
code(r'''# 한 문장으로 blame_attribution 감 잡기
named_ex   = "Russia bombed the power plant and shelled the city."
obscured_ex = "The power plant was bombed and the city was shelled."
print("가해자 명시:", blame_attribution(named_ex, nlp, topic="ukraine"))
print("행위자 가림:", blame_attribution(obscured_ex, nlp, topic="ukraine"))'''),

md("""### 우크라이나+가자 전체에 적용 → 소스별 blame_directness 비교
귀속은 **가해 행위를 서술하는 문장에서만** 발동한다(attack/strike/kill…).
우크라이나만으로는 발동 문서가 적어, 같은 가해-구조를 공유하는 **가자(gaza)** 성명까지 백업 코퍼스에서 함께 불러와
표본을 키운다. 발동한 문서들만 모아 **소스별 평균 `blame_directness`** 를 낸다."""),
code(r'''import json as _json
corpus = _json.load(open(os.path.join(PROJECT, "data", "backup", "corpus_clean.json"),
                        encoding="utf-8"))
two = [d for d in corpus if d["topic"] in ("ukraine", "gaza")]
print("우크라이나+가자 문서:", len(two), "건")

from collections import defaultdict
blame_dir = defaultdict(list)   # 소스 -> 발동한 문서들의 blame_directness 리스트
fired = 0
for d in two:
    bl = blame_attribution(d["text"], nlp, d["topic"], d.get("lang", "en"))
    if bl["blame_directness"] is not None:     # 가해 서술이 있는 문서만
        blame_dir[d["source"]].append(bl["blame_directness"])
        fired += 1
print(f"귀속이 발동한 문서: {fired}/{len(two)} (가해를 서술한 성명만 발동)")'''),
md("""소스별 평균을 낸다. **발동 문서가 0건인 소스는 평균이 정의되지 않는다(귀속 0건)** — 이것 자체가 신호다.
아래 TODO에서 평균을 내는 한 줄을 채운다."""),
code(r'''# TODO: 각 소스의 blame_directness 리스트 v 의 평균을 내라 (힌트: sum(v)/len(v))
print(f"{'source':8}{'평균 blame_directness':>22}{'발동 문서수':>12}")
for s in ["UN", "CN", "FR", "KR"]:
    v = blame_dir[s]
    avg = round(_______ / len(v), 2) if v else None   # ← 빈칸: 합을 무엇으로?
    print(f"{s:8}{str(avg):>22}{len(v):>12}")'''),
code(r'''# CHECK Step8 — 실제 데이터 패턴(FR > UN > CN, CN 최저, KR=없음) 재현
try:
    mean = {s: (round(sum(v)/len(v), 2) if v else None) for s, v in blame_dir.items()}
    assert mean.get("UN") and mean.get("CN") and mean.get("FR"), "UN/CN/FR 발동 문서가 있어야"
    assert mean["FR"] > mean["UN"] > mean["CN"], "FR > UN > CN 순서가 안 맞는다"
    assert not blame_dir["KR"], "한국은 귀속 0건이어야 (공격을 서술하지 않음)"
    print("✅ PASS — blame_directness: FR", mean["FR"], "> UN", mean["UN"],
          "> CN", mean["CN"], "| KR=없음(귀속 0건)")
except Exception as e:
    print("❌ FAIL —", e, "\n힌트: avg = sum(v)/len(v)")'''),
md("""<details><summary>💡 힌트 / 정답</summary>

```python
avg = round(sum(v) / len(v), 2) if v else None   # 빈칸 = sum(v)
```

**읽어라 (핵심 해석).** 실제 결과는 대략:
- **프랑스 0.43 > UN 0.38 > 중국 0.30**, **한국은 귀속 0건**(평균 정의 안 됨).
- 한국은 공격을 *구체적으로 서술하지 않고* "깊이 우려·규탄한다" 식으로 **추상적으로만** 말한다 → 가해 동사가 안 나와 발동 자체가 0건.
- 중국은 공격을 언급하더라도 **행위자를 가리는 수동태 비율이 가장 높다(최저 0.30)** → 명시(named)가 적어 directness가 낮다.
- 단, **프랑스는 발동 문서가 7건뿐**이라 표본이 작다 → 절대 수치보다 "중국이 가장 가린다 / 한국은 서술 자체가 없다"는 *구조적 신호*에 무게를 둔다.

⚠️ **함정 경고 (정직하게):**
> 1. 귀속은 **가해를 서술한 문장에서만** 발동한다 → 희소하다(전체 304건 중 ~101건만 발동).
> 2. 소형 spaCy 모델은 **복문(여러 절이 접속된 긴 문장)** 에서 일부 SVO를 놓친다 → 카운트가 과소될 수 있다.
> 3. 그래서 우크라이나만으론 표본이 작아 **가자까지 합쳐** 봤다. 절대 수치보다 **소스 간 *상대* 순서**를 신뢰한다.
</details>"""),

md("""## 🎯 회고 (5분)

1. **수동태**가 외교에서 책임을 흐리는 장치라면, `directness_index` 가 낮은 문서를 한 건 열어
   실제로 "누가 했는지"가 흐려졌는지 눈으로 확인해보자. 숫자를 믿기 전에 원문을 본다.
2. 중국의 높은 `verb_strength_max` 를 그대로 "중국이 가장 강경하다"로 발표하면 왜 위험한가?
   (→ 길이 편향. S4에서 1000단어당으로 정규화해 다시 본다.)
3. 한국의 `subject_first_person ≈ 0` 은 무엇을 의미할까? '신중함'인가 '거리두기'인가?
   이건 숫자가 답하지 못한다 — **해석은 인간의 몫**(S3에서 의미 분석으로 보강).

## ▶️ 다음 (Session 3)
> "오늘은 **구조(능동/수동·동사·주어)** 를 규칙으로 셌고, SVO로 **귀속(누가 가해자로 *지목*됐나)** 까지 갔다.
> 그런데 규칙으로 못 잡는 게 남았다 — *framing*(가해/피해/중립을 어떻게 *규정*하나), 미묘한 *완곡어법*, 양면적 *상호성*.
> 다음 주는 **상호성·완곡어(부정처리 포함)** 를 만들고 **Claude(LLM)로 의미를 교차검증**한다.
> 설계 원칙: **계산은 코드(결정론), 의미 해석은 LLM, 판단은 인간.**"""),
]

save(cells, "session2/session2.ipynb")
