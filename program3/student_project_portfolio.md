# AI Quant-Mate 과정 — 학생 프로젝트·학습 정리 (편입 지원용)

> 대상: 편입 준비 중인 대학생
> 용도: Resume의 Projects 항목 / Application의 Extracurricular Activities / Personal Statement 소재
> 근거 자료: week1~week4 강의(html) 및 실습 노트북(ipynb), 진단평가, Q&A 기록

---

## 0. 프로젝트 한 줄 정의

**"AI-Assisted Quantitative Investment Analysis System"**
한국 주식시장(KRX) 실데이터를 수집·분석·저장하고, 기술적 분석과 리스크 측정을 수행한 뒤, LLM(GPT-4o Vision, Anthropic Function Calling)을 분석 파이프라인에 통합한 엔드투엔드 퀀트 분석 시스템을 Python으로 직접 구축한 프로젝트.

- **기간**: 8주 과정 중 4주(8세션) 완료 시점 기준 — Phase 1 "개인 퀀트 시스템 구축" 완결
- **기술 스택**: Python, pandas, NumPy, SciPy, SQLite(SQL), Plotly, matplotlib, pykrx API, OpenAI API(GPT-4o Vision), Anthropic API(Function Calling)
- **데이터**: KRX 상장 5개 종목(삼성전자, SK하이닉스, 한미반도체, NAVER, LG화학) 약 1년치(244 거래일) OHLCV 실시세 + KOSPI 지수

---

## 1. 세세한 버전 (Detailed Version)

### Week 1 — 데이터 수집과 AI 차트 분석 파이프라인

**학습한 내용**
- Python 기초(변수, 함수, 라이브러리 import)와 Google Colab 환경
- 금융 시계열 데이터 구조(OHLCV), 이동평균선(MA5/MA20/MA60), 골든크로스·데드크로스·정배열 등 기술적 분석 개념
- 멀티모달 AI(Vision API)에 차트 이미지를 전달하는 프롬프트 엔지니어링(페르소나 설정, 구조화된 출력 강제, temperature 조절)

**직접 수행한 작업**
1. pykrx API로 반도체 섹터 3개 종목(삼성전자·SK하이닉스·한미반도체)의 1년치(244 거래일) OHLCV 데이터 수집
2. pandas `rolling()`으로 MA5/MA20/MA60 이동평균 계산
3. Plotly로 캔들스틱 + 3개 이동평균선 오버레이 인터랙티브 차트 구현 (`make_chart()` 함수로 모듈화)
4. 차트를 PNG로 렌더링(kaleido) → base64 인코딩 → GPT-4o Vision API에 전송하여 종목별 투자 의견(추세/핵심 시그널/매수·매도 의견/리스크 4단 구조) 자동 생성
5. 분석 결과를 종목·현재가·이동평균·1년 수익률·AI 의견 컬럼의 CSV 리포트로 집계·저장

**산출물**: 종목별 차트 PNG 3종, AI 분석 텍스트 3종, `analysis_YYYYMMDD.csv` 통합 리포트

### Week 2 — 포트폴리오 집중도 분석과 AI 피드백

**학습한 내용**
- 보유 종목 수 ≠ 분산투자: 비중(weight) 기반 포트폴리오 분석
- **허핀달-허쉬만 지수(HHI)** 로 섹터 집중도를 정량화 (HHI = Σwᵢ², 0.15/0.25 임계값으로 위험 등급 판정)
- pandas의 split-apply-combine(`groupby`) 패러다임, 벡터 연산·브로드캐스팅
- "계산은 Python, 해석은 LLM"이라는 역할 분리 설계 철학

**직접 수행한 작업**
1. 미국 기술주 5종(NVDA, AMD, TSM, AAPL, MSFT) 포트폴리오 CSV를 직접 구성
2. 평가액·비중 계산 → `groupby`로 섹터별 비중 집계 → HHI 산출(0.354 = 고위험 판정)
3. 계산된 지표를 GPT-4o에 주입해 현황/핵심 리스크/리밸런싱 제안/모니터링 포인트 4단 구조의 리포트 자동 생성
4. **Week 1 진단평가(13문항) 전 항목 통과**: 환경 설정, Python 자료형, pandas, pykrx, Plotly, Vision AI 파이프라인까지 6개 영역을 스스로 재구현하며 검증

**산출물**: 보유종목/섹터별 비중 CSV 2종, AI 리스크 평가 리포트, 진단평가 완료 노트북

### Week 3 — SQLite 데이터베이스 구축과 시계열 분석

**학습한 내용**
- CSV의 한계(덮어쓰기, 타입 손실, 검색 불가)와 파일 기반 RDBMS(SQLite)의 필요성
- SQL CRUD, JOIN(INNER/LEFT/self-join), 집계함수, 인덱싱, `EXPLAIN QUERY PLAN`
- 정규화(1NF~3NF), 복합 기본키·외래키 설계, 트랜잭션(ACID), 멱등적 적재(UPSERT), 스키마 마이그레이션, 백업 전략

**직접 수행한 작업**
1. 3-테이블 정규화 스키마 설계·구현: `tickers`(종목 식별) / `prices`(일별 시세, 복합 PK) / `ai_reviews`(AI 의견 로그, append-only)
2. pykrx 실시세 115행(5종목 × 23거래일)을 `INSERT OR REPLACE`로 멱등 적재
3. self-join으로 "7일 전 대비 수익률" 계산(한미반도체 +21.81% 등), GROUP BY로 종목별 통계 산출
4. 트랜잭션 롤백·IntegrityError 처리·`ALTER TABLE` 마이그레이션·복합 인덱스 생성(쿼리 플랜이 SCAN→SEARCH로 개선됨을 확인)
5. gpt-4o-mini로 종목별 모멘텀 스코어(0~100) 자동 산출 → DB에 누적 기록하여 시점 간 점수 변화 추적(70→85 등)
6. 3-테이블 LEFT JOIN 종합 리포트 생성, DB 백업 및 일일 CSV 리포트 자동 내보내기

**산출물**: `quant.db`(정규화 DB), 시각화 차트(정규화 지수 추이, 거래량·일별수익률), `daily_report_YYYYMMDD.csv`, DB 백업 파일

### Week 4 — 리스크 정량화와 AI Function Calling (Phase 1 캡스톤)

**학습한 내용**
- **MDD(최대 낙폭)**: `cummax()` 기반 peak-to-trough 계산
- **VaR(Value at Risk) 3가지 추정법** 비교: Historical(분포 무가정) / Parametric(정규분포, μ−1.645σ) / Monte Carlo(10,000회 시뮬레이션)
- **CVaR(Expected Shortfall)**: 꼬리 평균으로 VaR보다 보수적인 지표
- 상관계수 행렬과 분산투자 효과(위기 시 상관계수 0.3→0.9 수렴 — 분산 효과의 한계)
- 베타(β) 추정(선형회귀), 단일·다중요인 스트레스 테스트(시장·금리·환율 충격의 행렬 연산)
- LLM **Function Calling**: 자연어 질의 → 파라미터 추출 → 결정론적 계산 → 결과 해석의 2단 호출 패턴
- Kupiec 백테스팅으로 VaR 모형 적합성 검증

**직접 수행한 작업**
1. Week 3 DB의 1년치 시세로 동일가중 5종목 포트폴리오 NAV 곡선 구축, MDD 계산(-28.5%) 및 낙폭 시각화
2. 포트폴리오 VaR 95%를 3가지 방법으로 산출·비교(Historical -2.4%, CVaR -4.2%), fat tail 존재 확인
3. 개별 VaR 단순합 vs 포트폴리오 VaR 비교로 **분산투자 효과를 정량화**, 5×5 상관계수 히트맵 작성
4. KOSPI 지수 대비 종목별 베타를 회귀로 추정 → "KOSPI -15%" 단일요인 스트레스(-12.8%) 및 시장·금리·환율 3요인 민감도 행렬 스트레스(-8.4%) 수행
5. Anthropic Function Calling으로 "금리 +200bp, 코스피 -10%, 환율 +5%" 같은 자연어 시나리오를 받아 자동으로 스트레스 테스트를 실행하고 결과를 해석하는 AI 도구 구현 — "계산은 코드, 해석은 AI, 판단은 인간" 원칙으로 환각(hallucination) 가드레일 설계
6. 60일 롤링 윈도우 Kupiec 백테스트로 VaR 위반율(240일 중 12회 = 5%) 검증
7. `stress_runs` 테이블에 시나리오 파라미터(JSON)·손익·취약 종목·AI 요약을 누적 저장하여 "취약성 시계열" 추적 체계 구축

**산출물**: NAV+MDD 차트, VaR 3개 방법 비교표, 상관계수 히트맵, 베타 벡터, 다중요인 스트레스 결과, AI 시나리오 해석 리포트, 백테스트 판정, `risk_summary_YYYYMMDD.csv`

### 학습 태도의 증거 (Q&A 기록 기반)

수업 Q&A 기록(qna.md, week4_qna.md — 80여 개 문답)에서 드러나는 특징:
- **수학적 엄밀성 추구**: "왜 하필 -1.645인가?", "로그 수익률과 단순 수익률의 통계적 차이는?", "VaR 95% = -2.4%의 정확한 의미는?" (VaR을 손실 한도로 오해하는 흔한 오류를 스스로 잡아냄)
- **시스템 사고**: 주차별 결과물이 다음 주차의 입력이 되는 데이터 파이프라인 연속성, 스키마 계약(ticker/date/close) 질문
- **프로덕션 마인드**: API 장애 시 fallback 로직, 재현성을 위한 random seed, 실서비스 적용 시 우선 개선 3가지 등 실험실 너머를 묻는 질문
- **AI에 대한 비판적 태도**: LLM 환각 방지 장치, 결정론적 계산과 휴리스틱 해석의 분리 구조에 대한 질문

---

## 2. 영문 지원서용 문구 (Application-Ready, English)

### 2-1. Resume — Projects 섹션

**AI-Assisted Quantitative Investment Analysis System** | *Python, SQL, OpenAI/Anthropic APIs* | 2026
- Built an end-to-end quantitative analysis pipeline in Python that ingests a year of real Korean stock-market (KRX) data for 5 securities, computes technical indicators, and generates AI-driven investment reports
- Designed a normalized 3-table SQLite database with composite keys, transactions, and indexing to persist daily prices and AI-generated momentum scores, enabling time-series queries (e.g., self-joins for week-over-week returns)
- Quantified portfolio risk using Maximum Drawdown, Value-at-Risk (historical, parametric, and 10,000-path Monte Carlo methods), CVaR, and multi-factor stress tests (market, interest-rate, FX shocks) with beta estimation via linear regression
- Integrated LLMs as analysis tools: GPT-4o Vision for chart-image interpretation and Anthropic function calling to translate natural-language scenarios into deterministic stress-test computations, with guardrails separating calculation (code) from interpretation (AI)
- Validated the VaR model with Kupiec backtesting over a rolling 60-day window (violation rate ≈ 5%, within acceptance bounds)

*(공간이 부족하면 위 5개 중 1·3·4번 3개만 사용 권장)*

### 2-2. Common App — Activities 섹션 (글자수 제한 버전)

- **Position/Leadership (50자 이내)**:
  `Student, Quantitative Finance & AI Programming Course`
- **Description (150자 이내)**:
  `Built a Python system analyzing 1yr of Korean stock data: SQL database, VaR/stress-test risk models, and LLM integration for AI-driven reports.`

### 2-3. UC Application / 자유 양식 Extracurricular (약 350자)

> Over an intensive 8-session quantitative finance program, I built a complete investment-analysis system from scratch in Python. Starting with raw market data from the Korean stock exchange, I progressed from computing moving averages, to designing a normalized SQL database, to implementing the risk models used by real financial institutions—Value-at-Risk, Monte Carlo simulation, and multi-factor stress testing. The most exciting part was integrating large language models responsibly: my system uses AI to interpret charts and explain risk scenarios in plain language, but keeps every calculation deterministic and code-driven, because I learned that in finance, you verify before you trust.

### 2-4. Personal Statement 소재 (서사 앵글 3종)

**앵글 A — "검증하는 습관" (지적 성실성 서사)**
VaR 95%가 -2.4%라는 결과를 처음 봤을 때 "최악의 경우 2.4% 손실"로 읽었다가, 그것이 '한도'가 아니라 '확률적 경계'이며 나머지 5%의 꼬리(CVaR -4.2%)가 진짜 위험임을 깨달은 경험 → 숫자를 받아들이기 전에 그 정의를 의심하는 습관 → 모형 자체를 Kupiec 백테스트로 검증하기까지의 과정. *"All models assume. Test the assumptions themselves."*

**앵글 B — "AI 시대의 분업" (기술 윤리·설계 철학 서사)**
AI가 차트를 읽고 투자 의견까지 내는 시스템을 직접 만들면서 오히려 AI를 덜 신뢰하게 된 역설 → 환각을 막기 위해 "계산은 코드, 해석은 AI, 판단은 인간"이라는 아키텍처를 설계 → AI를 잘 쓰는 능력이란 AI에게 무엇을 맡기지 않을지를 아는 것. (CS/데이터사이언스 전공 지원 시 특히 효과적)

**앵글 C — "4주 만에 쌓은 시스템" (성장·집요함 서사)**
1주차에 변수와 함수를 배우던 수준에서 4주 만에 정규화된 데이터베이스, 몬테카를로 시뮬레이션, 회귀 기반 베타 추정까지 도달 → 매주 결과물이 다음 주의 입력이 되는 파이프라인 구조 덕분에 "한 번 만든 것은 버리지 않는다"는 누적적 학습을 체득 → 진단평가 13문항을 스스로 재구현하며 통과한 경험. (수학/통계/금융공학 전공 지원 시 효과적)

---

## 3. Summary (요약 버전)

### 한글 요약 (3문장)

편입 준비생인 이 학생은 8세션의 퀀트 금융·AI 프로그래밍 과정에서 KRX 5개 종목의 1년치 실시세를 다루는 엔드투엔드 분석 시스템을 Python으로 직접 구축했다. 데이터 수집(pykrx API)과 기술적 분석·시각화(pandas, Plotly)에서 출발해, 정규화된 SQLite 데이터베이스 설계, MDD·VaR(3가지 추정법)·CVaR·다중요인 스트레스 테스트 등 기관 수준의 리스크 측정, Kupiec 백테스팅까지 수행했다. 특히 GPT-4o Vision과 Anthropic Function Calling을 분석 도구로 통합하되 "계산은 코드, 해석은 AI, 판단은 인간"이라는 가드레일을 설계해, AI를 비판적으로 활용하는 엔지니어링 관점을 보여주었다.

### English Summary (3 sentences)

Through an 8-session quantitative finance and AI programming course, this student independently built an end-to-end analysis system in Python covering a full year of real Korean stock-market data for five securities. The work progressed from data ingestion (pykrx API) and technical analysis with visualization (pandas, Plotly) to designing a normalized SQLite database and implementing institution-grade risk measurement—Maximum Drawdown, Value-at-Risk via three estimation methods, CVaR, multi-factor stress testing, and Kupiec backtesting. Notably, the student integrated GPT-4o Vision and Anthropic function calling as analysis tools while designing guardrails under the principle "calculation by code, interpretation by AI, decision by human," demonstrating a critical, engineering-minded approach to AI.

### 핵심 키워드 (지원서 작성 시 참고)

| 분류 | 키워드 |
|---|---|
| 프로그래밍 | Python, pandas, NumPy, SciPy, matplotlib, Plotly |
| 데이터베이스 | SQL, SQLite, 정규화(1NF~3NF), 트랜잭션(ACID), 인덱싱, UPSERT |
| 퀀트 금융 | OHLCV, 이동평균, 골든크로스, HHI(섹터 집중도), MDD, VaR(Historical/Parametric/Monte Carlo), CVaR, 베타, 상관계수, 스트레스 테스트, Kupiec 백테스팅 |
| AI/LLM | GPT-4o Vision(멀티모달), Anthropic Function Calling, 프롬프트 엔지니어링, 환각 가드레일 |
| 엔지니어링 | API 통합, 데이터 파이프라인, 멱등적 적재, fallback 설계, 백업 자동화, 재현성(random seed) |

---

## 4. 작성 시 유의사항 (정직성 체크)

지원서에 쓸 때 다음 경계를 지키는 것을 권장한다:

1. **"수강 과정 내 가이드된 프로젝트"임을 과장하지 말 것** — 강사 주도 커리큘럼을 따라 구현한 것이므로 "독자적으로 연구·개발했다(independently researched)"보다는 "built / implemented / designed (within a structured course)"가 안전하다. 다만 진단평가를 스스로 통과하고 Q&A에서 깊이 있는 질문을 한 기록은 능동적 학습의 진짜 증거이므로 강조해도 좋다.
2. **수치는 실제 노트북 출력 기준** — MDD -28.5%, VaR -2.4%, HHI 0.354 등은 실습 결과물에 실제로 존재하는 수치다. 인터뷰에서 설명할 수 있어야 한다.
3. **8주 과정 중 4주 완료 시점** — 지원 시점에 5~8주차(포트폴리오 최적화: Markowitz, Sharpe, Black-Litterman)까지 마쳤다면 이 문서를 업데이트해 추가할 것.
4. **투자 성과를 주장하지 말 것** — 이 프로젝트는 분석 시스템 구축이지 실제 투자 수익이 아니다. "수익률 X% 달성" 같은 표현은 쓰지 않는다.
