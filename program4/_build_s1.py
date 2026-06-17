# -*- coding: utf-8 -*-
"""session1.ipynb 빌더 — 데이터 수집·정제 (주제1: 우크라이나)"""
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
md("""# Session 1 — 외교 성명문, 데이터부터 손에 쥐기
### 주제 1: 우크라이나 전쟁 · 수집과 정제

> **오늘 한 문장:** "같은 전쟁을 두고 UN·한국·중국·프랑스는 *서로 다른 단어*로 말한다.
> 그 차이를 숫자로 잡아내는 게 이 프로젝트다. 오늘은 그 **원재료(성명문)** 를 손에 쥔다."

이 프로젝트는 세 개의 사건군 — **우크라이나 전쟁, 가자 분쟁, AI 거버넌스** — 에 대한
네 개 소스(UN / 한국 외교부 / 중국 외교부 / France Diplomatie)의 공식 성명문을
**9개 분석 차원**으로 정량 분석한다. 우리는 이미 **4개 소스를 실제로 스크래핑해 195건을 수집**해 두었다.
오늘 세션의 목표:

1. **원천데이터가 진짜 존재하는지** 두 눈으로 확인한다 (분석의 첫 번째 윤리).
2. 데이터를 불러와 **구조(스키마)** 를 이해한다.
3. 공개 데이터의 **현실(지저분함)** 을 보고, 무엇을 버릴지 정한다 = **정제**.
4. 우크라이나 작업 데이터셋을 만들고, **침묵 지도**를 처음 그린다.

> 💡 **이번 과정 운영 방식:** 셀을 위에서 아래로 하나씩 실행한다.
> `# TODO` 가 보이면 직접 채우고, 바로 아래 `# CHECK` 셀을 실행해 `✅` 가 떠야 다음으로."""),

md("""## 🗺️ 프로젝트 전체 지도 — 9개 분석 차원

같은 사건을 두고 네 소스가 *서로 다른 단어*로 말한다. 그 차이를 우리는 **9개 차원**으로 잰다.
**핵심 6 + 확장 3** 구조다(툴킷 `diplo_analysis.py` 와 1:1 대응).

**핵심 6개 차원**

| # | 차원 | 한 줄 뜻 | 도구 |
|---|---|---|---|
| 1 | **Directness 직설성** | 능동/수동 + 우회표현 (`Russia attacked` vs `civilians were attacked`) | spaCy |
| 2 | **Verb Strength 동사강도** | note(1)…condemn(6)…demand(7) 사다리 | spaCy lemma |
| 3 | **Subject Pattern 주어패턴** | 누가 주어로 등장하나 (우리/국가/국제사회/모든 당사자…) | spaCy |
| 4 | **Mutuality 상호성** | 양면적 표현 밀도 ("both sides", "all parties") | 사전 |
| 5 | **Hedging 완곡어** | 유보·완곡 표현 밀도 ("may", "appears to") | 사전 |
| 6 | **Silence Map 침묵지도** | 누가 어떤 사건에 *말하지 않았나* | 커버리지 |

**확장 3개 차원 (v2)**

| # | 차원 | 한 줄 뜻 | 도구 |
|---|---|---|---|
| 7 | **Event Naming 완곡명명** | 사건을 뭐라 부르나 (`invasion` vs `situation`) | 다국어 사전 |
| 8 | **Blame Attribution 귀속** | 누구를 가해자로 *지목*했나 (행위자 명시 vs 가림) | 의존구문 SVO |
| 9 | **Targeted Sentiment 대상별 태도** | 행위자별 감정 비대칭 (러시아엔 부정, 우크라이나엔 긍정?) | 다국어 사전 |

**어느 세션에서 무엇을 배우나**

| 세션 | 새로 배우는 차원 |
|---|---|
| s1 (오늘) | 데이터 + **6번 침묵지도**의 원재료 |
| s2 | 1·2·3(직설성·동사강도·주어) + **8번 귀속(Blame Attribution)** |
| s3 | 4·5(상호성·완곡어, **부정처리** 포함) + **9번 대상별 태도** |
| s4 | 검증·시각화 + **7번 완곡명명(원어 검증)** |
| s5~6 | 가자에 9개 차원 전체 재적용 + 시계열 |

> 💡 오늘은 **6번 침묵지도**의 원재료만 손에 쥔다. 나머지 8개 차원은 위 표의 순서로 하나씩 만든다."""),

md("## Step 0 — 환경 설정\n필요한 라이브러리를 설치하고, 프로젝트 폴더를 찾는다."),
code('!pip install spacy plotly -q\n!python -m spacy download en_core_web_sm -q'),
code(SETUP),

md("""## Step 1 — 원천데이터 존재여부 확인 🔍

> **왜 이걸 먼저 하나:** 분석가가 가장 많이 하는 실수는 "데이터가 있겠지" 하고
> 분석부터 짜는 것이다. 파일이 없거나, 비었거나, 깨졌으면 그 위의 모든 분석은 거짓말이 된다.
> **존재 → 개수 → 내용**, 이 세 가지를 눈으로 본 뒤에만 다음으로 간다."""),
code(r'''# 백업 코퍼스 파일들이 실제로 있는지 확인
import os
backup = os.path.join(PROJECT, "data", "backup")
need = ["corpus_clean.json", "corpus_clean.csv", "coverage_clean.csv", "manifest.json"]
print("📁", backup, "\n")
for f in need:
    p = os.path.join(backup, f)
    ok = os.path.exists(p)
    size = os.path.getsize(p) if ok else 0
    print(f"  {'✅' if ok else '❌'} {f:22s} {size:>10,} bytes")'''),
code(r'''# 수집 요약(manifest) 읽기 — 무엇을, 몇 개나 모았나
import json
manifest = json.load(open(os.path.join(backup, "manifest.json"), encoding="utf-8"))
print("총 문서 수 :", manifest["total_docs"])
print("커버한 사건:", manifest["events_covered"], "/", manifest["events_total"])
print("소스별     :", manifest["by_source"])
print("주제별     :", manifest["by_topic"])'''),
code(r'''# CHECK Step1 — 데이터가 실제로 존재하고 비어있지 않은지
try:
    assert manifest["total_docs"] > 100, "문서가 너무 적다"
    assert all(os.path.exists(os.path.join(backup, f)) for f in need), "백업 파일 누락"
    print("✅ PASS — 원천데이터 3종 코퍼스가 모두 존재한다. 분석을 시작해도 좋다.")
except AssertionError as e:
    print("❌ FAIL —", e)'''),

md("""## Step 2 — 데이터 로드

`corpus_clean.json` 은 문서 한 건이 딕셔너리 하나인 **리스트**다.
pandas의 `DataFrame` 으로 올리면 표처럼 다룰 수 있다."""),
code(r'''import pandas as pd
docs = json.load(open(os.path.join(backup, "corpus_clean.json"), encoding="utf-8"))
df = pd.DataFrame(docs)
print("행/열:", df.shape)
df.head(3)'''),
md("""**스키마(컬럼) 설명**

| 컬럼 | 뜻 |
|---|---|
| `source` | UN / KR(한국) / CN(중국) / FR(프랑스) |
| `topic` | ukraine / gaza / ai_governance |
| `event_id`, `event_name` | 어떤 사건에 대한 성명인가 |
| `date` | 발표일 |
| `title`, `url` | 제목과 원문 링크 (검증 때 클릭해서 확인) |
| `text` | 성명 본문 (분석 대상) |
| `collected_via` | live_scrape = 실제로 우리가 긁어옴 |"""),
code(r'''# TODO: source 컬럼의 값별 개수를 세어보자 (힌트: value_counts)
counts = df["source"]._____()   # ← 빈칸을 채워라
print(counts)'''),
code(r'''# CHECK Step2
try:
    counts = df["source"].value_counts()
    assert set(counts.index) >= {"UN","KR","CN","FR"}, "소스 4종이 안 보인다"
    print("✅ PASS\n", counts.to_dict())
except Exception as e:
    print("❌ FAIL —", e, "\n힌트: df['source'].value_counts()")'''),
md("""<details><summary>💡 힌트 / 정답</summary>

```python
counts = df["source"].value_counts()
```
`value_counts()` 는 각 값이 몇 번 나오는지 세어 큰 순서로 돌려준다.
</details>"""),

md("""## Step 3 — 공개 데이터의 현실: 왜 '정제'가 필요한가

우리는 이미 한 번 정제했다(`corpus_clean`). 무엇을 왜 버렸는지 보자.
**중국 외교부**는 사건마다 따로 성명을 내지 않고 **매일 정례 브리핑** 한 번에
우크라이나·가자·양자관계·기자 질문을 다 답한다. 그래서 원본(raw) 문서 하나가
1만 8천 자가 넘고 여러 주제가 섞여 있다."""),
code(r'''# raw 와 clean 의 평균 글자수 비교
raw = json.load(open(os.path.join(backup, "corpus.json"), encoding="utf-8"))
clean = docs
def avglen(data, src):
    L = [len(d["text"]) for d in data if d["source"]==src]
    return sum(L)//len(L) if L else 0
print(f"{'source':8}{'raw 평균자수':>14}{'clean 평균자수':>16}")
for s in ["UN","KR","CN","FR"]:
    print(f"{s:8}{avglen(raw,s):>14,}{avglen(clean,s):>16,}")
print(f"\nraw 총 {len(raw)}건 → clean {len(clean)}건 (주제 키워드 없는 노이즈 제거 + 중국 브리핑에서 주제 문단만 추출)")'''),
md("""> **정제 규칙 (scrapers/clean_corpus.py 에 구현)**
> 1. 본문에 주제 키워드(ukraine/russia 등)가 **단 한 번도 없으면** → 잘못 걸린 문서, 제거.
> 2. 6,000자 넘는 문서(주로 중국 브리핑)는 → **주제 관련 문단 + 바로 앞 질문**만 추출.
>
> 데이터 분석은 "무엇을 남기고 무엇을 버릴지"를 정하는 데서 시작한다.
> 이 결정은 **기록하고 공개**해야 한다(재현성). 그래서 정제 코드를 레포에 같이 둔다."""),

md("""## Step 4 — 오늘의 주제: 우크라이나만 골라내기

이번 주제(s1~s4)는 우크라이나다. `topic == "ukraine"` 인 행만 추린다."""),
code(r'''# TODO: ukraine 행만 골라 ukr 변수에 담아라 (힌트: df[df["..."] == "..."])
ukr = df[df["topic"] == "_______"].copy()
print("우크라이나 문서:", len(ukr), "건")
ukr.groupby("source").size()'''),
code(r'''# CHECK Step4
try:
    assert len(ukr) > 50 and set(ukr["topic"].unique()) == {"ukraine"}, "필터가 잘못됐다"
    print("✅ PASS — 우크라이나", len(ukr), "건 확보")
except Exception as e:
    print("❌ FAIL —", e, '\n힌트: df[df["topic"] == "ukraine"]')'''),

md("""## Step 5 — 침묵 지도 첫 등장 🤫

외교에서 **말하지 않는 것**은 말하는 것만큼 중요한 신호다.
어떤 사건에 어느 소스가 성명을 **안 냈는지**를 표로 만든다.
이게 분석 차원 6번 **Silence Map**의 원재료다."""),
code(r'''# 사건 × 소스 문서 수 매트릭스 (이미 만들어 둔 coverage_clean.csv)
cov = pd.read_csv(os.path.join(backup, "coverage_clean.csv"))
cov_ukr = cov[cov["topic"]=="ukraine"][["event_id","event_name","date","UN","KR","CN","FR","total"]]
cov_ukr'''),
code(r'''# 어느 사건에서 누가 침묵했나? (0 = 침묵)
for _, r in cov_ukr.iterrows():
    silent = [s for s in ["UN","KR","CN","FR"] if r[s]==0]
    if silent:
        print(f'  {r["event_id"]} {r["event_name"][:38]:40s} 침묵: {", ".join(silent)}')'''),
md("""**여기서 벌써 패턴이 보인다.** 예컨대 한국은 ICC 영장·댐 파괴·에너지 시설 공격
같은 **법적·기술적 변곡점**에는 자주 침묵하고, 침공·1주년 같은 **상징적 사건**엔 말한다.
이건 4주차(s4) 검증에서 다시 깊게 본다. 오늘은 "침묵도 데이터다"만 기억하자."""),

md("## Step 6 — 작업 데이터 저장\n다음 세션(구조 분석)에서 바로 쓰도록 우크라이나 데이터셋을 저장한다."),
code(r'''ukr.to_json(os.path.join(PROJECT, "data", "ukraine_working.json"),
            orient="records", force_ascii=False, indent=1)
print("✅ 저장: data/ukraine_working.json  (", len(ukr), "건 )")
print("다음 세션(Session 2)에서 이 파일을 spaCy로 구문 분석한다.")'''),

md("""## 🎯 회고 (5분)

1. 4개 소스 중 **글이 가장 긴/짧은** 소스는? 그게 분석에 어떤 함정을 만들까?
2. 우크라이나 사건 중 **4개 소스가 모두 말한** 사건과 **누군가 침묵한** 사건의 차이는?
3. 우리가 중국 데이터에서 문단을 잘라낸 것은 정당한가? 무엇을 잃었을 수 있나?

## ▶️ 다음 (Session 2)
> "오늘은 *누가 말했나*를 봤다. 다음엔 *어떻게 말했나* —
> **능동태로 'Russia attacked'라 쓰는가, 수동태로 'civilians were attacked'라 쓰는가**를
> spaCy로 자동 측정한다. **Directness Index(직설성)** 의 탄생."""),
]

save(cells, "session1/session1.ipynb")
