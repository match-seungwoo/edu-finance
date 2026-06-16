# -*- coding: utf-8 -*-
"""_build_hw.py — 과제(Take-home) 노트북 빌더 (주제3: AI 거버넌스).

한 정의에서 두 개의 노트북을 만든다:
  - homework/ai_governance_assignment.ipynb   (빈칸 scaffold, 학생이 채움)
  - homework/ai_governance_answerkey.ipynb     (전부 채워진 정답본)

설계:
  코딩 TODO 셀은 BLANK(과제용) / FILLED(정답용) 두 버전을 가진다.
  ANSWERS 맵에 (BLANK→FILLED) 쌍을 두어, 과제 노트북을 정답으로 자동 채워
  검증할 수 있게 한다(_validate_hw.py 가 사용).
  서술형/CHECK/시각화 셀은 두 노트북에서 동일하거나, 정답본에만 모범답이 더 붙는다.
"""
from nb import md, code, save

# ── S1/S4 와 100% 동일한 SETUP 문자열 (VERBATIM 재사용) ──────────────
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

# ── 빈칸(BLANK) ↔ 정답(FILLED) 코드 쌍. 검증기가 이 맵으로 과제를 채운다.
# 각 항목: (블랭크 코드, 정답 코드). 두 코드는 노트북에서 1:1로 대응한다.
ANSWERS = []

def todo(blank, filled):
    """코딩 TODO 셀 등록 → 과제엔 blank, 정답엔 filled 가 들어간다."""
    ANSWERS.append((blank, filled))
    return blank, filled


# ════════════════════════════════════════════════════════════════════
# 공통 셀 빌더 — assignment / answerkey 두 모드로 셀 리스트를 만든다.
# mode="assignment" → blank 코드 + 힌트(details)만
# mode="answerkey"  → filled 코드 + 모범 서술형 + instructor note
# ════════════════════════════════════════════════════════════════════
def build_cells(mode):
    KEY = (mode == "answerkey")
    cells = []
    A = cells.append

    # ── 헤더 ────────────────────────────────────────────────────────
    title_tag = "정답본 (ANSWER KEY)" if KEY else "과제 (TAKE-HOME)"
    A(md(f"""# 과제 — AI 거버넌스, 혼자 처음부터 끝까지  ·  {title_tag}
### 주제 3: AI 거버넌스 · 4주간 배운 6차원 툴킷을 *스스로* 들이댄다

> **이 과제 한 문장:** "우크라이나·가자에서는 강사와 함께 분석했다.
> 이제 **AI 거버넌스**라는 새 코퍼스에 너 혼자 `diplo_analysis` 툴킷을 들고 들어가,
> *누가 침묵했는지* 찾아내고, *당사자성이 낮은 주제에서 각국의 말하기가
> 수렴하는지 발산하는지* 를 직접 검증한다."

이번 코퍼스는 **작다(약 21건)**. 작은 데이터는 그 자체로 발견이다 —
어떤 소스는 아예 **한 건도 없다**. 그 침묵을 네가 찾아내는 게 첫 임무다.

#### 🎯 학습 목표
1. 배운 툴킷(`diplo_analysis`)을 **새 주제에 스스로** 적용한다.
2. **침묵 지도**로 *구조적으로 부재한 소스* 를 발견하고 그 이유를 추론한다.
3. **당사자성(stake) 가설**을 검증한다: 고당사자성(우크라이나/가자) vs
   저당사자성(AI 거버넌스)에서 언어 패턴(상호성·동사강도·완곡어)이 다른가?
4. 결과를 **차트 한 장**으로 보여주고, 분석의 **한계**를 스스로 적는다.

#### ❓ 연구 질문 (recap)
- **Q1.** 같은 사건을 두고 소스(UN/한국/중국/프랑스)별로 말하기가 다른가?
- **Q2.** 주제의 **당사자성**이 언어를 바꾸는가? — 우크라이나·가자는 소스들이
  *직접 당사자*(고당사자성)지만, AI 거버넌스는 *한 발 떨어진* 글로벌 거버넌스
  (저당사자성)다. 그럼 강도·상호성·완곡어가 달라지는가?

> 💡 **진행 방식:** 셀을 위에서 아래로 하나씩 실행한다.
> `# TODO` 가 보이면 빈칸(`____`)을 직접 채우고, 바로 아래 `# CHECK` 셀을 실행해 `✅` 가 떠야 다음으로.
> `📝 서술형` 마크다운 셀은 **너의 문장으로** 채운다(채점 대상)."""))

    # ── Step 0 환경 ─────────────────────────────────────────────────
    A(md("## Step 0 — 환경 설정\n필요한 라이브러리를 설치하고, 프로젝트 폴더를 찾는다."))
    A(code('!pip install spacy plotly pandas -q\n!python -m spacy download en_core_web_sm -q'))
    A(code(SETUP))

    # ── Step 1 데이터 존재 확인 + 로드 ──────────────────────────────
    A(md("""## Step 1 — 데이터 존재 확인 + AI 거버넌스 불러오기 🔍

분석 전 항상 **존재 → 개수 → 내용** 순으로 두 눈으로 확인한다(분석의 첫 윤리).
이번엔 간단히만 확인하고, `topic == "ai_governance"` 만 골라낸다."""))
    A(code(r'''import json, os, pandas as pd
docs_all = json.load(open(os.path.join(PROJECT,"data","backup","corpus_clean.json"), encoding="utf-8"))
df = pd.DataFrame(docs_all)
print("전체 코퍼스:", df.shape, "| 주제:", dict(df["topic"].value_counts()))'''))

    b, f = todo(
        r'''# TODO: topic 이 "ai_governance" 인 행만 골라 ai 변수에 담아라.
#       힌트: df[df["topic"] == "____"]
ai = df[df["topic"] == "______________"].copy()
print("AI 거버넌스 문서:", len(ai), "건")
ai.groupby("source").size()''',
        r'''# 정답: ai_governance 행만 추출
ai = df[df["topic"] == "ai_governance"].copy()
print("AI 거버넌스 문서:", len(ai), "건")
ai.groupby("source").size()''')
    A(code(f if KEY else b))

    A(code(r'''# CHECK Step1 — AI 거버넌스가 제대로 골라졌는가 (작은 코퍼스: ~21건)
try:
    assert set(ai["topic"].unique()) == {"ai_governance"}, "필터가 잘못됐다"
    assert 15 <= len(ai) <= 30, "건수가 예상 범위를 벗어났다"
    print("✅ PASS — AI 거버넌스", len(ai), "건 확보 (작은 코퍼스다)")
except Exception as e:
    print("❌ FAIL —", e, '\n힌트: df[df["topic"] == "ai_governance"]')'''))
    if not KEY:
        A(md("""<details><summary>💡 힌트</summary>

빈칸은 주제 이름 문자열이다. `df["topic"]` 컬럼에 어떤 값들이 있는지 위 셀에서 봤다.
정답 코드는 정답본 노트북에 있다.
</details>"""))

    # ── Step 2 침묵 지도 ────────────────────────────────────────────
    A(md("""## Step 2 — 침묵 지도: 어느 소스가 *구조적으로 부재* 하는가? 🤫

> **이번 과제의 첫 발견.** 우크라이나(S1)에서 배웠듯 **말하지 않는 것도 데이터**다.
> AI 거버넌스 8개 사건(ai01~ai08)에 대해 **사건 × 소스** 매트릭스를 만들어,
> *어떤 소스가 거의 / 아예 말하지 않았는지* 를 네가 직접 찾아낸다."""))

    b, f = todo(
        r'''# TODO: silence_map 으로 AI 거버넌스 침묵 지도를 만들어라.
#   - silence_map(docs, events) 는 사건×소스 커버리지(0=침묵)를 돌려준다.
#   - docs 인자에는 ai 의 레코드 리스트, events 인자에는 ai_governance 사건 목록.
#   힌트: from diplo_analysis import silence_map / from scrapers.events import events_for
from diplo_analysis import silence_map
from scrapers.events import events_for

ai_docs = ai.to_dict("records")
sm = silence_map(ai_docs, events_for("________________"))   # ← 빈칸: 어떤 topic?
cov = pd.DataFrame(sm)[["event_id","event_name","UN","KR","CN","FR","silent_sources"]]
cov''',
        r'''# 정답: AI 거버넌스 침묵 지도
from diplo_analysis import silence_map
from scrapers.events import events_for

ai_docs = ai.to_dict("records")
sm = silence_map(ai_docs, events_for("ai_governance"))
cov = pd.DataFrame(sm)[["event_id","event_name","UN","KR","CN","FR","silent_sources"]]
cov''')
    A(code(f if KEY else b))

    b, f = todo(
        r'''# TODO: 소스별 총 문서 수를 세어, '아예 0건인 소스'를 찾아라.
#       힌트: cov[["UN","KR","CN","FR"]].sum() 으로 소스별 합계를 구한다.
src_totals = cov[["UN","KR","CN","FR"]].____()    # ← 빈칸: 합계 메서드
print("소스별 총 문서 수:\n", src_totals)
absent = [s for s in ["UN","KR","CN","FR"] if src_totals[s] == 0]
print("\n구조적으로 부재(0건)한 소스:", absent)''',
        r'''# 정답: 소스별 합계 → 0건 소스 탐지
src_totals = cov[["UN","KR","CN","FR"]].sum()
print("소스별 총 문서 수:\n", src_totals)
absent = [s for s in ["UN","KR","CN","FR"] if src_totals[s] == 0]
print("\n구조적으로 부재(0건)한 소스:", absent)''')
    A(code(f if KEY else b))

    A(code(r'''# CHECK Step2 — 부재한 소스를 제대로 찾았는가
try:
    src_totals = cov[["UN","KR","CN","FR"]].sum()
    absent = [s for s in ["UN","KR","CN","FR"] if src_totals[s] == 0]
    assert absent == ["FR"], f"부재 소스가 예상과 다르다: {absent}"
    print("✅ PASS — 프랑스(FR)가 AI 거버넌스에서 단 한 건도 없다(구조적 침묵).")
    print("   이게 왜 그런지는 Step 5(a) 서술형에서 설명한다.")
except Exception as e:
    print("❌ FAIL —", e, '\n힌트: 소스별 합계가 0인 곳을 찾아라')'''))
    if not KEY:
        A(md("""<details><summary>💡 힌트</summary>

- 첫 칸은 `events_for("ai_governance")`.
- 둘째 칸은 `.sum()` — 컬럼별 합계를 낸다.
- 합계가 0인 소스가 바로 "한 건도 안 낸" = **구조적으로 부재한** 소스다.
- *왜* 부재할까는 곧 서술형에서 묻는다. (이 코퍼스가 어디서 긁혔는지 떠올려 보라.)
</details>"""))
    if KEY:
        A(md("""> 🧑‍🏫 **강사 메모 (정답):** AI 거버넌스에서 **FR=0**.
> `silent_sources` 열을 보면 프랑스는 8개 사건 *전부* 침묵이다. 게다가 **ai01(G7 히로시마)**
> 는 네 소스 모두 0 — 이 코퍼스 자체가 작고 듬성하다는 신호. 학생이 `absent == ["FR"]` 만
> 맞히면 통과지만, "FR이 *모든* 사건에서 빠졌다(우발적 누락이 아니라 구조적)"까지 읽으면 만점."""))

    # ── Step 3 분석 + 소스 비교표 ──────────────────────────────────
    A(md("""## Step 3 — `analyze_document` 전 문서 분석 → 소스 비교표

이제 툴킷의 `analyze_document` 를 **AI 거버넌스 전 문서**에 돌려 6차원을 뽑고,
**소스별 평균표**를 만든다. (프랑스는 데이터가 없으니 표에 UN/KR/CN 만 나온다.)

> ⚙️ S4에서 배운 교훈을 잊지 말 것: `verb_strength_max`(원시 최댓값)는 **문서 길이에
> 오염**된다. 그래서 아래에서 **밀도(`verb_density` = 강도동사수/단어수×1000)** 도 함께 만든다.
> 결론은 *밀도* 위에서 말한다."""))
    A(code(r'''from diplo_analysis import get_nlp, analyze_document
nlp = get_nlp()                       # spaCy 1회 로드
rows = [analyze_document(d, nlp) for d in ai_docs]   # 21건 전부 분석 (수 초)
ana = pd.DataFrame(rows)
# 원문 텍스트를 붙여 길이/단어수 계산 (S4의 길이 편향 교훈)
ana = ana.merge(ai[["id","text","title","url","lang"]], on="id", how="left")
ana["n_words"] = ana["text"].str.split().str.len()
print("분석 결과표:", ana.shape)
ana[["source","event_id","directness_index","verb_strength_max","mutuality_index","hedging_density"]].head(6)'''))

    b, f = todo(
        r'''# TODO: S4에서 배운 '밀도 정규화'를 그대로 적용하라.
#   verb_density = 강도동사 개수 / 단어수 × 1000
#   힌트: ana["n_strength_verbs"] 를 ana["n_words"] 로 나누고 1000 을 곱한다.
ana["verb_density"] = ana["________________"] / ana["n_words"] * 1000   # ← 빈칸

# 소스별 평균표 (밀도 포함). FR은 데이터가 없어 자동으로 빠진다.
cols = ["directness_index","verb_strength_max","verb_density",
        "mutuality_index","hedging_density","subject_first_person"]
agg = ana.groupby("______")[cols].mean().round(2)   # ← 빈칸: 무엇으로 묶나?
agg = agg.reindex([s for s in ["UN","KR","CN","FR"] if s in agg.index])
agg''',
        r'''# 정답: 밀도 정규화 + 소스별 평균표
ana["verb_density"] = ana["n_strength_verbs"] / ana["n_words"] * 1000

cols = ["directness_index","verb_strength_max","verb_density",
        "mutuality_index","hedging_density","subject_first_person"]
agg = ana.groupby("source")[cols].mean().round(2)
agg = agg.reindex([s for s in ["UN","KR","CN","FR"] if s in agg.index])
agg''')
    A(code(f if KEY else b))

    A(code(r'''# CHECK Step3 — 소스 비교표가 알려진 실제 결과와 맞는가 (소수 오차 허용)
try:
    assert "verb_density" in ana.columns and ana["verb_density"].notna().all()
    agg = ana.groupby("source")[cols].mean().round(2)
    assert "FR" not in agg.index, "FR은 데이터가 없어야 한다"
    assert set(agg.index) == {"UN","KR","CN"}, "소스가 UN/KR/CN 셋이어야 한다"
    # 상호성: 한국·중국이 UN보다 높다 (저당사자성에서 협력 어휘 多)
    assert agg.loc["CN","mutuality_index"] > agg.loc["UN","mutuality_index"]
    assert agg.loc["KR","mutuality_index"] > agg.loc["UN","mutuality_index"]
    print("✅ PASS — 소스 비교표 완성 (UN/KR/CN, 프랑스는 부재)")
    print("   상호성: 한국 %.1f · 중국 %.1f > UN %.1f"
          % (agg.loc["KR","mutuality_index"], agg.loc["CN","mutuality_index"], agg.loc["UN","mutuality_index"]))
except Exception as e:
    print("❌ FAIL —", e, '\n힌트: 빈칸은 "n_strength_verbs" 와 "source"')'''))
    if not KEY:
        A(md("""<details><summary>💡 힌트</summary>

- 첫 칸은 `"n_strength_verbs"` (S4에서 똑같이 했다 — 개수를 길이로 나눠 밀도로).
- 둘째 칸은 `"source"` — 소스별로 묶어 평균.
- 표에 행이 **3개(UN/KR/CN)** 만 나오면 정상이다. 프랑스는 데이터가 없다.
</details>"""))
    if KEY:
        A(md("""> 🧑‍🏫 **강사 메모 (정답·실제 값, n=21):**
>
> | 소스 | directness | verb_max | verb_density | mutuality | hedging | we(1인칭) |
> |---|---|---|---|---|---|---|
> | UN | 0.87 | 3.50 | 3.47 | 5.37 | 1.63 | 0.15 |
> | 한국 | 0.72 | 1.00 | 0.42 | **10.63** | 2.00 | 0.00 |
> | 중국 | 0.85 | 4.89 | 2.35 | **10.43** | 2.72 | 0.12 |
>
> 읽는 법: 저당사자성 주제라 **한국·중국 모두 상호성이 매우 높다(≈10)** — 협력·대화·win-win 어휘.
> 한국은 동사강도가 바닥(verb_max 1.0, 'note' 수준) = 거의 강경어를 안 쓴다.
> **흔한 실수:** ① `verb_strength_max`(원시)만 보고 "중국 강경" 결론 → 밀도로 봐야 함.
> ② 표에 FR 행을 억지로 만들려다 NaN/에러. ③ 작은 n(21)을 잊고 과한 일반화."""))

    # ── Step 4 당사자성 비교 ────────────────────────────────────────
    A(md("""## Step 4 — 당사자성(stake) 가설 검증: 고당사자성 vs 저당사자성

> **Q2의 심장.** 우크라이나·가자에서 각국은 *직접 당사자*다(고당사자성).
> AI 거버넌스는 *한 발 떨어진* 글로벌 거버넌스다(저당사자성).
> 그럼 언어가 달라지는가? 아래 **우크라이나·가자 기준 수치(강사가 미리 계산)** 와
> 네가 방금 구한 AI 거버넌스 수치를 **나란히** 비교한다.

아래는 강사가 같은 툴킷으로 미리 계산한 **주제별 전체 평균(모든 소스 합산)** 이다.
이걸 기준선(reference)으로 삼는다."""))
    A(code(r'''# 강사 제공 기준선 — 우크라이나/가자(고당사자성) 주제별 전체 평균.
# (같은 diplo_analysis 툴킷으로 계산한 값. 너의 AI 거버넌스 결과와 비교용.)
REFERENCE = pd.DataFrame({
    "mutuality_index":   {"ukraine": 4.87, "gaza": 4.66},
    "verb_strength_max": {"ukraine": 4.05, "gaza": 3.44},
    "verb_density":      {"ukraine": 4.77, "gaza": 4.00},
    "hedging_density":   {"ukraine": 2.20, "gaza": 2.22},
    "directness_index":  {"ukraine": 0.79, "gaza": 0.80},
})
REFERENCE'''))

    b, f = todo(
        r'''# TODO: 네 AI 거버넌스 데이터(ana)의 '전체 평균'을 구해 기준선에 한 줄로 추가하라.
#   비교할 5개 지표의 평균을 내고 round(2) 한다.
#   힌트: ana[[지표들]].mean() → REFERENCE.loc["ai_governance"] = ...
metrics = ["mutuality_index","verb_strength_max","verb_density","hedging_density","directness_index"]
ai_mean = ana[metrics].____().round(2)     # ← 빈칸: 평균 메서드
compare = REFERENCE.copy()
compare.loc["ai_governance"] = ai_mean
compare''',
        r'''# 정답: AI 거버넌스 전체 평균을 기준선에 추가
metrics = ["mutuality_index","verb_strength_max","verb_density","hedging_density","directness_index"]
ai_mean = ana[metrics].mean().round(2)
compare = REFERENCE.copy()
compare.loc["ai_governance"] = ai_mean
compare''')
    A(code(f if KEY else b))

    A(code(r'''# CHECK Step4 — 당사자성 대비가 드러나는가
try:
    assert "ai_governance" in compare.index, "AI 거버넌스 행이 없다"
    m = compare["mutuality_index"]
    v = compare["verb_density"]
    # 저당사자성(AI)일수록 상호성↑, 동사밀도(강경)↓ 라는 가설
    assert m["ai_governance"] > m["ukraine"] and m["ai_governance"] > m["gaza"], "상호성 가설 불일치"
    assert v["ai_governance"] < v["ukraine"] and v["ai_governance"] < v["gaza"], "동사밀도 가설 불일치"
    print("✅ PASS — 저당사자성(AI)일수록 상호성↑ 동사강도(밀도)↓ 패턴이 보인다.")
    print("   상호성: AI %.2f vs 우크라 %.2f / 가자 %.2f" % (m["ai_governance"], m["ukraine"], m["gaza"]))
    print("   동사밀도: AI %.2f vs 우크라 %.2f / 가자 %.2f" % (v["ai_governance"], v["ukraine"], v["gaza"]))
except Exception as e:
    print("❌ FAIL —", e, '\n힌트: 빈칸은 .mean()')'''))
    if not KEY:
        A(md("""<details><summary>💡 힌트</summary>

빈칸은 `.mean()`. `ana[metrics].mean()` 은 각 지표의 전체 평균(시리즈)을 준다.
그걸 `compare.loc["ai_governance"]` 에 한 줄로 넣으면 3주제 비교표가 완성된다.
</details>"""))
    if KEY:
        A(md("""> 🧑‍🏫 **강사 메모 (정답·실제 값):**
>
> | 주제 | 당사자성 | mutuality | verb_density | verb_max | hedging | directness |
> |---|---|---|---|---|---|---|
> | 우크라이나 | 高 | 4.87 | 4.77 | 4.05 | 2.20 | 0.79 |
> | 가자 | 高 | 4.66 | 4.00 | 3.44 | 2.22 | 0.80 |
> | **AI 거버넌스** | **低** | **8.54** | **2.41** | 3.62 | 2.17 | 0.83 |
>
> **핵심 반전:** 저당사자성 주제(AI)에서 **상호성이 거의 2배(8.54 vs ~4.7)**, **동사강도 밀도는
> 절반(2.41 vs ~4.4)**. 즉 당사자성이 낮을수록 각국은 *더 협력적·덜 강경하게* 말한다.
> 완곡어(hedging)·직설성은 거의 안 변함 — 이건 주제보다 문체/장르 특성일 수 있다(서술형 (b)에서 논의).
> **흔한 실수:** "AI라 상호성이 높다"를 인과로 단정. n=21 + FR 부재라 *경향*까지만 말해야 한다."""))

    # ── Step 5 시각화 ───────────────────────────────────────────────
    A(md("""## Step 5 — 시각화 (Plotly) 한 장 📊

표는 정확하지만 눈에 안 들어온다. **너의 선택**으로 차트 한 장을 그려라.
아래는 가장 무난한 예시(주제별 상호성 비교 막대)의 골격이다. 빈칸만 채우면 된다.
원하면 레이더/산점도 등 다른 형태로 바꿔도 좋다(채점은 '의도가 드러나는가'로 본다)."""))

    b, f = todo(
        r'''# TODO: 주제별 상호성(mutuality) 비교 막대그래프를 완성하라.
#   x = 세 주제, y = compare["mutuality_index"] 값.
#   힌트: go.Bar(x=..., y=...) 의 y 에 어떤 열을 넣을지 생각.
import plotly.graph_objects as go
topics_ko = {"ukraine":"우크라이나(高당사자성)","gaza":"가자(高당사자성)","ai_governance":"AI거버넌스(低당사자성)"}
order = ["ukraine","gaza","ai_governance"]
fig = go.Figure(go.Bar(
    x=[topics_ko[t] for t in order],
    y=[compare.loc[t, "________________"] for t in order],   # ← 빈칸: 어떤 지표?
    marker_color=["#E45756","#F58518","#4C78A8"],
    text=[f'{compare.loc[t,"mutuality_index"]:.1f}' for t in order],
    textposition="outside",
))
fig.update_layout(
    title="당사자성이 낮을수록 상호성(협력 어휘)이 높다",
    xaxis_title="주제(당사자성)", yaxis_title="상호성 지수 (1000단어당 양면적 표현)",
    template="plotly_white", height=440,
)
fig.show()''',
        r'''# 정답: 주제별 상호성 비교 막대
import plotly.graph_objects as go
topics_ko = {"ukraine":"우크라이나(高당사자성)","gaza":"가자(高당사자성)","ai_governance":"AI거버넌스(低당사자성)"}
order = ["ukraine","gaza","ai_governance"]
fig = go.Figure(go.Bar(
    x=[topics_ko[t] for t in order],
    y=[compare.loc[t, "mutuality_index"] for t in order],
    marker_color=["#E45756","#F58518","#4C78A8"],
    text=[f'{compare.loc[t,"mutuality_index"]:.1f}' for t in order],
    textposition="outside",
))
fig.update_layout(
    title="당사자성이 낮을수록 상호성(협력 어휘)이 높다",
    xaxis_title="주제(당사자성)", yaxis_title="상호성 지수 (1000단어당 양면적 표현)",
    template="plotly_white", height=440,
)
fig.show()''')
    A(code(f if KEY else b))

    A(code(r'''# CHECK Step5 — 차트가 그려졌고 데이터가 올바르게 들어갔는가
try:
    ys = list(fig.data[0].y)
    assert len(ys) == 3 and abs(ys[2] - compare.loc["ai_governance","mutuality_index"]) < 1e-6
    print("✅ PASS — 시각화 완성 (AI 거버넌스 막대가 가장 높다)")
except Exception as e:
    print("❌ FAIL —", e, '\n힌트: 빈칸은 "mutuality_index"')'''))
    if not KEY:
        A(md("""<details><summary>💡 힌트</summary>

빈칸은 `"mutuality_index"`. 다른 차트를 그려도 되지만, 이 CHECK 셀은 위 예시 기준이다 —
다른 형태로 바꿨다면 CHECK는 건너뛰고 직접 그림이 뜨는지 확인하라.
</details>"""))

    # ── Step 6 서술형 (채점용) ──────────────────────────────────────
    A(md("""## Step 6 — 📝 서술형 질문 (채점 대상)

아래 세 칸을 **너의 문장으로** 채운다. 정답이 하나는 아니다. 채점은
*숫자를 근거로 댔는가 / 측정의 한계를 아는가* 를 본다. 각 3~6문장."""))

    # (a)
    A(md("""### (a) 왜 프랑스(FR)는 AI 거버넌스에서 한 건도 없는가? 🇫🇷

침묵 지도에서 FR=0 을 찾았다. 이것이 *우발적 누락*이 아니라 *구조적 부재*라면 그 이유는?
(힌트: 이 코퍼스는 어디서 긁혔나? 프랑스의 AI 외교 자료는 어디에 사는가?)"""))
    if KEY:
        A(md("""**📝 모범답 (a):**

> 우발적 누락이 아니라 **구조적 부재**다. 침묵 지도를 보면 프랑스는 8개 사건 *전부*에서 0건이고,
> 다른 세 소스는 같은 사건들에 문서를 냈다. 즉 "프랑스가 AI에 관심이 없어서"가 아니다.
> 원인은 **수집 구조**에 있다: 이 코퍼스는 각국의 *공식 성명문 트리(diplomatie.gouv.fr 성명란)* 에서
> 긁혔는데, 프랑스의 AI-거버넌스 자료(특히 2025 파리 AI Action Summit, ai08)는 **외교부 성명 트리가
> 아니라 엘리제궁/정상회의 전용 포털** 같은 별도 사이트에 올라간다. 정작 프랑스는 파리 정상회의의
> *주최국*인데 우리 스크래퍼가 보는 위치엔 없는 것이다. 따라서 "FR=0"은 프랑스의 침묵이 아니라
> **우리 측정 창(window)의 사각지대**이며, 결론에 반드시 이 한계를 명시해야 한다.
> (이것이 침묵 지도의 진짜 교훈: 0은 '안 했다'와 '내가 못 봤다'를 구분해야 한다.)"""))
    else:
        A(md("""> _여기에 답을 적으세요 (3~6문장)._
>
>"""))

    # (b)
    A(md("""### (b) 저당사자성 주제(AI)에서 4개(실제론 3개) 소스의 언어는 *수렴* 하는가 *발산* 하는가?

Step 3 소스 비교표와 Step 4 당사자성 비교표를 근거로 답하라.
고당사자성(우크라이나/가자)과 비교해 소스 간 차이가 줄었나 늘었나? 어떤 지표에서?"""))
    if KEY:
        A(md("""**📝 모범답 (b):**

> **부분 수렴**이다. 고당사자성 주제(우크라이나)에서는 상호성이 중국 10 vs 프랑스 1로 *9배* 벌어졌지만,
> 저당사자성인 AI에서는 **한국 10.6 · 중국 10.4 로 둘이 거의 붙었고 UN 도 5.4 로 끌어올라** 격차가
> 줄었다 — 직접 이해가 걸리지 않은 주제라 모두 '협력·대화·win-win'이라는 *안전한 공통 어휘*로
> 수렴하는 것으로 보인다. 동사강도(밀도)도 전반적으로 낮아져(2.4 수준) 강경함의 편차가 작아졌다.
> 다만 **완전 수렴은 아니다**: 중국은 여전히 동사강도 max가 높고(4.9), 한국은 거의 강경어를 안 쓴다(1.0).
> 또 표본이 21건뿐이고 프랑스가 빠져 있어 "수렴"은 *경향* 수준으로만 말할 수 있다.
> 요컨대 **당사자성이 낮아지면 소스 간 언어가 협력 쪽으로 수렴하는 경향**이 관찰되나, 단정은 못 한다."""))
    else:
        A(md("""> _여기에 답을 적으세요 (3~6문장)._
>
>"""))

    # (c)
    A(md("""### (c) 이 분석의 한계 2가지

네가 한 분석을 *스스로 반증* 한다면 어디를 공격하겠는가? 구체적으로 2가지."""))
    if KEY:
        A(md("""**📝 모범답 (c) — 둘 이상 들면 만점:**

> 1. **표본이 너무 작고 듬성하다(n=21).** AI 거버넌스는 21건뿐이고 한국은 4건, ai01은 전 소스 0건이다.
>    이 정도 표본으로 낸 평균은 문서 한두 개에 크게 흔들린다 → '경향'까지만, 인과·일반화는 금물.
> 2. **프랑스 부재로 4-소스 비교가 깨졌다.** Q2는 4개 소스 비교가 전제인데 FR=0이라 사실상 3개만 비교한다.
>    게다가 FR 부재 자체가 *측정 창의 한계*(별도 포털)지 진짜 침묵이 아니다 — 비교의 공정성이 흔들린다.
> 3. (추가) **사전·규칙 기반 측정의 한계.** mutuality는 단어 매칭이라 'all parties'가 *비판적 맥락*("all
>    parties failed")으로 쓰여도 협력으로 센다. 또 모든 문서가 영문본이라 한·중·프 원문의 뉘앙스가 번역에서
>    유실됐을 수 있다. 자동 점수는 사람이 원문과 대조해 검증해야 한다(S4 교차언어 검증의 교훈)."""))
    else:
        A(md("""> _여기에 한계 2가지를 적으세요._
>
> 1.
> 2."""))

    # ── (선택) Claude 확장 — DEMO_MODE 가드 ─────────────────────────
    A(md("""## (선택·가산점) Claude 의미 분석 확장 🤖

규칙 기반 점수가 *놓친* framing/미묘한 hedging을 Claude로 교차검증할 수 있다.
**API 키가 없으면 자동으로 건너뛴다(DEMO_MODE).** 키가 있을 때만 한 문서를 분석한다.

> 설계 원칙: *계산은 코드(결정론), 의미 해석은 LLM, 판단은 인간.*
> 모델 id는 `diplo_analysis.claude_semantic` 의 기본값을 따른다."""))
    A(code(r'''# 키가 있을 때만 실행 — 없으면 조용히 DEMO_MODE 로 넘어간다 (채점 비대상, 가산점)
import os
DEMO_MODE = not os.environ.get("ANTHROPIC_API_KEY")
if DEMO_MODE:
    print("ℹ️  DEMO_MODE — ANTHROPIC_API_KEY 가 없어 Claude 확장을 건너뜁니다(정상).")
    print("   규칙 기반 분석만으로 이 과제는 100% 완료됩니다.")
else:
    import anthropic
    from diplo_analysis import claude_semantic
    client = anthropic.Anthropic()
    sample = ai_docs[0]
    result = claude_semantic(sample["text"], client)   # framing/blame/강도/상호성/미묘한 hedging
    print("Claude 의미 분석 (", sample["source"], sample["event_id"], "):")
    for k, v in result.items():
        print(f"  {k}: {v}")'''))

    # ── 제출 안내 / 회고 ────────────────────────────────────────────
    A(md("""## ✅ 제출 전 체크 + 회고

**제출 전 확인**
- [ ] 모든 `# CHECK` 셀에 `✅ PASS` 가 떴다.
- [ ] Step 6 서술형 (a)(b)(c) 를 *내 문장* 으로 채웠다.
- [ ] 차트가 한 장 이상 그려진다.
- [ ] 위에서 아래로 한 번에 다시 실행해도 에러가 없다(Runtime → Restart and run all).

**회고 (제출 안 함, 스스로)**
1. "FR=0"을 처음 봤을 때 무엇이라 해석했나? 구조적 부재임을 안 뒤 해석이 어떻게 바뀌었나?
2. 저당사자성에서 상호성이 *올라간* 게 의외였나? 왜 그럴까?
3. 이 작은 코퍼스(21건)로 기사를 쓴다면, 어떤 문장은 쓰면 안 되는가?

> 🎓 **수고했다.** 4주간 우크라이나·가자에서 함께 깎은 자(尺)를, 새 주제에 혼자 들이대
> *침묵을 발견*하고 *당사자성 가설을 검증*했다. 좋은 분석가의 마지막 덕목 — **자기 숫자를
> 의심하기** — 를 서술형 (c)에서 실천했다면, 이 과제의 진짜 목표를 달성한 것이다."""))

    if KEY:
        A(md("""---
## 🧑‍🏫 강사 종합 노트 (정답본 전용)

**핵심 기대값 한눈에**
- **침묵 지도:** FR=0 (8개 사건 전부). ai01은 전 소스 0. → 학생은 `absent == ["FR"]` 발견.
- **소스 비교(n=21):** UN/KR/CN 만. 상호성 한국 10.63 · 중국 10.43 ≫ UN 5.37.
  동사강도 max 중국 4.89 · UN 3.50 · 한국 1.00. (밀도로 보면 모두 낮음, 한국 0.42.)
- **당사자성 대비:** 상호성 AI 8.54 ≫ 우크라 4.87 / 가자 4.66. 동사밀도 AI 2.41 ≪ 4.77 / 4.00.

**자주 나오는 학생 실수**
1. `verb_strength_max` 원시값만 보고 "중국 강경" 결론 → S4의 길이 편향 교훈을 잊음. 밀도로 봐야 함.
2. 표에 FR 행을 억지로 만들려다 KeyError/NaN. FR은 *데이터가 없는 게 정답*이다.
3. FR=0 을 "프랑스가 AI에 무관심"으로 오독. 실제론 *수집 창의 사각지대*(별도 포털).
4. n=21 + FR 부재를 잊고 인과·일반화로 과한 결론. '경향'까지만 허용.
5. 서술형에서 숫자 근거 없이 인상비평. 채점은 *숫자 인용 + 한계 인지*를 본다.

**채점 시:** CHECK 셀 PASS = 코드 정확성(자동). 서술형은 README 루브릭 표대로.
침묵 지도 발견(FR)과 한계 2가지(특히 n 작음·FR 부재)는 반드시 짚어야 상위 점수."""))

    return cells


if __name__ == "__main__":
    save(build_cells("assignment"), "homework/ai_governance_assignment.ipynb")
    save(build_cells("answerkey"),  "homework/ai_governance_answerkey.ipynb")
    # 검증기가 쓸 수 있게 ANSWERS 쌍 개수 보고
    print(f"TODO(blank→filled) 쌍: {len(ANSWERS)}개")
