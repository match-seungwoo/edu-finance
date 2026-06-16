# Week 1 진단 테스트 — 전체 설명

> `week1_diagnostic.ipynb`가 무엇을 테스트하는지, 왜 그렇게 구성되어 있는지 설명하는 문서.
> 힌트·정답은 `week1_diagnostic_hints.md`에 따로 있다. 이 문서는 **시험의 설계 의도**를 다룬다.

---

## 1. 이 테스트의 목적

week2 수업(pandas·groupby·HHI·AI 비평)으로 넘어가기 전에,
week1에서 다룬 **6개 영역의 기본기**가 손에 붙어 있는지 확인한다.

단순 암기 문제가 아니다. 각 문제는 **다음 문제의 입력**이 된다.
예: Q4에서 만든 `start_date`, `end_date`가 Q8의 pykrx 호출에 그대로 쓰이고,
Q8의 `samsung_df` 구조가 Q9의 `dfs`로 확장되며, Q9의 `dfs['삼성전자']`가
Q10의 차트 재료가 된다. 앞 문제를 틀리면 뒤가 전부 깨진다.

**합격 기준**: 13문제 전부 `✅ PASS`. 13/13이 아니면 week2 진입 불가.

---

## 2. 노트북 구조

```
Part 1 — 환경 (Q1, Q2)
Part 2 — Python 기본기 (Q3, Q4)
Part 3 — pandas (Q5, Q6, Q7)
Part 4 — pykrx 데이터 (Q8, Q9)
Part 5 — plotly 시각화 (Q10, Q11)
Part 6 — AI 호출 (Q12, Q13)
최종 점검 (FINAL SCOREBOARD)
```

각 문제는 3개 셀 + 힌트로 구성된다:
1. **TODO 셀**: 학생이 코드를 채우는 빈 셀.
2. **CHECK 셀**: `assert` 기반 자동 검증. PASS/FAIL 출력.
3. **💡 1차 힌트 / 📖 2차 전체 설명**: `<details>` 접힘 블록.
   펼치기 전까지 정답이 안 보인다.

**운영 원칙** (노트북 상단 규칙)
- CHECK가 PASS 떠야 다음 문제로 간다.
- 힌트는 **5분 혼자 붙잡은 뒤**에만 연다.
- 펼쳐 본 코드를 복붙하지 않고 손으로 다시 친다.

---

## 3. 사전 설치 셀

```python
!pip install pykrx openai plotly==5.24.1 kaleido==0.2.1 -q
```

- `pykrx`: 한국 주식 데이터(KRX) 조회.
- `openai`: OpenAI API 공식 SDK.
- `plotly==5.24.1`: 시각화. 버전을 고정한 이유는 이후 버전에서 Colab과 간헐적 호환 이슈가 있기 때문.
- `kaleido==0.2.1`: plotly Figure를 PNG로 저장하는 백엔드. 0.2.1로 못 박는 이유도 같다 — 최신은 Colab에서 깨지는 케이스가 있다.

---

## 4. Part별 학습 목표 & 문제 해설

### Part 1 — 환경 (Q1, Q2)

**목표**: 코드 한 줄도 쓰기 전에 **환경이 제대로 세팅됐는지** 본다.

#### Q1. 라이브러리 import

- 테스트 대상: `import` 문법 두 가지.
  - `import X as 별명` (pandas)
  - `from X import Y` (datetime, pykrx, openai)
- 검증 원리: CHECK 셀이 `dir()`에 이름이 있는지 확인한다.
  - `pd.__name__ == 'pandas'` 로 pandas가 진짜 import 됐는지까지 본다.
- 흔한 실수: `import pandas`만 하고 `pd` 별명을 안 붙이는 것. → CHECK에서 즉시 fail.

#### Q2. OpenAI 클라이언트 생성

- 테스트 대상: API 키를 환경에서 꺼내 `OpenAI(api_key=...)` 클라이언트 만들기.
- 환경 분기:
  - Colab → `userdata.get('OPENAI_API_KEY')`
  - 로컬 → `os.environ['OPENAI_API_KEY']`
- 검증 원리: **실제로 API를 한 번 호출해 본다** (`gpt-4o-mini`에 "ping").
  키가 틀리면 여기서 4xx가 떠서 fail.
- 보안 포인트: 키를 코드에 박지 않는다. `print(key)`로 노출시키지 않는다.

---

### Part 2 — Python 기본기 (Q3, Q4)

**목표**: dict와 datetime 조작. 이후 pykrx 호출의 입력을 만드는 파트.

#### Q3. 종목 dict

- 테스트 대상: 한글 키 + **문자열 티커** dict.
- 검증 포인트: 티커를 숫자로 넣으면 안 된다.
  - `005930` (문자) vs `5930` (숫자). 앞의 0이 사라지면 pykrx가 못 찾는다.
- CHECK: `target_stocks.get('삼성전자') == '005930'` — 값뿐 아니라 **타입**까지 맞아야 통과.

#### Q4. 날짜 문자열

- 테스트 대상: `datetime` + `timedelta` + `strftime`.
- 포맷: `"%Y%m%d"` → `20260422` 같은 8자리 연속 숫자.
  pykrx는 **구분자 없는** 포맷만 받는다. `2026-04-22`는 에러.
- 검증 원리:
  - 길이 8 + `isdigit()` 체크
  - `strptime`으로 다시 파싱해 `end_date - start_date`가 **1년(±5일)**인지 확인.
- 이후 연결: 여기서 만든 `start_date`, `end_date`가 Q8·Q9의 pykrx 인자로 재사용된다.

---

### Part 3 — pandas (Q5, Q6, Q7)

**목표**: DataFrame 생성, 컬럼 접근, 벡터 연산(rolling), 인덱싱(iloc).

#### Q5. DataFrame 생성 & 평균

- 테스트 대상: `pd.DataFrame({...})` 생성 + `df["컬럼"].mean()`.
- 핵심 감각: dict의 각 value는 **같은 길이의 리스트**여야 한다.
- CHECK: `mean_close == 120.0` 여야 PASS. 평균을 손으로 계산하면 (100+110+120+130+140)/5 = 120.

#### Q6. 이동평균 (rolling)

- 테스트 대상: `df["종가"].rolling(window=3).mean()`.
- 핵심 감각: **앞 2개 행은 NaN이 정상**이다. window=3인데 1번째, 2번째 행은 평균을 낼 값이 부족하다.
- CHECK에서 검증하는 값:
  - `iloc[0]`, `iloc[1]` → `NaN`
  - `iloc[2]` → `(10+20+30)/3 = 20.0`
  - `iloc[-1]` → `(50+60+70)/3 = 60.0`
- 이후 연결: MA5/MA20/MA60 (Q9)의 기초.

#### Q7. iloc로 마지막 값

- 테스트 대상: `df.iloc[-1]` 또는 `Series.iloc[-1]`로 마지막 행/값 꺼내기.
- 핵심 감각: `iloc`는 **정수 위치** 기반, `loc`는 **라벨(이름)** 기반.
  `-1`은 파이썬 관례대로 끝에서 첫 번째.
- 이후 연결: week1 리포트에서 "마지막 거래일 종가"를 뽑을 때 쓰는 패턴.

---

### Part 4 — pykrx 데이터 (Q8, Q9)

**목표**: 실제 한국 주식 데이터 수집. 문자열·dict·pandas가 여기서 합쳐진다.

#### Q8. 단일 종목 1년치 OHLCV

- 테스트 대상: `stock.get_market_ohlcv_by_date(start_date, end_date, 티커)`.
- 인자 순서 주의: **날짜가 앞, 티커가 뒤**. 뒤집으면 빈 DataFrame.
- 결과 구조:
  - 인덱스: `DatetimeIndex` (날짜)
  - 컬럼: `시가 / 고가 / 저가 / 종가 / 거래량 / 등락률`
- CHECK:
  - DataFrame 타입인가
  - 100일 초과 (1년치면 주말·공휴일 빼고 약 240~250일)
  - 필수 5개 컬럼 포함 확인
- 실패 원인: 날짜 포맷 오류 / 티커 문자열 아님 / 네트워크 문제.

#### Q9. 3종목 dict + MA 컬럼

- 테스트 대상: dict 순회 + 반복적 pykrx 호출 + rolling 컬럼 추가.
- 패턴:
  ```python
  for name, ticker in target_stocks.items():
      df = stock.get_market_ohlcv_by_date(start_date, end_date, ticker)
      df["MA5"]  = df["종가"].rolling(5).mean()
      df["MA20"] = df["종가"].rolling(20).mean()
      df["MA60"] = df["종가"].rolling(60).mean()
      dfs[name] = df
  ```
- 흔한 함정: df 객체를 루프 **밖에서** 재사용해 3종목 데이터가 동일해지는 버그.
  반드시 루프 **안에서** 새로 받아야 한다.
- CHECK: 키 3개 정확, MA5/MA20/MA60 컬럼 전부 존재, MA60이 전부 NaN은 아님(1년치면 60일 이후부터 값이 채워진다).

---

### Part 5 — plotly 시각화 (Q10, Q11)

**목표**: 인터랙티브 차트 그리기 + 정적 이미지로 저장.

#### Q10. Candlestick + MA 3개

- 테스트 대상: `go.Figure(data=[...])`에 Candlestick 1개 + Scatter 3개.
- 캔들: `go.Candlestick(x=, open=, high=, low=, close=)` — OHLC를 명시적으로 매핑.
- 라인: `go.Scatter(x=df.index, y=df["MA5"], name="MA5")` × 3.
- 공통 감각: **모든 trace가 같은 x축(날짜)** 위에 그려져야 겹친다.
- CHECK:
  - `fig`가 `go.Figure` 인스턴스인가
  - trace 타입 중 `candlestick` 1개 포함
  - `scatter` 3개 이상 포함

#### Q11. PNG 저장

- 테스트 대상: `fig.write_image("chart_test.png", engine="kaleido")`.
- 권장 옵션: `width=1200, height=700, scale=2` — AI Vision이 세밀한 선을 더 잘 읽게 해상도 2배.
- CHECK:
  - 파일이 실제로 생성됐는가
  - 파일 크기 > 10KB (너무 작으면 저장 실패)
- 실패 원인: kaleido 버전 불일치 → `!pip install kaleido==0.2.1 -q`로 재설치.
- 이후 연결: Q12에서 이 PNG를 base64로 인코딩해 Vision API에 보낸다.

---

### Part 6 — AI 호출 (Q12, Q13)

**목표**: 이미지를 AI에 전달하는 **멀티모달 파이프라인**. week2에서 AI 비평으로 확장된다.

#### Q12. base64 인코딩 함수

- 테스트 대상: 파일을 바이너리로 읽어 base64 문자열로 변환하는 함수.
- 정석 패턴:
  ```python
  def encode_image(path: str) -> str:
      with open(path, "rb") as f:
          return base64.b64encode(f.read()).decode("utf-8")
  ```
- 왜 base64인가: OpenAI API는 JSON 기반. JSON에는 이진 바이트를 직접 못 넣는다.
  base64는 이진 → ASCII 변환 방식. 크기가 ~33% 커지지만 JSON에 안전하게 실린다.
- CHECK:
  - 함수 `callable`
  - 결과가 문자열 + 길이 > 1000
  - 디코딩 후 **PNG 시그니처** (`\x89PNG\r\n\x1a\n`) 일치

#### Q13. Vision API 호출

- 테스트 대상: `gpt-4o` 모델에 텍스트 + 이미지를 동시에 보내기.
- 메시지 구조의 핵심: `content`가 문자열이 아니라 **리스트**다.
  ```python
  "content": [
      {"type": "text", "text": "..."},
      {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}},
  ]
  ```
- `data:image/png;base64,` 접두사가 **필수**. 빠지면 `400 invalid_image_url`.
- CHECK: 응답이 문자열이고 길이 > 50(짧으면 호출 실패로 간주).
- 이후 연결: week2에서 텍스트만 보내는 버전으로 돌아가지만, 멀티모달 감각은 여기서 먼저 체화한다.

---

## 5. FINAL SCOREBOARD 동작 원리

마지막 셀은 13개의 `lambda` 함수로 전역 상태를 다시 검증한다.

```python
checks = {
    'Q1': lambda: all(n in dir() for n in [...]),
    'Q2': lambda: 'client' in dir() and ...,
    ...
}
```

- 각 lambda는 **예외를 낼 수 있다**. 상위 try/except로 감싸 fail 처리.
- 개별 CHECK 셀과 다른 점: **전역 변수 이름 + 기본 타입 확인**까지만 한다.
  Q2의 실제 API 호출 같은 무거운 검증은 다시 돌리지 않는다.
- 최종 출력: `13/13 PASS` → "합격". 아니면 "불합격 — FAIL 항목 재시도".

---

## 6. 문제 간 데이터 흐름 (요약)

```
Q1 (import) ─────────────────────────────────┐
                                             │
Q2 (client) ────────────────────────────┐    │
                                        │    │
Q3 (target_stocks) ──────────────┐      │    │
                                 │      │    │
Q4 (start_date, end_date) ──┐    │      │    │
                            ▼    ▼      │    │
Q8 (samsung_df) ←─ start/end/ticker     │    │
                            │            │    │
Q9 (dfs) ←── target_stocks ─┘            │    │
   │                                      │    │
   └─→ Q10 (fig) ── dfs['삼성전자']        │    │
          │                                │    │
          └─→ Q11 (chart_test.png)         │    │
                   │                        │    │
                   └─→ Q12 (img_b64) ──────┐│    │
                                            ▼▼    ▼
                                    Q13 (ai_analysis)
                                    ← client + img_b64
```

- **Q4 → Q8 → Q9 → Q10 → Q11 → Q12 → Q13**은 직렬 체인이다.
  하나가 틀리면 그 뒤로 전부 연쇄 fail.
- Q1, Q2, Q3은 체인의 **원료**. 먼저 PASS 받고 시작해야 뒤가 편하다.

---

## 7. 강사 체크리스트

- 학생이 Q1~Q2에서 30분 이상 붙잡고 있다면 환경 문제다. API 키 등록 방식을 화면 공유로 같이 본다.
- Q6에서 NaN 처리를 못 넘기면 `rolling`을 화이트보드에 3줄짜리 예시(값, 평균, NaN)로 그려 준다.
- Q9에서 3종목 데이터가 똑같이 나오면 루프 안에서 새 df를 안 받은 것이다. 이건 **반드시** 설명한다.
  week2 session3의 groupby와 직접 연결되는 감각.
- Q13에서 400 에러가 뜨면 `data:image/png;base64,` 접두사 확인 → 거의 100% 이게 원인.
- 13/13 찍고 나면 week2 `session3.html` → `session3.ipynb` 순으로 진입.
