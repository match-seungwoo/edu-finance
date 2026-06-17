# 외교 언어 분석 프로젝트 — 학생 프로젝트·학습 정리 (지원서용)

> 대상: 외교·국제관계·데이터/언어학·저널리즘 방향 지원 학생
> 용도: Resume의 Projects / Application의 Activities / Personal Statement 소재
> 근거: program4 — 6세션 강의·실습 노트북(ipynb), 실제 수집 코퍼스, 분석 산출물

---

## 0. 프로젝트 한 줄 정의

**"Quantifying Cultural Codes in Diplomatic Language"**
UN·한국·중국·프랑스 4개 소스가 우크라이나·가자·AI 거버넌스 세 사건군에 대해 발표한
**공식 외교 성명문 354건을 직접 스크래핑·정제**하고, 9개 정량 차원(직설성·동사강도·주어패턴·상호성·완곡어·침묵지도·완곡명명·귀속·대상별태도)으로
분석해 "같은 사건, 다른 언어"를 데이터로 입증한 엔드투엔드 데이터 저널리즘 프로젝트.

- **기술 스택**: Python, requests/BeautifulSoup(스크래핑), spaCy(구문 분석), Anthropic Claude API(의미 분석), pandas, Plotly, Internet Archive 복구
- **데이터**: 30개 사건 × 4개 소스, 실제 수집 raw 371건 → 정제 354건, 30/30 사건 커버
- **방법론**: Hybrid — "계산은 코드, 해석은 LLM, 판단은 인간"

---

## 1. 세세한 버전 (Detailed Version)

### 데이터 파이프라인 구축 (수집 → 정제)
- 4개 정부/국제기구 사이트(press.un.org, mofa.go.kr, fmprc.gov.cn, diplomatie.gouv.fr)를 **각기 다른 구조에 맞춰 스크래핑**. 봇 차단·인코딩(GB2312)·세션쿠키·페이지네이션 한계 등 실제 엔지니어링 문제를 해결.
- 라이브 스크래핑이 막힌 과거 데이터는 **Internet Archive raw 스냅샷**으로 복구.
- **재현성 설계**: 라이브 수집 + JSON/CSV 백업 폴백 구조, 정제 규칙을 코드로 공개.
- **정제 판단**: 중국 외교부 '일일 정례 브리핑'(1만 8천 자, 다주제 혼재)에서 주제 관련 문단만 추출 — "무엇을 버릴지가 분석의 시작"이라는 데이터 윤리를 체득.

### 분석 프레임워크 설계·구현 (외교 도메인 지식 투입)
- 외교 언어의 무게를 아는 사람만 떠올릴 수 있는 6개 차원을 설계·구현. 예: 동사 강도 사다리(note→condemn→demand), 상호성 지수(중국 외교 언어의 특징).
- spaCy로 능동/수동·주어·동사를 자동 추출, Claude API로 framing·미묘한 hedging을 의미 분석, 둘을 **교차검증**.

### 비판적 검증 (이 프로젝트의 차별점)
- **측정 타당성 자체를 의심**: "동사 강도 최댓값"이 문서 길이와 상관(r≈0.93)됨을 발견 → "중국이 가장 강경"이 측정 착시였음을 규명, 1000단어당 밀도로 정규화하니 순위가 뒤집혀 중국이 최하로 내려감.
- **교차언어 검증**: 한·중·프 3개 언어 능력으로 자동 분석 결과를 원문 대조(ground truth).

### 발견 (요지)
- 중국 외교언어의 양면성(상호성 지수 압도적 1위)이 실데이터로 재현.
- 한국의 선택적 침묵(법적·기술적 변곡점엔 침묵, 상징적 사건엔 발언).
- 시계열 분석: UN 가장 일관 / 한국 가장 유연.
- 외교 당사자성이 낮은 AI 거버넌스에서 협력적 언어 증가 → "당사자성-언어강도" 가설 지지.

**산출물**: 주석 데이터셋(CSV), 소스별 6차원 비교표, 인터랙티브 Plotly 시각화, 일반 독자용 Visual Essay 도식·서사.

---

## 2. 영문 지원서용 문구 (Application-Ready)

### Resume — Projects
**Quantifying Cultural Codes in Diplomatic Language** | *Python, spaCy, Claude API, web scraping* | 2026
- Scraped and cleaned **195 official diplomatic statements** from four government/IGO sources (UN, Korea, China, France) on 30 geopolitical events, with reproducible live-scrape + backup pipelines and Internet Archive recovery
- Designed a **six-dimension quantitative framework** (directness, verb-strength ladder, subject pattern, mutuality, hedging, silence map) grounded in diplomatic domain knowledge, combining spaCy syntactic parsing with Claude-based semantic analysis
- Exposed a **measurement-validity flaw** — verb-strength max correlated with document length (r≈0.93); after density normalization the source ranking reversed (China fell to the bottom) — and validated automated results against Korean/Chinese/French source texts
- Found and documented cross-source patterns (China's distinctively high mutuality language; Korea's selective silence on legal milestones; stake-dependent language intensity)

### Common App — Activities (150자)
`Built a Python pipeline scraping 195 diplomatic statements (UN/Korea/China/France); quantified cross-cultural language differences with spaCy + Claude; validated with trilingual source-checking.`

### UC / 자유 양식 (약 350자)
> I built a system that measures how the UN, Korea, China, and France use *different words for the same war*. After scraping and cleaning 195 official statements, I quantified six dimensions of diplomatic language—from the verbs they choose (note vs. condemn) to the silences they keep. The turning point was discovering that my own metric was wrong: "China sounds toughest" turned out to be an artifact of document length, and the ranking reversed once I normalized it. Using my Korean, Chinese, and French, I checked the machine's readings against the original texts. The project taught me that in both diplomacy and data, the words you don't verify are the ones that mislead you.

### Personal Statement 소재 (앵글)
- **A. "검증하는 습관"**: 자기 지표의 길이 편향을 스스로 발견·교정 → 숫자를 의심하는 지적 성실성.
- **B. "번역가의 정체성"**: 한중프 3개 언어로 AI 분석의 ground truth를 검증 → 문화 간 번역자.
- **C. "침묵을 읽기"**: 외교에서 말하지 않은 것을 데이터로 포착 → 도메인 직관 + 정량 방법의 결합.

---

## 3. 핵심 키워드

| 분류 | 키워드 |
|---|---|
| 프로그래밍 | Python, requests, BeautifulSoup, pandas, Plotly |
| NLP/AI | spaCy(구문 분석), Anthropic Claude API, 프롬프트 엔지니어링, hybrid 방법론 |
| 데이터 | 웹 스크래핑, 데이터 정제, 재현성, 백업 폴백, Internet Archive 복구 |
| 분석 | 정량 텍스트 분석, 측정 타당성, 상관/정규화, 시계열 분산, 교차언어 검증 |
| 도메인 | 외교 언어, framing, 외교 당사자성, 침묵의 신호 |

---

## 4. 작성 시 유의 (정직성 체크)

1. **"수강 과정 내 가이드된 프로젝트"** — "독자 연구"로 과장 금지. "built / designed / implemented (within a structured course)" 권장. 단, 측정 편향을 스스로 잡아낸 검증 과정은 진짜 능동성의 증거이므로 강조해도 좋다.
2. **수치는 실제 노트북 출력 기준** — 상호성 CN 11.4, 길이 상관 r≈0.93, 정규화 후 중국 최하 등은 실제 산출물에 존재. 인터뷰에서 설명할 수 있어야 한다.
3. **표본 한계 명시** — AI 거버넌스 n=50, 프랑스 AI=0 등. "경향"으로 진술, 과일반화 금지.
4. **정치적 중립** — 특정 국가 비판이 아니라 *언어 패턴의 정량 기술*임을 분명히. 결론은 측정에 근거.
