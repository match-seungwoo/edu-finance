# AI Quant-Mate 프로젝트 면접 Q&A (총 30문항)

> 8주 과정 중 1~4주차 "개인 퀀트 시스템 완성" 단계를 마친 수강생을 대상으로 한 인터뷰 질문 세트입니다. 각 문항은 **질문 + 면접관 체크포인트(모범답안 요지)** 형식으로 작성되었습니다.

---

## 🟢 초급 (Easy) — 개념·도구 사용법 (10문)

### Q1. 1주차에서 `pykrx`를 사용한 이유는 무엇인가요? `yfinance`와 같은 다른 라이브러리 대신 선택한 배경을 설명해 주세요.
**Check:** 한국거래소(KRX) 데이터 직접 조회 / 종목코드는 6자리 문자열(앞자리 0 보존) / `stock.get_market_ohlcv_by_date()`로 OHLCV 일별 시세를 가져옴.

### Q2. 이동평균선 MA5, MA20, MA60은 각각 무엇을 의미하나요? 그리고 코드로는 어떻게 계산했나요?
**Check:** 5일/20일/60일 종가 평균 = 단기/중기/장기 추세 / `df["종가"].rolling(window=5).mean()` / window-1 만큼 앞에 NaN 발생.

### Q3. "골든크로스"와 "데드크로스"의 차이를 설명하고, 정배열(MA5 > MA20 > MA60)이 왜 상승 신호로 해석되는지 답해 주세요.
**Check:** 단기선이 장기선을 상향 돌파=골든크로스(매수 신호), 하향 돌파=데드크로스(매도 신호) / 정배열은 모든 기간의 매수세가 우세함을 의미.

### Q4. Google Colab 환경에서 OpenAI / Anthropic API 키를 안전하게 관리하기 위해 어떤 방법을 썼나요?
**Check:** `from google.colab import userdata` → `userdata.get("OPENAI_API_KEY")` / 노트북에 하드코딩 금지 / GitHub 커밋 시 키 노출 방지.

### Q5. Plotly의 `go.Candlestick()`을 호출할 때 필수로 넘겨야 하는 4개의 인자는 무엇인가요?
**Check:** `x`(날짜), `open`, `high`, `low`, `close` — 시고저종 4개 + x축.

### Q6. 차트 이미지를 GPT-4o Vision API에 보내기 전 Base64로 인코딩하는 이유는 무엇인가요?
**Check:** 바이너리 이미지 데이터를 텍스트(ASCII)로 변환해야 JSON 페이로드에 임베드 가능 / `base64.b64encode(image_bytes).decode()`.

### Q7. 2주차에서 다룬 `portfolio.csv`의 컬럼 구조를 설명해 주세요.
**Check:** `ticker`(종목코드), `name`(종목명), `quantity`(수량), `current_price`(현재가), `sector`(섹터) — 5개 컬럼.

### Q8. pandas에서 DataFrame과 Series의 차이는 무엇인가요?
**Check:** DataFrame = 2차원 표(여러 컬럼) / Series = 1차원 배열(한 컬럼 또는 인덱싱된 값) / `df["weight"]` 결과는 Series.

### Q9. 3주차에서 SQLite의 PRIMARY KEY와 FOREIGN KEY는 어떻게 사용했나요?
**Check:** `tickers` 테이블의 PK는 `ticker` / `prices` 테이블은 복합 PK `(ticker, date)` / `ai_reviews.ticker`는 `tickers.ticker`를 참조하는 FK.

### Q10. CSV로 매일의 시세를 저장할 때 발생하는 가장 큰 문제는 무엇이며, 왜 DB로 옮겼나요?
**Check:** 매일 덮어쓰기 → 과거 데이터 손실 / 타입 손실(숫자가 문자열로) / 검색·필터링 어려움 / 동시성 위험.

---

## 🟡 중급 (Medium) — 응용·연결 (10문)

### Q11. 종목 비중과 섹터별 비중을 계산할 때 pandas의 어떤 패턴을 사용했나요? for 루프를 사용하지 않은 이유는 무엇인가요?
**Check:** 벡터 연산 / `df["value"] = df["quantity"] * df["current_price"]` → `df["weight"] = df["value"] / df["value"].sum()` / `groupby("sector")["weight"].sum()` / for 루프는 느리고 가독성 낮음(broadcasting 활용).

### Q12. HHI(Herfindahl-Hirschman Index)는 왜 비중을 **제곱**해서 합산하나요? 산술 합이 아닌 제곱을 선택한 이유는?
**Check:** 큰 비중은 더 크게, 작은 비중은 더 작게 반영 → 쏠림 극대화 / `(0.5)² = 0.25` vs `(0.1)² = 0.01` / 1/N에 수렴할수록 분산.

### Q13. HHI가 0.15 / 0.25를 기준으로 나뉘는데, 각각 어떤 상태이고 0.3이 나왔다면 어떻게 조치해야 할까요?
**Check:** <0.15 분산 양호 / 0.15~0.25 주의 / >0.25 고집중·리밸런싱 필요 / 0.3이면 가장 비중 큰 섹터를 줄이고 저상관 섹터로 분산.

### Q14. groupby의 Split-Apply-Combine 3단계를 섹터별 비중 계산을 예로 설명해 주세요.
**Check:** Split: `groupby("sector")`로 섹터별 부분집합 / Apply: 각 그룹에 `.sum()` 적용 / Combine: 결과를 하나의 Series로 결합.

### Q15. 3주차 `prices` 테이블에서 "오늘 종가와 7일 전 종가"를 한 행에 보고 싶다면 어떤 SQL을 작성하나요?
**Check:** Self-Join 패턴 / `FROM prices now JOIN prices past ON now.ticker = past.ticker AND past.date = date(now.date, '-7 day')`.

### Q16. `INSERT OR REPLACE`(UPSERT)는 언제 사용했고, 단순 `INSERT`와 어떻게 다른가요?
**Check:** 동일 PK 행이 이미 있으면 새 데이터로 덮어쓰기 / 매일 동일 (ticker, date) 시세를 재수집할 때 PK 충돌 방지 / 단순 INSERT는 UNIQUE constraint 위반 에러.

### Q17. 4주차에서 MDD(Maximum Drawdown)는 어떻게 계산했나요? `cummax()`가 핵심인 이유는?
**Check:** `peak = nav.cummax()` → 지금까지의 누적 최고점 추적 / `drawdown = nav / peak - 1` → 고점 대비 현재 위치 / `mdd = drawdown.min()` / cummax 없이는 "역사상 최고점"을 알 수 없음.

### Q18. VaR을 구하는 Historical, Parametric, Monte Carlo 세 방법 중 자신이 선택한 방법과 그 이유를 설명해 주세요.
**Check:** Historical = 과거 분포 그대로(직관적·꼬리 반영, 데이터 양 의존) / Parametric = 정규분포 가정(빠름·fat tail 과소평가) / MC = 시뮬레이션 1만 번(유연·계산 비용) / 상황별 트레이드오프 설명 가능 여부.

### Q19. 4주차 시나리오 스트레스에서 "베타(β)"는 어떻게 활용되나요?
**Check:** $\text{Stock PnL} = \beta \times \text{Market Shock}$ / 베타=1은 시장과 동일 변동 / 베타=1.5면 시장 -10% 시 종목 -15% / 회귀(`scipy.stats.linregress` 또는 `np.polyfit`)로 추정.

### Q20. 2주차에서 AI(LLM)에게 포트폴리오 비평을 시킬 때, 단순히 CSV를 통째로 넣지 않고 어떤 가공을 거쳐 프롬프트에 넣었나요?
**Check:** HHI, 섹터별 비중 표, 상위 비중 종목 등 **요약 통계**를 텍스트로 정리 / "퀀트 애널리스트" 페르소나 부여 / 출력 형식 강제(현재 상태/리스크/리밸런싱 제안).

---

## 🔴 고급 (Hard) — 깊이·트레이드오프·설계 (10문)

### Q21. 단순 수익률 대신 **로그 수익률**($r_t = \ln(P_t / P_{t-1})$)을 사용하는 이유를 시계열·통계 관점에서 설명해 주세요.
**Check:** 시간 가법성(여러 기간 합산이 단순 덧셈) / 정규분포 근사 더 좋음 / 작은 값에서는 단순 수익률과 거의 같음 / VaR/CVaR 모형 가정과 정합.

### Q22. "분산투자(Diversification)는 최악의 순간에 사라진다"는 말이 4주차에서 어떻게 검증되는지 설명해 주세요.
**Check:** 평시 종목 간 상관계수 ρ≈0.3 → 위기 시 ρ→0.9 / $\sigma_p^2 = \sum w_i^2 \sigma_i^2 + 2\sum w_i w_j \sigma_i \sigma_j \rho_{ij}$ / ρ 증가 시 포트 분산이 개별 분산 합에 수렴 → 분산효과 소멸.

### Q23. CVaR(Expected Shortfall)는 VaR과 어떻게 다르며, 왜 "더 보수적인" 위험 지표라고 부르나요?
**Check:** VaR = 5% 분위수(경계선) / CVaR = `E[R | R ≤ VaR]` (꼬리 평균) / VaR은 "이 정도까지는 잃을 수 있다", CVaR은 "그 너머가 얼마나 깊은지" / fat tail 분포에서 차이 커짐 / Coherent risk measure 조건(subadditivity) 만족.

### Q24. 정규분포 가정 기반의 Parametric VaR이 실제 금융 데이터에서 위험을 과소평가하는 이유는?
**Check:** Fat tail(첨도>3) / Skewness(왼쪽 꼬리 두꺼움) / 변동성 군집(GARCH 효과) / 1.645σ가 실제 5% 분위수보다 작음(0.05보다 더 자주 발생) / 해결: Student-t, EVT, Historical.

### Q25. AI Function Calling에서 **2차 호출**이 반드시 필요한 이유는 무엇인가요? 1차 호출만으로 끝내면 어떤 문제가 발생하나요?
**Check:** 1차: LLM이 인자 추출 → tool_use 응답만 옴 / Python이 실제 계산 실행 / 2차: tool_result를 메시지에 추가해 다시 LLM 호출 → 비로소 자연어 해설 생성 / 1차로 끝내면 JSON만 있고 사용자 친화적 해석 없음 / `messages` 배열에 history 누적 필수.

### Q26. 3주차 정규화(1NF, 2NF, 3NF)와 성능을 위한 비정규화의 트레이드오프를 본인 프로젝트에서 어떻게 결정했나요?
**Check:** `tickers`(name, sector 한 곳) / `prices`(시세만) 분리 → 종목명 바뀌어도 한 곳만 업데이트 / 단점: JOIN 비용 / 매일 수천 행 추가되는 시세에는 INDEX(ticker, date)로 보완 / OLTP는 정규화, OLAP 리포트는 비정규화 view 사용 가능.

### Q27. VaR 백테스트(Kupiec test)는 어떤 원리이며, rolling 60일로 추정한 VaR이 적정한지 어떻게 판정했나요?
**Check:** 60일 window로 5% VaR 추정 → 다음 날 실제 수익률이 VaR보다 더 손실이면 "위반" 카운트 / 전체 기간 위반률이 5%에 근접해야 모델 정확 / 너무 적게(<2%) 위반=보수적, 많이(>8%) 위반=과소평가 / 이항분포 가정 가능도비검정(LR).

### Q28. 다요인 스트레스 시나리오(금리 +200bp, 환율 +10%, 시장 -15%)에서 종목별 손익을 계산하는 식을 일반화해 설명해 주세요.
**Check:** $\text{PnL}_i = \sum_j \beta_{i,j} \times \text{Shock}_j$ / 민감도 행렬 $B \in \mathbb{R}^{N \times K}$ (종목 × 요인) / 충격 벡터 $s \in \mathbb{R}^K$ / 포트 손익 = $w^T B s$ / 베타 추정의 안정성·요인 간 상관 처리는 별도 이슈.

### Q29. 1~4주차 결과물이 어떻게 파이프라인으로 연결되는지, 각 주차 산출물이 다음 주차의 입력으로 어떻게 쓰이는지 설명해 주세요.
**Check:** W1 `analysis_YYYYMMDD.csv`(종목/현재가/AI 의견) → W2 입력 / W2 `portfolio_weights.csv` + HHI → W3 DB 적재(prices, ai_reviews) / W3 `quant.db` 시계열 → W4 MDD·VaR 계산 입력 / 데이터 계약(스키마)이 일관되어야 작동 / "각 주가 다음 주의 입력을 만든다"는 설계 원칙.

### Q30. 만약 본 프로젝트를 실제 운용(production)에 옮긴다면, 현재 구조에서 가장 먼저 보완해야 할 3가지는 무엇이라고 생각하나요?
**Check:** (열린 질문) 예시 답변
- **데이터 무결성**: SQLite → PostgreSQL/TimescaleDB, 트랜잭션·동시성 / 일일 ETL 스케줄러(Airflow)
- **모델 검증**: VaR 백테스트 자동화·드리프트 모니터링 / 정규분포 가정 → EVT/Student-t로 교체 검토
- **AI 신뢰성**: LLM 출력 검증 레이어(스키마 검증, hallucination 가드) / 비용·레이트 리밋 / Function Calling 결과의 결정성 확보
- **보안**: API 키 시크릿 매니저, 감사 로그, 권한 분리
- **재현성**: 코드·데이터·모델 버전 고정(MLflow, DVC)
- 면접관이 "왜 그 3개인지" 깊이를 보는 질문.

---

## 평가 가이드 (제안)

| 등급 | 기준 |
|------|------|
| **A** | 초·중급 18문항 이상 + 고급 6문항 이상 명확히 답변 + Q29/Q30 같은 설계 사고 가능 |
| **B** | 초·중급 14문항 이상 + 고급 3~5문항 답변 |
| **C** | 초급 위주로 답변, 중·고급은 부분적 |

총 30문항. 면접 시간 60~90분 권장(문항당 평균 2~3분).
