# -*- coding: utf-8 -*-
"""session4.ipynb 빌더 — 검증 + 시각화 (주제1: 우크라이나 · 종합)"""
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
md("""# Session 4 — 6차원을 종합하고, *믿을 수 있는지* 검증한다
### 주제 1: 우크라이나 전쟁 · 검증 + 시각화 (캡스톤)

> **오늘 한 문장:** "S2~S3에서 우리는 *손으로* 여섯 개의 자(尺)를 만들었다.
> 오늘은 그 자들을 **한 파일로 묶고**, 우크라이나 전 문서에 들이대고,
> 그림으로 보여준 뒤 — 가장 중요하게 — **그 숫자를 의심한다.**"

지난 세 번의 세션에서 우리는 외교 성명문을 재는 **6개 차원**을 만들었다.

| # | 차원 | 무엇을 재나 | 만든 세션 |
|---|---|---|---|
| 1 | **directness_index** | 직설성 (능동/수동 + 우회표현) | S2 |
| 2 | **verb_strength** | 동사 강도 (note 1 ~ demand 7) | S2 |
| 3 | **subject_pattern** | 주어 패턴 (we / 국가 / 국제사회 / 모든 당사자) | S2 |
| 4 | **mutuality_index** | 상호성 (양면적 표현 밀도) | S3 |
| 5 | **hedging_density** | 완곡어 밀도 | S3 |
| 6 | **silence_map** | 침묵 지도 (사건×소스) | S1 |

오늘의 목표:
1. 흩어진 함수를 **`diplo_analysis.py` 한 파일로 묶은 툴킷**을 쓴다 (한 줄 import).
2. 우크라이나 **157개 문서 전체**를 분석해 결과표를 만들고 **소스별로 집계**한다.
3. **인터랙티브 차트(Plotly)** 로 차이를 *보여준다* — 헤드라인: 상호성 중국 ~12 vs 프랑스 ~1.
4. **검증 1 (교차언어 점검):** 자동 측정값이 원문과 말이 되나 사람이 확인한다.
5. **검증 2 (측정 타당성):** "verb_strength_max가 높은 게 정말 강경해서일까,
   아니면 그냥 *문서가 길어서*일까?" — 길이 편향을 드러내고 고친다.
6. Q1(소스별 차이) 우크라이나 답을 정리하고 **주석 데이터셋**으로 저장한다.

> 💡 **운영 방식:** 셀을 위에서 아래로 하나씩 실행한다.
> `# TODO` 가 보이면 직접 채우고, 바로 아래 `# CHECK` 셀을 실행해 `✅` 가 떠야 다음으로."""),

md("## Step 0 — 환경 설정\n필요한 라이브러리를 설치하고, 프로젝트 폴더를 찾는다."),
code('!pip install spacy plotly pandas -q\n!python -m spacy download en_core_web_sm -q'),
code(SETUP),

md("""## Step 1 — 툴킷 한 줄로 불러오기 🧰

> **오늘의 큰 변화:** S2~S3에서 우리는 `directness_index`, `verb_strength` …
> 같은 함수를 **노트북 안에서 직접** 짰다. 그 함수들을 이제 **한 파일
> (`diplo_analysis.py`)** 로 묶어 두었다. 이제 아래 *한 줄*이면 6차원이 다 나온다.
>
> 이것이 코드가 성숙하는 과정이다 — *실험(노트북) → 정리(모듈) → 재사용(import)*.
> 다음 주(가자)부터는 이 모듈을 그대로 가져다 쓴다. 바퀴를 다시 만들지 않는다."""),
code(r'''# 6차원 툴킷을 한 줄로 import. 내부 구현은 이미 S2~S3에서 다 봤으니 이제 '쓰기'만 한다.
from diplo_analysis import get_nlp, analyze_document, silence_map
from diplo_analysis import VERB_LADDER, MUTUALITY_TERMS   # 사다리/사전도 그대로 재사용

nlp = get_nlp()          # spaCy 모델 1회 로드 (캐시됨)
print("✅ 툴킷 로드 완료")
print("   동사 강도 사다리:", {k: VERB_LADDER[k] for k in ["note","condemn","demand"]}, "...")
print("   상호성 사전 항목 수:", len(MUTUALITY_TERMS), "개")'''),
code(r'''# 진짜로 한 문서가 분석되나? 우크라이나 1번 문서로 즉석 시연 (live)
import json
docs = json.load(open(os.path.join(PROJECT, "data", "ukraine_working.json"), encoding="utf-8"))
print("우크라이나 작업 문서:", len(docs), "건\n")

sample = docs[0]
r = analyze_document(sample, nlp)        # ← 이 한 줄이 6차원(규칙기반 5개)을 다 계산
print(f"[{r['source']}] {r['event_id']} {r['date']}")
for k in ["directness_index","verb_strength_max","verb_strength_mean",
          "mutuality_index","hedging_density","subject_first_person"]:
    print(f"   {k:22s} = {r[k]}")'''),
code(r'''# CHECK Step1 — 툴킷이 정상 동작하는가
try:
    assert callable(analyze_document) and callable(silence_map)
    assert set(["directness_index","verb_strength_max","mutuality_index"]) <= set(r.keys())
    print("✅ PASS — diplo_analysis 한 줄 import 로 6차원 분석 준비 완료")
except Exception as e:
    print("❌ FAIL —", e)'''),

md("""## Step 2 — 우크라이나 전 문서 분석 → 결과표

이제 `analyze_document` 를 **157개 문서 전부**에 돌린다.
spaCy가 매 문서를 구문 분석하므로 30초~1분 정도 걸린다. 기다리자.

> ⚙️ **속도 팁:** 분석 결과는 똑같이 나오게끔 `data/backup/analysis_rule_based.json`
> 에 **미리 계산해** 두었다(354건, 3주제 전체). 수업 중 시간이 없으면 그걸 불러도 된다.
> 하지만 오늘은 "툴킷이 진짜 돈다"를 보여주려 **라이브로** 돌린다."""),
code(r'''import pandas as pd

# (A) 라이브 분석 — 157개 문서를 전부 돌린다 (권장: 한 번은 직접 본다)
rows = [analyze_document(d, nlp) for d in docs]
ana = pd.DataFrame(rows)
print("분석 결과표:", ana.shape)
ana[["source","event_id","directness_index","verb_strength_max",
     "mutuality_index","hedging_density"]].head(6)'''),
code(r'''# (B) (선택) 미리 계산해 둔 결과로 검산 — 라이브 결과와 같은지 확인용
pre = pd.DataFrame(json.load(open(os.path.join(PROJECT,"data","backup",
                   "analysis_rule_based.json"), encoding="utf-8")))
pre_ukr = pre[pre["topic"]=="ukraine"].reset_index(drop=True)
print("미리 계산본(우크라이나):", pre_ukr.shape[0], "건")
print("라이브 mutuality 평균:", round(ana["mutuality_index"].mean(),3),
      "/ 미리 계산본:", round(pre_ukr["mutuality_index"].mean(),3),
      "→ 같으면 재현 OK")'''),
md("""### 소스별 평균 집계 — 오늘의 핵심 표

각 소스(UN/한국/중국/프랑스)가 **평균적으로 어떻게 말하는가**.
이 한 장의 표가 우리 프로젝트 Q1(소스별 차이)의 답이다."""),
code(r'''# TODO: source 별로 묶어 6차원의 평균을 구하라.
#       힌트: ana.groupby("____")[열목록].mean().round(2)
cols = ["directness_index","verb_strength_max","verb_strength_mean",
        "mutuality_index","hedging_density","subject_first_person"]
agg = ana.groupby("______")[cols].mean().round(2)   # ← 빈칸을 채워라
agg = agg.reindex(["UN","KR","CN","FR"])             # 보기 좋게 순서 고정
agg'''),
code(r'''# CHECK Step2 — 집계가 알려진 실제 결과와 맞는가 (소수 오차 허용)
try:
    agg = ana.groupby("source")[cols].mean().round(2).reindex(["UN","KR","CN","FR"])
    mut = agg["mutuality_index"]
    assert mut["CN"] > mut["KR"] > mut["UN"] > mut["FR"], "상호성 순위가 이상하다"
    assert abs(mut["CN"] - 11.92) < 0.6, "중국 상호성 값이 예상과 다르다"
    print("✅ PASS — 소스별 집계 완성")
    print("   상호성 순위: 중국", mut["CN"], "> 한국", mut["KR"],
          "> UN", mut["UN"], "> 프랑스", mut["FR"])
except Exception as e:
    print("❌ FAIL —", e, '\n힌트: ana.groupby("source")[cols].mean()')'''),
md("""<details><summary>💡 힌트 / 정답</summary>

```python
agg = ana.groupby("source")[cols].mean().round(2)
agg = agg.reindex(["UN","KR","CN","FR"])
```
`groupby("source")` 는 같은 소스끼리 행을 묶고, `.mean()` 은 그룹별 평균을 낸다.
`reindex` 는 단지 행 순서를 보기 좋게 고정할 뿐(분석엔 영향 없음).
</details>"""),
md("""**벌써 이야기가 보인다.**
- **중국**의 상호성(`mutuality_index` 11.92)은 프랑스(0.98)의 **약 12배**다.
  "all parties / dialogue / win-win" 같은 *양면적* 단어를 압도적으로 많이 쓴다.
- **directness** 는 네 소스가 0.75~0.86 으로 비슷 — 다들 능동태를 많이 쓴다.
- `verb_strength_max` 는 중국·UN이 높고 한국·프랑스가 낮다 …
  **그런데 이 숫자, 정말 믿어도 될까? → Step 5에서 의심한다.**"""),

md("""## Step 3 — 시각화 (Plotly) 📊
표는 정확하지만 *눈에 안 들어온다.* 같은 숫자를 **인터랙티브 막대·레이더**로 보여주자.
마우스를 올리면 값이 뜨고, 범례를 클릭해 끄고 켤 수 있다."""),
code(r'''import plotly.graph_objects as go
import plotly.express as px

SRC_KO = {"UN":"UN", "KR":"한국", "CN":"중국", "FR":"프랑스"}
SRC_COLOR = {"UN":"#4C78A8", "KR":"#E45756", "CN":"#F58518", "FR":"#54A24B"}
order = ["UN","KR","CN","FR"]
labels = [SRC_KO[s] for s in order]
colors = [SRC_COLOR[s] for s in order]'''),
md("### (a) 헤드라인 — 소스별 상호성 지수 (중국 ~12 vs 프랑스 ~1)"),
code(r'''fig_mut = go.Figure(go.Bar(
    x=labels, y=[agg.loc[s,"mutuality_index"] for s in order],
    marker_color=colors,
    text=[f'{agg.loc[s,"mutuality_index"]:.1f}' for s in order],
    textposition="outside",
))
fig_mut.update_layout(
    title="소스별 상호성 지수 (Mutuality Index) — 1000단어당 양면적 표현",
    xaxis_title="소스", yaxis_title="상호성 지수 (높을수록 '양측 균형' 강조)",
    template="plotly_white", height=420,
)
fig_mut.show()
print("→ 같은 전쟁을 두고, 중국은 '모든 당사자/대화/win-win'을, 프랑스는 거의 안 쓴다.")'''),
md("### (b) 소스별 동사 강도 최댓값 (verb_strength_max)"),
code(r'''# TODO: 위 (a) 막대그래프를 본떠, 이번엔 'verb_strength_max' 막대를 그려라.
#       y 값만 "verb_strength_max" 로 바꾸면 된다.
fig_verb = go.Figure(go.Bar(
    x=labels,
    y=[agg.loc[s,"______________"] for s in order],   # ← 빈칸: 어떤 열?
    marker_color=colors,
    text=[f'{agg.loc[s,"verb_strength_max"]:.1f}' for s in order],
    textposition="outside",
))
fig_verb.update_layout(
    title="소스별 동사 강도 최댓값 (1 note ~ 7 demand)",
    xaxis_title="소스", yaxis_title="평균 최대 동사 강도",
    template="plotly_white", height=420,
)
fig_verb.show()'''),
code(r'''# CHECK Step3b
try:
    ys = [t.y for t in fig_verb.data][0]
    assert abs(ys[order.index("CN")] - agg.loc["CN","verb_strength_max"]) < 1e-6
    print("✅ PASS — verb_strength_max 막대 완성 (중국/UN 높고, 한국/프랑스 낮음)")
except Exception as e:
    print("❌ FAIL —", e, '\n힌트: 빈칸은 "verb_strength_max"')'''),
md("""<details><summary>💡 힌트 / 정답</summary>

빈칸은 `"verb_strength_max"`. (a)와 똑같은 코드에서 y의 열 이름만 바꾸면 된다.
</details>"""),
md("### (c) 6차원 한눈에 — 레이더 차트 (정규화 비교)"),
code(r'''# 6개 차원은 단위가 제각각이라(0~1, 1~7, 0~13 …) 그대로 겹치면 안 보인다.
# 각 차원을 0~1 로 min-max 정규화해 '상대적 모양'을 비교한다.
radar_cols = ["directness_index","verb_strength_max","verb_strength_mean",
              "mutuality_index","hedging_density","subject_first_person"]
radar_ko = ["직설성","동사강도(max)","동사강도(mean)","상호성","완곡어","1인칭(we)"]

norm = agg[radar_cols].copy()
for c in radar_cols:
    lo, hi = norm[c].min(), norm[c].max()
    norm[c] = (norm[c]-lo)/(hi-lo) if hi > lo else 0.5

fig_radar = go.Figure()
for s in order:
    vals = [norm.loc[s,c] for c in radar_cols]
    fig_radar.add_trace(go.Scatterpolar(
        r=vals + [vals[0]], theta=radar_ko + [radar_ko[0]],
        name=SRC_KO[s], line_color=SRC_COLOR[s], fill="toself", opacity=0.45,
    ))
fig_radar.update_layout(
    title="소스별 6차원 프로필 (각 축 0~1 정규화)",
    polar=dict(radialaxis=dict(visible=True, range=[0,1])),
    template="plotly_white", height=520,
)
fig_radar.show()
print("→ 네 나라의 '말하기 지문(指紋)'이 서로 다른 모양으로 보인다.")'''),

md("""## Step 3.5 — 새 차원 3개: 9차원으로 확장 🆕
> **툴킷이 자랐다.** S2~S3에서 만든 6차원 위에, v2 툴킷은 **3개 차원**을 더 얹었다.
> `analyze_document` 한 줄이 이제 **9차원**을 한 번에 돌려준다(위에서 이미 다 계산돼 있었다!).

| # | 새 차원 | 무엇을 재나 | 컬럼 |
|---|---|---|---|
| 7 | **완곡명명 (event naming)** | 사건을 *뭐라 부르나* — 강한 규정 ↔ 완곡 | `naming_escalation` |
| 8 | **귀속 직접성 (blame)** | 가해자를 *직접 지목*했나, 행위자를 가렸나 | `blame_directness` |
| 9 | **대상별 태도 (sentiment)** | 행위자별 감정 비대칭 (누구를 가장 비판?) | `sentiment_gap`, `most_criticized` |

### (7) 완곡명명 — 같은 전쟁을 'invasion'이라 부르나 'situation'이라 부르나
> 같은 사건도 **부르는 단어**가 입장을 드러낸다. 사전에 0~3 가중치를 매겼다:
> `invasion / war of aggression = 3 (강한 규정)` … `war = 2` … `conflict / crisis = 1 (완곡)`
> … `situation / military operation = 0 (가장 완곡)`.
> `naming_escalation` 은 문서에 등장한 명명 단어들의 **가중 평균**이다 (높을수록 단호한 규정)."""),
code(r'''# event_naming 을 직접 한 문장에 적용해 본다 — 같은 사건, 다른 단어
from diplo_analysis import event_naming

for phrase in ["Russia's invasion of Ukraine is a war of aggression.",
               "We are concerned about the conflict and the situation in Ukraine."]:
    nm = event_naming(phrase, "ukraine", lang="en")
    print(f'"{phrase[:48]}..."')
    print(f"   → 명명 단어 {nm['naming_terms']}  escalation={nm['naming_escalation']}  "
          f"(0 완곡 ~ 3 강한 규정)\n")
print("→ 첫 문장은 'invasion/war'(강), 둘째는 'conflict/situation'(완곡). 단어가 입장이다.")'''),
md("### 소스별 명명 등록(register) — 누가 가장 완곡하게 부르나"),
code(r'''# analyze_document 가 이미 채워 둔 naming_escalation 컬럼을 소스별로 집계한다.
#   (None=명명 단어가 없던 문서는 평균에서 자동 제외)
naming_by_src = ana.groupby("source")["naming_escalation"].mean().round(2).reindex(order)
print("우크라이나 — 소스별 평균 명명 등록(naming_escalation):")
print(naming_by_src)
print("\n→ 우크라이나만 보면 네 소스 모두 'war/invasion'을 비교적 단호히 쓴다.")
print("   하지만 가자까지 합치면 그림이 달라진다 ↓")'''),
code(r'''# 가자까지 합쳐(전쟁 2주제) 보면 '중국이 가장 완곡'이 드러난다.
gaza_docs = json.load(open(os.path.join(PROJECT,"data","gaza_working.json"), encoding="utf-8"))
both = pd.DataFrame([analyze_document(d, nlp) for d in (docs + gaza_docs)])
naming_both = both.groupby("source")["naming_escalation"].mean().round(2)
naming_both = naming_both.sort_values(ascending=False)
print("우크라이나+가자 — 소스별 명명 등록(높을수록 단호):")
print(naming_both)
print("\n→ UN(~1.54)이 가장 단호히 규정. 중국(~1.10)이 가장 완곡 — 'conflict/crisis' 선호.")'''),
code(r'''# CHECK Step3.5 — 명명 등록 순위가 알려진 결과와 맞는가
try:
    nb_ = both.groupby("source")["naming_escalation"].mean().round(2)
    assert nb_["UN"] >= nb_["CN"], "UN이 중국보다 단호해야 한다"
    assert nb_["CN"] == nb_.min(), "중국이 가장 완곡해야 한다('conflict/crisis')"
    print("✅ PASS — 명명 등록 분석 완성")
    print(f"   가장 단호: UN {nb_['UN']}  /  가장 완곡: 중국 {nb_['CN']}")
except Exception as e:
    print("❌ FAIL —", e)'''),
md("""<details><summary>💡 왜 우크라이나만 보면 안 되고 두 주제를 합치나?</summary>

우크라이나 단일 주제에서는 러시아 '침공'이 워낙 명백해 네 소스 다 'war/invasion'을 쓴다(차이가 작다).
**가자**처럼 입장이 더 갈리는 주제를 합치면, 중국이 'conflict/crisis/situation' 같은
**완곡한 단어**를 선호하는 경향이 평균에서 드러난다. 한 사건만 보지 말고 **여러 사건에 걸친
패턴**을 봐야 명명 전략이 보인다 — 이것도 검증의 한 형태다.
</details>"""),
md("""### (8·9) 9차원 통합 시각화 — 새 차원까지 한 그림에
> 6차원 막대·레이더에 **명명(7)·귀속(8)** 을 얹는다. 단위가 다르니
> (escalation 0~3, blame_directness 0~1) **그룹 막대**로 나란히 본다."""),
code(r'''# 새 두 차원을 소스별로 — naming_escalation(완곡명명) + blame_directness(귀속 직접성)
ext = ana.groupby("source")[["naming_escalation","blame_directness"]].mean().round(2).reindex(order)

fig_ext = go.Figure()
fig_ext.add_trace(go.Bar(name="완곡명명 (0 완곡~3 단호)", x=labels,
    y=[ext.loc[s,"naming_escalation"] for s in order], marker_color="#72B7B2"))
fig_ext.add_trace(go.Bar(name="귀속 직접성 (0~1, 가해자 직접지목)", x=labels,
    y=[ext.loc[s,"blame_directness"] for s in order], marker_color="#B279A2"))
fig_ext.update_layout(
    title="새 차원 — 소스별 명명 등록 & 귀속 직접성",
    barmode="group", template="plotly_white", height=440,
    xaxis_title="소스", yaxis_title="값 (차원별 스케일 다름·모양 비교)")
fig_ext.show()
print("→ '얼마나 단호히 규정하나(명명)'와 '가해자를 직접 지목하나(귀속)'를 한눈에 비교.")'''),
md("### 9차원 레이더 — 6차원 + 새 3차원 (각 축 0~1 정규화)"),
code(r'''# 6차원 레이더를 9축으로 확장한다. 단위가 제각각이라 다시 0~1 min-max 정규화.
#   sentiment 차원은 sentiment_gap(행위자 간 감정 격차)을 쓴다.
nine_cols = ["directness_index","verb_strength_max","mutuality_index",
             "hedging_density","subject_first_person",
             "naming_escalation","blame_directness","sentiment_gap"]
nine_ko = ["직설성","동사강도","상호성","완곡어","1인칭",
           "완곡명명","귀속직접성","감정격차"]

nine = ana.groupby("source")[nine_cols].mean().reindex(order)
nine_norm = nine.copy()
for c in nine_cols:
    col = nine_norm[c]
    lo, hi = col.min(), col.max()
    nine_norm[c] = (col - lo) / (hi - lo) if hi > lo else 0.5
nine_norm = nine_norm.fillna(0)   # 명명/귀속/감정이 None인 소스는 0으로

fig_radar9 = go.Figure()
for s in order:
    vals = [nine_norm.loc[s,c] for c in nine_cols]
    fig_radar9.add_trace(go.Scatterpolar(
        r=vals + [vals[0]], theta=nine_ko + [nine_ko[0]],
        name=SRC_KO[s], line_color=SRC_COLOR[s], fill="toself", opacity=0.4))
fig_radar9.update_layout(
    title="소스별 9차원 프로필 (각 축 0~1 정규화)",
    polar=dict(radialaxis=dict(visible=True, range=[0,1])),
    template="plotly_white", height=560)
fig_radar9.show()
print("→ 6차원 지문에 명명·귀속·감정 3축이 더해져 '말하기 지문'이 더 촘촘해졌다.")'''),

md("""## Step 4 — 검증 1: 교차언어 점검 (사람이 직접 본다) 🔍🌐

> **핵심 메시지:** "기계가 0.86이라 했다고 그게 진실은 아니다.
> 자동 측정값이 **원문을 읽었을 때 말이 되는지** 사람이 확인해야 한다.
> 너는 한국어·중국어·프랑스어를 읽을 수 있다 — 이건 강력한 검증 무기다."

방법: 소스마다 대표 문서를 **1건씩** 골라, 자동 측정값과 **원문 URL**을 나란히 뽑는다.
그리고 **체크리스트**대로 원문을 직접 열어 "이 숫자가 납득되나" 판정한다.
(실제 원문 대조는 **너의 몫**이다. 노트북은 *대상과 측정값*만 차려 준다.)"""),
code(r'''# 소스별로 '상호성이 가장 두드러진' 문서 1건씩 뽑아 검증 대상으로 삼는다.
ana2 = ana.merge(pd.DataFrame(docs)[["id","url","title","lang","text"]], on="id", how="left")

spot = []
for s in order:
    sub = ana2[ana2["source"]==s].sort_values("mutuality_index", ascending=False)
    spot.append(sub.iloc[0])
spot = pd.DataFrame(spot)

for _, r in spot.iterrows():
    print(f"━━ [{SRC_KO[r['source']]}] {r['event_id']}  ({r['lang']})")
    print(f"   제목 : {str(r['title'])[:70]}")
    print(f"   URL  : {r['url']}")
    print(f"   자동측정 → 상호성 {r['mutuality_index']}, 직설성 {r['directness_index']},"
          f" 동사강도max {r['verb_strength_max']}")
    print(f"   본문 앞부분: {str(r['text'])[:160].strip()}...")
    print()'''),
md("""### ✅ 교차언어 검증 체크리스트 (원문 URL을 직접 열고 채운다)

각 문서 URL을 클릭해 원문을 읽고, 아래 4문항에 직접 답해 보자.

| 문서 | (1) 상호성이 높다면 'all parties/대화/win-win' 류 표현이 실제로 보이나? | (2) 직설성 점수가 능동/수동 비율과 맞나? | (3) 동사강도 max에 해당하는 단어(condemn/demand 등)가 실제 있나? | (4) 측정이 *놓친* 뉘앙스가 있나? |
|---|---|---|---|---|
| 중국 (zh→en) | | | | |
| 한국 (ko→en) | | | | |
| 프랑스 (fr→en) | | | | |

> 💬 **자주 나오는 발견:** 중국 영문본은 "all parties"가 정말 자주 보인다(측정 타당).
> 반대로 프랑스는 *짧고 사무적*이라 상호성 단어가 없어 점수가 0에 가깝다 —
> 이건 "프랑스가 비협조적"이라서가 아니라 **문체가 달라서**일 수 있다(측정의 한계!)."""),
code(r'''# (선택) TODO 같은 자리: 특정 문서의 '상호성 단어가 실제로 무엇이었는지' 직접 확인
from diplo_analysis import mutuality_index
cn_doc = spot[spot["source"]=="CN"].iloc[0]
detail = mutuality_index(cn_doc["text"])
print("중국 문서가 실제로 쓴 양면적 표현(횟수):")
for term, n in sorted(detail["mutuality_hits"].items(), key=lambda x:-x[1]):
    print(f"   {term:28s} {n}회")'''),

md("""### Step 4.5 — 검증을 한 단계 더: **원어(原語) 분석** 🌐🔬
> **지금까지의 한계를 솔직히 말한다.** 우리 코퍼스는 **영문본(영어 번역/영어 성명)** 이다
> (`lang="en"`). 즉 한국·중국·프랑스의 *진짜 단어*가 아니라 **번역된 단어**를 재고 있었다.
> 번역은 뉘앙스를 깎는다 — "局势(국면)"가 "situation"으로, "谴责(규탄)"이 "condemn"으로.
>
> **툴킷은 이미 다국어다.** 핵심 함수들이 `lang=` 인자를 받는다:
> - `mutuality_index(text, lang="zh")` — 중국어 상호성 사전
> - `event_naming(text, topic, lang="ko")` — 한국어 명명 사전
> - `hedging_density(text, lang="fr")` — 프랑스어 완곡어 사전
> - `get_nlp_multi(lang)` — 언어별 spaCy 모델 (구문 분석이 필요할 때)
>
> 아래는 **실제 외교 표현**으로 다국어 사전이 원문에서 제대로 작동함을 보이는 시연이다.
> (사전 기반 함수라 **모델 설치 없이** 바로 돈다.)"""),
code(r'''# 다국어 사전 함수는 spaCy 모델 없이 동작한다 — 실제 외교 표현으로 검증
from diplo_analysis import mutuality_index, event_naming, hedging_density

# 진짜 외교 문구 (원어 그대로)
zh = "中方呼吁有关各方通过对话与谈判和平解决，反对战争"          # 중국 외교부 식 표현
fr = "La France condamne l'invasion et l'agression de la Russie en Ukraine."  # 프랑스
ko = "정부는 모든 당사자에게 대화를 통한 평화적 해결을 촉구한다."   # 한국 외교부 식 표현

# (1) 중국어 — 상호성 사전이 各方/对话/和平/谈判 에 반응하나?
mz = mutuality_index(zh, lang="zh")
print("[zh] 상호성 발화:", list(mz["mutuality_hits"]))
print("     → 各方(각 당사자)·对话(대화)·和平(평화)·谈判(협상) 포착 = 원문에서 직접 측정 성공\n")

# (2) 프랑스어 — 명명 사전이 invasion 을 '강한 규정(3)'으로 잡나?
nf = event_naming(fr, "ukraine", lang="fr")
print("[fr] 명명 단어:", nf["naming_terms"], "→ dominant =", nf["naming_dominant"],
      f"(escalation {nf['naming_escalation']})")
print("     → invasion/agression = 가중치 3 = 가장 단호한 규정\n")

# (3) 한국어 — 상호성 사전이 모든 당사자/대화/평화적 에 반응하나?
mk = mutuality_index(ko, lang="ko")
print("[ko] 상호성 발화:", list(mk["mutuality_hits"]),
      "→ 번역을 거치지 않은 원문에서 직접 측정")'''),
code(r'''# CHECK Step4.5 — 다국어 사전이 원어를 제대로 측정하는가 (모델 불필요)
try:
    assert "各方" in mutuality_index(zh, lang="zh")["mutuality_hits"]
    assert event_naming(fr, "ukraine", lang="fr")["naming_dominant"] == "invasion"
    assert "모든 당사자" in mutuality_index(ko, lang="ko")["mutuality_hits"]
    print("✅ PASS — zh/ko/fr 원어 사전이 실제 외교 표현에서 정확히 작동")
    print("   (en 외 spaCy 모델 다운로드 없이 — 사전 기반이라 가능)")
except Exception as e:
    print("❌ FAIL —", e)'''),
md("""<details><summary>💡 CHECK: 그럼 지금 당장 한·중·프 *원문*을 분석할 수 있나?</summary>

**아니다 — 두 가지가 더 필요하다.** 솔직해야 분석이 믿음직하다.

1. **원어 코퍼스 수집.** 현재 `ukraine_working.json` 의 `text` 는 전부 영문본이다.
   원어를 재려면 스크래퍼를 **각국 자국어판**(중국 외교부 中文, 프랑스 français, 한국 국문)으로
   확장해 원문을 모아야 한다.
2. **언어별 spaCy 모델 설치** (구문 분석=직설성·귀속에 필요):
   `python -m spacy download fr_core_news_sm zh_core_web_sm ko_core_news_sm`
   → 그 뒤 `get_nlp_multi("zh")` 로 중국어 모델을 로드한다.
   (오늘 검증에서는 **모델을 부르지 않는다** — 미설치 상태에서도 돌게 사전 함수만 시연.)

**왜 이게 이 프로젝트의 최우선 신뢰도 업그레이드인가?**
번역본은 *원문의 명명·완곡 전략을 평탄화*한다. 너는 **한·중·프·영을 읽는 trilingual 자산**을
가졌다 — 원어를 직접 재면 "중국이 局势(국면)라 부르는 걸 영문에선 conflict로 옮겼다" 같은
**번역이 숨긴 차이**까지 잡아낼 수 있다. 이게 남이 못 하는 너만의 분석이다.
다국어 사전은 위처럼 **실제 외교 표현으로 이미 검증**돼 있으니, 남은 건 *원어 데이터*뿐이다.
</details>"""),

md("""## Step 5 — 검증 2: 측정 타당성 (오늘의 가장 중요한 30분) ⚠️

> **한 문장:** "숫자를 믿기 전에, 그 숫자가 *왜* 그런지 의심하라."

Step 2에서 `verb_strength_max` 가 중국·UN은 높고 한국·프랑스는 낮았다.
순진하게 읽으면 "중국·UN이 더 강경하다". **정말 그럴까?**

`verb_strength_max` 는 *문서에 등장한 강도동사 중 최댓값*이다.
그런데 **문서가 길면** 우연히라도 강한 동사가 한 번쯤 나올 확률이 높아진다.
즉 이 점수는 **'강경함'이 아니라 '문서 길이'를 재고 있을지 모른다.** 이것을
**측정 편향(length bias)** 이라 한다. 데이터로 직접 까 보자."""),
code(r'''# 각 문서의 길이(글자수·단어수)를 붙인다.
ana2["text_len"]  = ana2["text"].str.len()
ana2["n_words"]   = ana2["text"].str.split().str.len()
print("소스별 평균 글자수:")
print(ana2.groupby("source")["text_len"].mean().round(0).reindex(order).astype(int))
print("\n→ 중국 ~17,000자, UN ~28,000자. 한국·프랑스는 ~1,300자. 길이가 13~22배 차이!")'''),
md("### (5-1) 길이 ↔ 동사강도 상관 — 산점도 + 상관계수"),
code(r'''corr_max = ana2["verb_strength_max"].corr(ana2["text_len"])
print(f"상관계수(verb_strength_max vs 글자수) = {corr_max:.3f}")

fig_bias = px.scatter(
    ana2, x="text_len", y="verb_strength_max",
    color="source", color_discrete_map=SRC_COLOR,
    hover_data=["event_id"], log_x=True,
    labels={"text_len":"문서 길이 (글자수, 로그축)","verb_strength_max":"동사강도 max",
            "source":"소스"},
    title=f"길이가 길수록 동사강도 max가 높다 (상관계수 r={corr_max:.2f})",
)
fig_bias.update_layout(template="plotly_white", height=460)
fig_bias.show()
print("→ 오른쪽 위로 쏠린다 = 긴 문서일수록 max가 높다. '강경'이 아니라 '길이' 효과 의심.")'''),
md("""### (5-2) 더 날카롭게 — 강도동사 *개수* 는 길이에 거의 비례한다

`verb_strength_max` 만 보면 애매하니, **강도동사가 몇 번 나왔나(`n_strength_verbs`)** 를
길이와 비교해 보자. 이건 길이와 거의 *직선*으로 붙는다 — 결정적 증거다."""),
code(r'''corr_cnt = ana2["n_strength_verbs"].corr(ana2["n_words"])
print(f"상관계수(강도동사 개수 vs 단어수) = {corr_cnt:.3f}  ← 1에 가까우면 '거의 길이 그 자체'")
print("소스별 강도동사 평균 개수:")
print(ana2.groupby("source")["n_strength_verbs"].mean().round(1).reindex(order))'''),
md("""### (5-3) 해결책 — '1000단어당 강도동사 밀도'로 정규화

길이 효과를 없애려면 **개수를 길이로 나눈다**: `밀도 = 강도동사 수 / 단어수 × 1000`.
(상호성·완곡어는 이미 이 방식으로 정규화돼 있었다 — 동사강도만 빠져 있었던 것.)"""),
code(r'''# TODO: 1000단어당 강도동사 '밀도'를 계산하라.
#       힌트: n_strength_verbs 를 n_words 로 나누고 1000 을 곱한다.
ana2["verb_density"] = ana2["______________"] / ana2["n_words"] * 1000   # ← 빈칸

cmp = ana2.groupby("source").agg(
    원시_max=("verb_strength_max","mean"),
    강도동사_개수=("n_strength_verbs","mean"),
    밀도_1000단어당=("verb_density","mean"),
).round(2).reindex(order)
cmp'''),
code(r'''# CHECK Step5
try:
    corr_density = ana2["verb_density"].corr(ana2["n_words"])
    assert ana2["verb_density"].notna().all()
    assert abs(corr_cnt) > 0.8, "개수~길이 상관이 예상보다 약하다"
    assert abs(corr_density) < abs(corr_cnt), "정규화 후 상관이 더 줄어야 한다"
    print("✅ PASS — 길이 편향을 드러내고 밀도로 정규화했다.")
    print(f"   강도동사 개수 vs 길이 상관 : {corr_cnt:.2f}  (강함 = 길이에 끌려감)")
    print(f"   밀도        vs 길이 상관 : {corr_density:.2f}  (약함 = 길이 효과 제거됨)")
except Exception as e:
    print("❌ FAIL —", e, '\n힌트: 빈칸은 "n_strength_verbs"')'''),
md("""<details><summary>💡 힌트 / 정답</summary>

```python
ana2["verb_density"] = ana2["n_strength_verbs"] / ana2["n_words"] * 1000
```
나눗셈 한 번이 측정을 '길이 측정기'에서 '강경함 측정기'로 바꾼다.
</details>"""),
code(r'''# 정규화 전/후 비교 막대 — 결론을 눈으로 못 박는다
fig_fix = go.Figure()
fig_fix.add_trace(go.Bar(name="원시 max (길이 편향)", x=labels,
    y=[cmp.loc[s,"원시_max"] for s in order], marker_color="#bbbbbb"))
fig_fix.add_trace(go.Bar(name="밀도(1000단어당, 정규화)", x=labels,
    y=[cmp.loc[s,"밀도_1000단어당"] for s in order], marker_color="#E45756"))
fig_fix.update_layout(
    title="정규화하면 순위가 바뀐다 — '길어서 강해 보인' 착시 제거",
    barmode="group", template="plotly_white", height=440,
    yaxis_title="값(스케일 다름·모양만 비교)")
fig_fix.show()'''),
md("""> **이번 검증이 보여준 것 (반드시 기록):**
> - `n_strength_verbs`(강도동사 개수)는 단어수와 상관 **≈0.94** — 거의 *길이 그 자체*였다.
> - 밀도로 정규화하면 길이 상관이 **≈0.31** 으로 떨어진다 — 길이 효과가 제거됐다.
> - **순위가 바뀐다:** 원시 max로는 중국이 1위(6.2)였지만, 1000단어당 밀도로 보면
>   **UN·한국이 상위(≈7.4, 6.8)** 로 올라오고 **중국은 중하위권(≈5.5)** 으로, 프랑스(≈3.3)가 최하로 떨어진다.
>   짧고 단호한 한국의 강도동사 *밀도*는 원래 높았고, 중국은 *길어서* 높아 보였던 것.
>   (우크라이나+가자를 합쳐도 같다: 한국 ≈7.5 ≈ UN ≈7.4 상위, 중국 ≈5.3 중하위.)
>
> 교훈: **"중국이 더 강경하다"는 처음 결론은 측정 편향의 산물이었다 — 정규화하니 중국이 원시 1위에서 중하위권으로 내려앉고, UN·한국이 상위로 올라온다.**
> 좋은 분석가는 자기 숫자를 *반증하려* 든다. 그래야 남는 결론이 진짜다."""),

md("""## Step 6 — Q1 우크라이나 답 정리 + 주석 데이터셋 저장 💾

우리 프로젝트의 큰 질문 **Q1: "같은 사건을 두고 소스별로 말하기가 다른가?"** —
우크라이나에 대한 답을 정리하고, 6차원 결과를 CSV로 남긴다(다음 비교의 기준선)."""),
code(r'''# 소스별 6차원 + 정규화 동사밀도까지 담은 최종 집계표
final_cols = ["directness_index","verb_strength_max","verb_density",
              "mutuality_index","hedging_density","subject_first_person"]
final = ana2.groupby("source")[final_cols].mean().round(3).reindex(order)
final.index = [SRC_KO[s] for s in order]
print("== Q1 우크라이나 — 소스별 6차원 요약 ==")
final'''),
code(r'''# 문서 단위 주석 데이터셋(annotated)도 함께 저장 — 재현·후속분석용
out_dir = os.path.join(PROJECT, "data")
keep = ["id","source","event_id","date","directness_index","verb_strength_max",
        "verb_strength_mean","verb_density","mutuality_index","hedging_density",
        "subject_first_person","subject_all_parties","subject_national",
        "text_len","n_words","n_strength_verbs"]
ana2[keep].to_csv(os.path.join(out_dir,"ukraine_annotated.csv"),
                  index=False, encoding="utf-8-sig")
final.to_csv(os.path.join(out_dir,"ukraine_source_summary.csv"), encoding="utf-8-sig")
print("✅ 저장:")
print("   data/ukraine_annotated.csv      (문서별 6차원, ", len(ana2), "행 )")
print("   data/ukraine_source_summary.csv (소스별 요약 4행)")'''),
code(r'''# CHECK Step6
try:
    assert os.path.exists(os.path.join(out_dir,"ukraine_annotated.csv"))
    assert os.path.exists(os.path.join(out_dir,"ukraine_source_summary.csv"))
    chk = pd.read_csv(os.path.join(out_dir,"ukraine_annotated.csv"))
    assert len(chk) == len(docs) and "verb_density" in chk.columns
    print("✅ PASS — 주석 데이터셋 저장 완료 (", len(chk), "행 ).")
except Exception as e:
    print("❌ FAIL —", e)'''),
md("""### 📌 Q1 우크라이나 — 한 문단 결론

> 같은 우크라이나 전쟁을 두고 네 소스는 **눈에 띄게 다르게** 말한다.
> **중국**은 상호성 표현(all parties·대화·win-win)을 압도적으로 많이 써(≈12, 프랑스의 약 12배)
> *중립·균형*의 프레임을 세운다. **한국**은 짧지만 강도동사 *밀도*가 높아 — 길이를 보정하면 —
> UN과 더불어 상위로, 의외로 단호하다. **프랑스**는 짧고 사무적이라 상호성·강도 점수가 모두 낮은데, 이는
> "소극적"이라기보다 **문체 차이**일 수 있다(측정의 한계). **UN**은 길고 절차적이다.
> 그리고 우리는 — 가장 중요하게 — `verb_strength_max` 가 **문서 길이에 오염**돼 있었음을
> 찾아내 **밀도로 교정**했다. 결론은 *교정된 숫자* 위에서만 말한다."""),

md("""## 🎯 회고 (5분)

1. **측정 편향**: `verb_strength_max` 말고도 길이에 오염될 수 있는 차원이 또 있을까?
   (힌트: 개수 기반 vs 밀도 기반. 어떤 게 안전한가?)
2. **교차언어 검증**에서 자동 점수와 원문이 *어긋난* 사례를 찾았는가? 왜 어긋났나?
3. **프랑스가 점수가 낮은 것**은 "협조적이지 않아서"인가 "문체가 짧아서"인가?
   숫자만으로 단정할 수 있나? 무엇을 더 봐야 하나?
4. 오늘 만든 차트 중 *하나만* 기사에 싣는다면 어느 것? 왜?

## ▶️ 다음 (Session 5 — 주제 전환: 가자)
> "우크라이나 한 주제에 네 번을 썼다. 이제 파이프라인이 손에 익었으니,
> **가자(Gaza) 분쟁**에는 `diplo_analysis` 를 그대로 들고 가 **훨씬 빠르게** 같은 6차원을
> 뽑는다. 그리고 새 무기 하나 — **시계열(time series)**: '10월 7일 이후 각국의 동사강도가
> 시간에 따라 어떻게 변했나'를 본다. 같은 자, 새로운 전장."""),
]

save(cells, "session4/session4.ipynb")
