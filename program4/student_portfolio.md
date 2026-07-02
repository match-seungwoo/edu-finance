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

- **기술 스택**: Python, requests/BeautifulSoup(스크래핑), spaCy(구문 분석·의존구문 SVO), Anthropic Claude API(의미 분석), pandas, Plotly, SciPy(통계 검정), Internet Archive 복구
- **데이터**: 30개 사건 × 4개 소스, 실제 수집 raw 371건 → 정제 354건, 30/30 사건 커버(소스별 UN 92·한국 45·중국 120·프랑스 97)
- **방법론**: Hybrid — "계산은 코드, 해석은 LLM(Claude), 판단은 인간"
- **핵심 결과의 통계적 견고성**: 앵커 발견(중국 상호성 1위)이 Cohen's d=2.48, Mann-Whitney p≈10⁻³⁰ 로 유의 (단일 지표 우연 아님)

---

## 1. 세세한 버전 (Detailed Version)

### 데이터 파이프라인 구축 (수집 → 정제)
- 4개 정부/국제기구 사이트(press.un.org, mofa.go.kr, fmprc.gov.cn, diplomatie.gouv.fr)를 **각기 다른 구조에 맞춰 스크래핑**. 봇 차단·인코딩(GB2312)·세션쿠키·페이지네이션 한계 등 실제 엔지니어링 문제를 해결.
- 라이브 스크래핑이 막힌 과거 데이터는 **Internet Archive raw 스냅샷**으로 복구.
- **재현성 설계**: 라이브 수집 + JSON/CSV 백업 폴백 구조, 정제 규칙을 코드로 공개.
- **정제 판단**: 중국 외교부 '일일 정례 브리핑'(1만 8천 자, 다주제 혼재)에서 주제 관련 문단만 추출 — "무엇을 버릴지가 분석의 시작"이라는 데이터 윤리를 체득.

### 분석 프레임워크 설계·구현 (외교 도메인 지식 투입)
- 외교 언어의 무게를 아는 사람만 떠올릴 수 있는 **핵심 6차원**을 설계·구현: 직설성 · 동사 강도 사다리(note→condemn→demand) · 주어 패턴 · 상호성 지수(중국 외교 언어의 특징) · 완곡어 밀도 · 침묵 지도.
- 6차원의 구조적 약점(bag-of-words·영문 단일언어·귀속 부재)을 스스로 진단하고 **확장 3차원(v2)** 을 신설: **완곡명명**(invasion vs conflict) · **귀속**(가해자를 명시했나) · **대상별 태도**(한 성명 안 행위자별 감정 비대칭).
- **NLP 기법 강화(v2)**: 부정·범위 처리(negation scope — "no mutual interest" 오탐 제거) · 의존구문 **SVO 추출 + 경량 coreference**(직설성·귀속을 "누가-무엇을" 그래프로) · 다국어 사전(en·ko·zh·fr)으로 원어 분석 모듈 구현.
- spaCy로 능동/수동·주어·동사·SVO를 자동 추출, Claude API로 framing·미묘한 hedging을 의미 분석, 둘을 **교차검증**.

### 비판적 검증 (이 프로젝트의 차별점)
- **측정 타당성 자체를 의심**: "동사 강도 최댓값"이 문서 길이와 상관(r≈0.9)됨을 발견 → "중국이 가장 강경"이 측정 착시였음을 규명, 1000단어당 밀도로 정규화하니 순위가 뒤집혀 중국이 최하로 내려감.
- **구성타당도(construct validity) 점검**: 빈출어 `ceasefire`(124건)가 '분쟁 이벤트어'라 상호성 구성을 흐린다는 것을 데이터로 확인하고 사전에서 *의도적으로 제외* — "사전 선택이 결과를 좌우한다"는 방법론적 자각.
- **강건성 검증**: 정제 절단 임계값(`LONG_DOC`)이 결과를 왜곡하는지 전체본 vs 잘림본을 직접 비교(상호성 차이 ~3%) → "풍성함의 레버는 절단이 아니라 문서 수"라는 통찰로 코퍼스를 183→354건으로 확대.
- **통계적 견고성**: 핵심 발견에 효과크기(Cohen's d=2.48)·유의성(Mann-Whitney p≈10⁻³⁰)을 붙이고, 세 독립 차원(상호성·완곡명명·대상별 태도)의 합의(triangulation)로 우연 아님을 입증.
- **교차언어 검증**: 한·중·프 3개 언어 능력으로 자동 분석 결과를 원문 대조(ground truth).

### 발견 (요지)
- **중국 외교언어의 양면성** — 상호성 지수 압도적 1위(우크+가자 CN 11.90 ≫ KR 8.81 > UN 3.30 > FR 1.62)가 실데이터로 재현. 완곡명명(중국이 가장 완곡)·귀속(가해자를 가장 많이 가림, 0.30)·대상별 태도(네 행위자를 가장 고르게 비판)까지 **세 독립 차원이 같은 방향**.
- **한국의 선택적 침묵** — ICC 영장·ICJ 명령 등 법적·기술적 변곡점엔 침묵, 침공·1주년 등 상징적 사건엔 발언.
- **귀속 순위** — 프랑스 0.43(가해자를 가장 직접 지목) > UN 0.38 > 중국 0.30 > 한국(공격을 서술 안 해 0건).
- **시계열(Q3)** — 중국·프랑스가 가장 일관(중국 동사강도 분산 1.40, "all parties" 교리 불변) / 한국이 가장 유연(사건마다 언어 크게 조절).
- **당사자성 가설(Q2) 지지** — 저당사자성 AI 거버넌스에서 협력 언어 최고(상호성 8.15 vs 전쟁 ~6), 동사강도 최저(4.02). 전쟁용 차원인 귀속·대상별 태도가 AI에선 0건(가해자·대립당사자 부재).

**산출물**: 주석 데이터셋(CSV), 소스별 **9차원** 비교표, 통계 검정 결과, 침묵 지도 히트맵, 인터랙티브 Plotly 시각화, 일반 독자용 Visual Essay 도식·서사.

### 독립 적용 (과제 — AI 거버넌스)
- 4주간 우크라이나·가자로 함께 만든 툴킷(`diplo_analysis`)을 **새 코퍼스(AI 거버넌스)에 혼자 처음부터 끝까지** 적용 — 배운 방법론을 미지의 주제로 전이하는 능력의 증거.
- **구조적 부재 발견**: 프랑스가 AI 거버넌스에서 0건 — 우발적 누락이 아니라 프랑스 AI 정상회의 자료가 외교부 성명 트리가 아닌 엘리제궁/정상회의 전용 포털에 있는 *구조적* 부재임을 규명(침묵 지도의 발견).
- **차원 전이 판단**: 전쟁용 차원(귀속·대상별 태도)이 AI 코퍼스에서 0건인 것을 버그가 아니라 "당사자성 가설의 강한 증거"로 재해석.

---

## 2. 영문 지원서용 문구 (Application-Ready)

### Resume — Projects
**Quantifying Cultural Codes in Diplomatic Language** | *Python, spaCy, Claude API, web scraping* | 2026
- Scraped and cleaned **354 official diplomatic statements** from four government/IGO sources (UN, Korea, China, France) on 30 geopolitical events, with reproducible live-scrape + backup pipelines and Internet Archive recovery
- Designed a **nine-dimension quantitative framework** (directness, verb-strength ladder, subject pattern, mutuality, hedging, silence map, event-naming, blame-attribution, targeted-sentiment) grounded in diplomatic domain knowledge, combining spaCy dependency parsing (SVO + lightweight coreference, negation-scope handling) with Claude-based semantic analysis
- Exposed a **measurement-validity flaw** — verb-strength max correlated with document length (r≈0.9); after density normalization the source ranking reversed (China fell to the bottom) — and confirmed the anchor finding with effect size (Cohen's d=2.48) and significance (Mann-Whitney p≈10⁻³⁰)
- Validated automated results against Korean/Chinese/French source texts, and documented cross-source patterns triangulated across three independent dimensions (China's both-sided/soft language; Korea's selective silence on legal milestones; stake-dependent language intensity)

### Common App — Activities (150자)
`Built a Python pipeline scraping 354 diplomatic statements (UN/Korea/China/France); quantified 9 dimensions of cross-cultural language with spaCy + Claude; caught and fixed a length-bias flaw in my own metric; validated with trilingual source-checking.`

### UC / 자유 양식 (약 350자)
> I built a system that measures how the UN, Korea, China, and France use *different words for the same war*. After scraping and cleaning 354 official statements, I quantified nine dimensions of diplomatic language—from the verbs they choose (note vs. condemn) to the silences they keep. The turning point was discovering that my own metric was wrong: "China sounds toughest" turned out to be an artifact of document length, and the ranking reversed once I normalized it. Using my Korean, Chinese, and French, I checked the machine's readings against the original texts. The project taught me that in both diplomacy and data, the words you don't verify are the ones that mislead you.

### Personal Statement 소재 (앵글)
- **A. "검증하는 습관"**: 자기 지표의 길이 편향을 스스로 발견·교정 → 숫자를 의심하는 지적 성실성.
- **B. "번역가의 정체성"**: 한중프 3개 언어로 AI 분석의 ground truth를 검증 → 문화 간 번역자.
- **C. "침묵을 읽기"**: 외교에서 말하지 않은 것을 데이터로 포착 → 도메인 직관 + 정량 방법의 결합.

---

## 3. 핵심 키워드

| 분류 | 키워드 |
|---|---|
| 프로그래밍 | Python, requests, BeautifulSoup, pandas, Plotly, SciPy |
| NLP/AI | spaCy(의존구문 파싱·SVO·coreference), 부정범위 처리, 다국어 사전(en·ko·zh·fr), Anthropic Claude API, 프롬프트 엔지니어링, hybrid 방법론 |
| 데이터 | 웹 스크래핑, 데이터 정제, 재현성, 백업 폴백, Internet Archive 복구 |
| 분석·통계 | 정량 텍스트 분석, 측정 타당성, 구성타당도, 상관/정규화, 효과크기(Cohen's d)·비모수 검정(Mann-Whitney), 시계열 분산, 교차언어 검증, triangulation |
| 도메인 | 외교 언어, framing, 완곡명명, 귀속(attribution), 외교 당사자성, 침묵의 신호 |

---

## 4. 작성 시 유의 (정직성 체크)

1. **"수강 과정 내 가이드된 프로젝트"** — "독자 연구"로 과장 금지. "built / designed / implemented (within a structured course)" 권장. 단, 측정 편향을 스스로 잡아낸 검증 과정은 진짜 능동성의 증거이므로 강조해도 좋다.
2. **수치는 실제 노트북 출력 기준** — 상호성 CN 11.90(≫ FR 1.62), 길이 상관 r≈0.9, 정규화 후 중국 최하, Cohen's d=2.48, Mann-Whitney p≈10⁻³⁰ 등은 실제 산출물에 존재. 인터뷰에서 설명할 수 있어야 한다(→ `interview_qna.md` 105문항 참고).
3. **표본 한계 명시** — AI 거버넌스 n=50, 프랑스 AI=0, 한국 가자 소표본 등. 작은 표본 구간은 "경향·가설"로만 진술, 과일반화 금지.
4. **정치적 중립** — 특정 국가 비판이 아니라 *언어 패턴의 정량 기술*임을 분명히. "중국=양면성"도 가치 판단이 아니라 상호성 지수라는 측정 결과. 결론은 측정에 근거.
5. **시계열 발견은 정식 답변(`conclusion.md` Q3) 기준** — "중국·프랑스 가장 일관 / 한국 가장 유연"으로 진술(초기 초안의 "UN 가장 일관"은 폐기된 수치).
