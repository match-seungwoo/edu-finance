# -*- coding: utf-8 -*-
"""session6.ipynb 빌더 — 가자 시계열·종합 (주제2 캡스톤)"""
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
md("""# Session 6 — 시간의 축을 더한다, 그리고 한 장으로 말한다
### 주제 2: 가자 / 이스라엘-팔레스타인 · 시계열·종합 (주제2 캡스톤)

> **오늘 한 문장:** "지금까지는 *평균*만 봤다. 평균은 시간을 지운다.
> 오늘은 **시간 축**을 더한다 — 2023년 10월 7일부터 2025년 8월까지,
> 각 소스의 톤이 사건의 흐름 속에서 어떻게 출렁였나. 그리고 묻는다:
> **누가 가장 일관되고(consistent), 누가 가장 유연한가(flexible)?** (Q3)"

오늘의 목표:
1. **시계열 분석:** 사건 날짜를 x축에 놓고 소스별 톤(상호성·동사밀도)의 궤적을 그린다.
2. **일관성 vs 유연성 순위:** 각 소스의 시간에 따른 *분산(std)* 을 재 순위를 매긴다.
3. **침묵 지도 심화:** 가자에서 누가 *법적 사건(ICJ/ICC)* 에 침묵하나 —
   우크라이나 침묵 패턴과 겹쳐 본다.
4. **Visual Essay 산출물:** 기사/영상에 바로 쓸 **잘 다듬어진 Plotly 그림 한 장** +
   일반 독자용 **한국어 내러티브 캡션** 3~4문장.
5. **Q1/Q2/Q3 가자 결론**을 정리하고 `gaza_annotated.csv` 로 저장한다.

> 💡 **운영 방식:** 셀을 위에서 아래로 하나씩 실행한다.
> `# TODO` 가 보이면 직접 채우고, 바로 아래 `# CHECK` 셀을 실행해 `✅` 가 떠야 다음으로."""),

md("## Step 0 — 환경 설정\n필요한 라이브러리를 설치하고, 프로젝트 폴더를 찾는다."),
code('!pip install spacy plotly pandas -q\n!python -m spacy download en_core_web_sm -q'),
code(SETUP),

md("""## Step 1 — 가자 데이터 + 6차원 재계산 (빠르게)

S5에서 만든 `gaza_working.json` 을 불러와 툴킷으로 6차원을 다시 계산한다.
(S5와 동일한 한 줄 함수. 시계열에 쓰려고 **날짜**도 함께 챙긴다.)"""),
code(r'''from diplo_analysis import analyze_document, silence_map, get_nlp
import json, pandas as pd

nlp = get_nlp()
g = json.load(open(os.path.join(PROJECT,"data","gaza_working.json"), encoding="utf-8"))
print("가자 작업 문서:", len(g), "건")

ana = pd.DataFrame([analyze_document(d, nlp) for d in g]).merge(
      pd.DataFrame(g)[["id","text","title","url","lang"]], on="id", how="left")
ana["n_words"] = ana["text"].str.split().str.len()
ana["verb_density"] = ana["n_strength_verbs"] / ana["n_words"] * 1000   # S4 교훈: 길이 정규화
ana["date"] = pd.to_datetime(ana["date"])     # 시계열을 위한 날짜형 변환
order = ["UN","KR","CN","FR"]
print("분석 완료:", ana.shape)
ana[["source","event_id","date","mutuality_index","verb_density"]].head()'''),
code(r'''# CHECK Step1
try:
    assert len(ana) == 77 and "verb_density" in ana.columns
    assert str(ana["date"].dtype).startswith("datetime")
    print("✅ PASS — 가자 77건 6차원 + 날짜 준비 완료")
except Exception as e:
    print("❌ FAIL —", e)'''),

md("""## Step 2 — 시계열 분석: 톤은 시간 따라 출렁이는가 📈
### → 프로젝트 Q3(일관성 vs 유연성)

가자 사건은 **2023-10 → 2025-08** 로 날짜가 있다. 사건별로 소스의 평균 톤을 구해
**x=사건 날짜, 소스별 한 선**으로 그린다. 먼저 핵심 차원 **상호성**으로."""),
code(r'''# 사건(날짜)×소스 평균 — 시계열의 원재료
ts = (ana.groupby(["source","event_id","date"])[["mutuality_index","verb_density"]]
        .mean().reset_index().sort_values("date"))
ts.head(8)'''),
code(r'''import plotly.graph_objects as go
SRC_KO = {"UN":"UN","KR":"한국","CN":"중국","FR":"프랑스"}
SRC_COLOR = {"UN":"#4C78A8","KR":"#E45756","CN":"#F58518","FR":"#54A24B"}

fig_ts = go.Figure()
for s in order:
    sub = ts[ts["source"]==s].sort_values("date")
    fig_ts.add_trace(go.Scatter(
        x=sub["date"], y=sub["mutuality_index"],
        mode="lines+markers", name=SRC_KO[s], line_color=SRC_COLOR[s],
    ))
fig_ts.update_layout(
    title="가자 — 상호성 지수의 시간 궤적 (2023.10 → 2025.08)",
    xaxis_title="사건 발생일", yaxis_title="상호성 지수",
    template="plotly_white", height=460,
)
fig_ts.show()
print("→ 중국 선은 높게 '평평'하고, 한국 선은 위아래로 크게 '출렁'인다 — 일관 vs 유연.")'''),
md("""### 일관성 vs 유연성 순위 — 시간에 따른 분산(std)

선이 **평평하면 일관**(같은 톤 유지), **요동치면 유연**(사건마다 톤 변경).
이걸 숫자로: 각 소스의 사건별 상호성 값의 **표준편차(std)** 를 잰다. 낮을수록 일관."""),
code(r'''# TODO: 소스별로 사건별 상호성의 표준편차를 구하라. 힌트: .std()
ev = ana.groupby(["source","event_id"])["mutuality_index"].mean().reset_index()
consistency = ev.groupby("source")["mutuality_index"].______().round(2).reindex(order)  # ← 빈칸
rank = consistency.sort_values()
print("== 상호성 일관성 순위 (std 낮을수록 일관) ==")
for s in rank.index:
    label = "가장 일관적" if s==rank.index[0] else ("가장 유연함" if s==rank.index[-1] else "")
    print(f"  {SRC_KO[s]:4s}  std = {rank[s]:>5}   {label}")'''),
code(r'''# CHECK Step2
try:
    consistency = ev.groupby("source")["mutuality_index"].std().round(2).reindex(order)
    rank = consistency.sort_values()
    assert rank.index[0] == "UN", "상호성에서 가장 일관된 소스는 UN이어야 한다"
    assert rank.index[-1] == "KR", "상호성에서 가장 유연한 소스는 한국이어야 한다"
    print("✅ PASS — 상호성 일관성 순위: UN(가장 일관) … 한국(가장 유연)")
except Exception as e:
    print("❌ FAIL —", e, '\n힌트: 빈칸은 std')'''),
md("""<details><summary>💡 힌트 / 정답</summary>

```python
consistency = ev.groupby("source")["mutuality_index"].std().round(2).reindex(order)
```
`std()` 는 표준편차 — 값들이 평균에서 얼마나 흩어졌는지. 작을수록 '한결같다'.
</details>"""),
md("""### 차원을 바꾸면 순위도 바뀐다 — 동사강도 밀도의 일관성

상호성에선 UN이 가장 일관적이었다. **동사강도 밀도**로 보면? 차원마다 '누가 한결같은가'가
달라질 수 있다 — 이게 분석의 묘미다."""),
code(r'''ev2 = ana.groupby(["source","event_id"])["verb_density"].mean().reset_index()
cons_verb = ev2.groupby("source")["verb_density"].std().round(2).reindex(order).sort_values()
print("== 동사강도 밀도 일관성 순위 (std 낮을수록 일관) ==")
for s in cons_verb.index:
    print(f"  {SRC_KO[s]:4s}  std = {cons_verb[s]:>6}")
print("\n→ 동사강도에선 '중국'이 가장 한결같다. 한국은 여기서도 가장 출렁인다.")'''),

md("""## Step 3 — 침묵 지도 심화: 누가 *법* 앞에서 입을 다무나 🤫⚖️

침묵은 무작위가 아니다. **무엇에 대해** 침묵하느냐가 신호다.
가자 사건을 **법적 변곡점(ICJ/ICC)** vs **상징적/군사적 사건**으로 나눠
소스별 침묵률을 비교한다 — 우크라이나에서 본 패턴과 겹쳐 본다."""),
code(r'''from scrapers.events import events_for
smap = pd.DataFrame(silence_map(g, events_for("gaza")))

LEGAL = {"gaza05","gaza06"}   # ICJ 잠정조치 / ICC 영장신청
smap["kind"] = smap["event_id"].apply(lambda e: "법적(ICJ/ICC)" if e in LEGAL else "상징/군사")

# 소스별 × 사건유형별 침묵률 (성명이 0건이면 침묵)
rec = []
for s in order:
    for kind in ["법적(ICJ/ICC)","상징/군사"]:
        sub = smap[smap["kind"]==kind]
        silent = (sub[s]==0).sum()
        rec.append({"source":SRC_KO[s], "kind":kind,
                    "침묵사건수":int(silent), "전체사건수":len(sub),
                    "침묵률":round(silent/len(sub),2)})
sil = pd.DataFrame(rec)
sil.pivot(index="source", columns="kind", values="침묵률")'''),
md("""> **읽기.** 한국은 **법적 사건(ICJ)** 에서 침묵률이 두드러진다 — 우크라이나에서
> ICC 영장·댐 파괴 같은 법적·기술적 변곡점에 침묵한 것과 **같은 결**이다.
> *법적 판단을 요구하는 사건에서 한국 외교부는 입장 표명을 미룬다* 는 가설이
> 두 주제에서 반복 관측된다. (단정 아님 — 사건 수가 적다. 가설로 남기고 기록한다.)"""),
code(r'''# 침묵 패턴 막대 — 사건유형별 소스 침묵률
import plotly.express as px
fig_sil = px.bar(sil, x="source", y="침묵률", color="kind", barmode="group",
    color_discrete_map={"법적(ICJ/ICC)":"#6a51a3","상징/군사":"#bdbdbd"},
    labels={"source":"소스","침묵률":"침묵률 (성명 0건 비율)","kind":"사건 유형"},
    title="가자 — 사건 유형별 소스 침묵률 (법적 vs 상징/군사)")
fig_sil.update_layout(template="plotly_white", height=420)
fig_sil.show()'''),

md("""## Step 4 — Visual Essay 산출물: 한 장으로 말한다 🎨

> **저널리즘/영상 앵글.** 분석의 끝은 표가 아니라 **한 장의 그림**이다.
> 독자는 std를 모른다. 우리가 *번역*해 줘야 한다. 발표·기사에 바로 쓸
> **잘 다듬어진 Plotly 그림 한 장**을 만들고, 일반 독자용 캡션을 단다.

핵심 메시지 한 줄: **"중국은 어떤 사건에도 같은 톤(상호성)으로 말하고, 한국은 사건마다 톤을 바꾼다."**"""),
code(r'''# 폴리시드 시계열: 중국(가장 일관) vs 한국(가장 유연) 두 선을 강조, 나머지는 흐리게
fig = go.Figure()
for s in order:
    sub = ts[ts["source"]==s].sort_values("date")
    highlight = s in ("CN","KR")
    fig.add_trace(go.Scatter(
        x=sub["date"], y=sub["mutuality_index"],
        mode="lines+markers", name=SRC_KO[s],
        line=dict(color=SRC_COLOR[s], width=3.5 if highlight else 1.2,
                  dash=None if highlight else "dot"),
        opacity=1.0 if highlight else 0.45,
        marker=dict(size=8 if highlight else 5),
    ))

# 주석: 중국=평평(일관), 한국=출렁(유연)
cn = ts[ts["source"]=="CN"].sort_values("date")
kr = ts[ts["source"]=="KR"].sort_values("date")
fig.add_annotation(x=cn["date"].iloc[-1], y=cn["mutuality_index"].iloc[-1],
    text="중국: 사건이 바뀌어도<br>같은 '균형' 톤 유지", showarrow=True, arrowhead=2,
    ax=-60, ay=-40, font=dict(color="#F58518", size=12))
fig.add_annotation(x=kr["date"].iloc[kr["mutuality_index"].values.argmax()],
    y=kr["mutuality_index"].max(),
    text="한국: 사건마다<br>톤이 출렁", showarrow=True, arrowhead=2,
    ax=40, ay=-40, font=dict(color="#E45756", size=12))

fig.update_layout(
    title=dict(text="<b>같은 전쟁, 다른 일관성</b><br>"
                    "<span style='font-size:13px;color:gray'>"
                    "가자 사건 흐름 속 각국 외교부의 '균형' 화법 (2023.10–2025.08)</span>"),
    xaxis_title="사건 발생일", yaxis_title="상호성 지수 (양면적 표현 밀도)",
    template="plotly_white", height=520,
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
)
fig.show()'''),
md("""### 📝 내러티브 캡션 (일반 독자용 · 기사/영상 자막)

> **2023년 10월부터 2025년 8월까지, 가자에서 벌어진 열 개의 변곡점을 지나는 동안
> 중국 외교부의 화법은 거의 움직이지 않았다.** 공격이든 휴전이든 국제재판소 결정이든,
> 중국은 한결같이 "모든 당사자", "대화", "정치적 해결" 이라는 *균형의 언어*를 반복했다.
> **반대로 한국의 화법은 사건마다 크게 출렁였다** — 어떤 날엔 단호했고, 어떤 날엔 아예
> 침묵했다. 같은 자(尺)로 재면, **'무엇을 말하느냐'보다 '얼마나 한결같으냐'가 그 나라의
> 외교적 입지를 더 정직하게 드러낸다.**

위 그림과 이 4문장이 오늘의 **산출물**이다. 표가 아니라 *이야기*로 끝낸다."""),

md("""## Step 5 — Q1/Q2/Q3 가자 결론 + 데이터셋 저장 💾

세 개의 큰 질문에 대한 **가자**의 답을 정리하고, 6차원 결과를 CSV로 남긴다."""),
code(r'''# 소스별 최종 요약표
final_cols = ["directness_index","verb_strength_max","verb_density",
              "mutuality_index","hedging_density","subject_first_person"]
final = ana.groupby("source")[final_cols].mean().round(3).reindex(order)
final["상호성_std(시간)"] = consistency
final.index = [SRC_KO[s] for s in order]
print("== 가자 — 소스별 6차원 + 시간 일관성 ==")
final'''),
code(r'''# TODO: 가자 주석 데이터셋을 CSV로 저장하라. 힌트: ana[keep].to_csv(경로, ...)
keep = ["id","source","event_id","date","directness_index","verb_strength_max",
        "verb_strength_mean","verb_density","mutuality_index","hedging_density",
        "subject_first_person","subject_all_parties","subject_national","n_words"]
out = os.path.join(PROJECT,"data","gaza_annotated.csv")
ana[keep].to_csv(out, index=False, encoding="________")   # ← 빈칸: 한글 깨짐 방지 인코딩
print("저장 시도:", out)'''),
code(r'''# CHECK Step5
try:
    chk = pd.read_csv(os.path.join(PROJECT,"data","gaza_annotated.csv"))
    assert len(chk) == 77 and "verb_density" in chk.columns
    print("✅ PASS — data/gaza_annotated.csv 저장 완료 (", len(chk), "행 )")
except Exception as e:
    print("❌ FAIL —", e, '\n힌트: 인코딩 빈칸은 "utf-8-sig"')'''),
md("""<details><summary>💡 힌트 / 정답</summary>

```python
ana[keep].to_csv(out, index=False, encoding="utf-8-sig")
```
`utf-8-sig` 는 BOM을 붙여 엑셀에서 한글이 깨지지 않게 한다.
</details>"""),
md("""### 📌 Q1·Q2·Q3 — 가자 결론

> **Q1 (소스별 차이):** 가자에서도 네 소스는 뚜렷이 다르게 말한다. **중국**의 상호성(≈11.2)은
> 프랑스(≈1.5)의 7배. **한국**은 가장 직설적(0.89)이고 동사밀도가 높다(짧고 단호). **UN**은
> 길고 절차적, **프랑스**는 짧고 사무적. 우크라이나와 **같은 지문 구조**가 반복된다.
>
> **Q2 (당사자성):** **중국**은 두 주제 모두 상호성 1위 — *주제 무관 일관된 제3자 중립 프레임*.
> 당사자성이 약하다. 반면 **한국**은 법적 사건(ICJ)에 두 주제 모두 침묵 — 자국 이해/신중함이
> 침묵으로 드러나는 *유연한* 행위자. 당사자성의 결이 다르다.
>
> **Q3 (일관성 vs 유연성):** 시간 축에서 **상호성은 UN이 가장 일관(std 최저)**, **한국이 가장
> 유연(std 최고)**. **동사강도 밀도는 중국이 가장 일관**. 차원에 따라 '한결같은 자'가 바뀌지만,
> **한국은 어느 차원에서나 가장 출렁이는 소스**다."""),

md("""## 🎯 회고 (5분)

1. "일관성"은 미덕인가 한계인가? 중국의 한결같음은 *원칙*일까 *회피*일까?
2. 한국의 '유연함'은 *상황 적응*일까 *입장 부재*일까? 숫자만으로 단정할 수 있나?
3. 시계열에서 가장 *놀라운* 한 점(날짜)을 골라, 그날 무슨 일이 있었는지 원문을 열어 보라.

## ▶️ 다음 (과제 — 주제3: AI 거버넌스, 혼자 처음부터 끝까지)
> "이제 도구도 있고(`diplo_analysis`), 방법도 안다(수집→분석→검증→시계열→Visual Essay).
> **세 번째 주제는 혼자, 처음부터 끝까지** 해본다 — 정답지는 제공한다.
> 단, 미리 일러둔다: **4개 소스 중 하나는 이 주제에서 *구조적으로 침묵*한다.**
> 누구일지, 가서 침묵 지도로 직접 확인하라. 그게 첫 발견이 될 것이다.**"""),
]

save(cells, "session6/session6.ipynb")
