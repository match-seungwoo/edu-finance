# Week 1 진단 테스트 — 힌트 & 전체 설명

> `week1_diagnostic_clean.ipynb`에서 막혔을 때 펼쳐 보는 참고 문서.
>
> **사용법**
> 1. TODO 셀을 혼자 **최소 5분** 붙잡고 있었는지 먼저 체크.
> 2. 그래도 안 풀리면 해당 문제의 **💡 1차 힌트** 섹션을 펼친다.
> 3. 힌트로도 안 풀리면 **📖 2차 전체 설명** 섹션을 펼친다.
> 4. 펼쳐서 보고 그대로 복붙하지 말고, 다시 TODO 셀로 돌아가 **손으로** 다시 쳐 본다.

---

## Q1. 라이브러리 import

<details>
<summary><b>💡 1차 힌트</b></summary>

- 단순 모듈은 `import X` 또는 `import X as 별명`
- 모듈 안 특정 대상은 `from X import Y`
- 5줄이면 충분하다. 한 줄에 하나씩.

</details>

<details>
<summary><b>📖 2차 전체 설명</b></summary>

```python
import pandas as pd
import base64
from datetime import datetime, timedelta
from pykrx import stock
from openai import OpenAI
```

**왜 이렇게**
- `pandas as pd`: 관례. 커뮤니티 코드 거의 전부가 `pd`로 쓴다.
- `from datetime import datetime, timedelta`: `datetime` 모듈 안에 같은 이름 클래스가 있어 헷갈리니 둘 다 가져와서 바로 쓴다.
- `from pykrx import stock`: `pykrx.stock`에 OHLCV 함수가 모여 있다.
- `from openai import OpenAI`: 최신 openai SDK는 `OpenAI()` 클라이언트 인스턴스 패턴.

</details>

---

## Q2. OpenAI 클라이언트 생성

<details>
<summary><b>💡 1차 힌트</b></summary>

- 환경에 따라 키 꺼내는 방식이 다르다:
	- Colab: `from google.colab import userdata` 후 `userdata.get('OPENAI_API_KEY')`
	- 로컬: `import os` 후 `os.environ.get('OPENAI_API_KEY')`
- 꺼낸 키를 `OpenAI(api_key=...)` 인자로 넣으면 끝.

</details>

<details>
<summary><b>📖 2차 전체 설명</b></summary>

**Colab**
```python
from google.colab import userdata
OPENAI_API_KEY = userdata.get('OPENAI_API_KEY')
client = OpenAI(api_key=OPENAI_API_KEY)
```

**로컬**
```python
import os
OPENAI_API_KEY = os.environ['OPENAI_API_KEY']  # 없으면 KeyError
client = OpenAI(api_key=OPENAI_API_KEY)
```

**주의**
- 키를 코드에 박아 넣지 말 것. GitHub에 올리는 순간 유출된다.
- `print(OPENAI_API_KEY)` 금지. 공유 화면에 그대로 뜬다.
- 키 길이 확인만 하려면 `print(f"len={len(OPENAI_API_KEY)}")`.

</details>

---

## Q3. 종목 딕셔너리

<details>
<summary><b>💡 1차 힌트</b></summary>

- 딕셔너리는 `{ "키": "값", "키2": "값2" }` 형식.
- 티커는 반드시 **문자열**. 앞에 0이 있어서 숫자로 넣으면 `5930`이 되어 망한다.

</details>

<details>
<summary><b>📖 2차 전체 설명</b></summary>

```python
target_stocks = {
    "삼성전자":   "005930",
    "SK하이닉스": "000660",
    "한미반도체": "042700",
}
```

**체크**
- `target_stocks["삼성전자"]` 쳐 보면 `'005930'` 문자열이 나와야 한다.
- `type(target_stocks["삼성전자"])`가 `<class 'str'>`인지 확인.

</details>

---

## Q4. 날짜 문자열

<details>
<summary><b>💡 1차 힌트</b></summary>

- 오늘 객체: `datetime.today()`
- 365일 빼기: `datetime.today() - timedelta(days=365)`
- 문자열로 포맷: `.strftime("%Y%m%d")`

</details>

<details>
<summary><b>📖 2차 전체 설명</b></summary>

```python
end_date = datetime.today().strftime("%Y%m%d")
start_date = (datetime.today() - timedelta(days=365)).strftime("%Y%m%d")
```

**포맷 코드**
- `%Y`: 4자리 연도 (2026)
- `%m`: 2자리 월 (01~12)
- `%d`: 2자리 일 (01~31)
- pykrx는 구분자 없는 `YYYYMMDD`만 받는다. `-` 넣으면 에러.

</details>

---

## Q5. DataFrame 생성과 컬럼 접근

<details>
<summary><b>💡 1차 힌트</b></summary>

- `pd.DataFrame({"컬럼명": [값1, 값2, ...]})` 형태.
- 평균은 `sample_df["종가"].mean()`.

</details>

<details>
<summary><b>📖 2차 전체 설명</b></summary>

```python
sample_df = pd.DataFrame({
    "날짜": ["2026-01-01", "2026-01-02", "2026-01-03", "2026-01-04", "2026-01-05"],
    "종가": [100, 110, 120, 130, 140],
})
mean_close = sample_df["종가"].mean()
```

**포인트**
- DataFrame 안 dict의 각 value는 **같은 길이의 리스트**여야 한다.
- `df["컬럼"]`는 Series(1차원). `.mean()`, `.sum()`, `.max()` 같은 집계 메서드가 바로 붙는다.

</details>

---

## Q6. 이동평균 계산 (rolling)

<details>
<summary><b>💡 1차 힌트</b></summary>

- `df["컬럼"].rolling(window=N).mean()`
- window=3이면 앞 2개 행은 NaN이 되는 게 정상이다.

</details>

<details>
<summary><b>📖 2차 전체 설명</b></summary>

```python
ma_df = pd.DataFrame({"종가": [10, 20, 30, 40, 50, 60, 70]})
ma_df["MA3"] = ma_df["종가"].rolling(window=3).mean()
```

**이동평균이 하는 일**
- index 2: (10+20+30)/3 = 20
- index 3: (20+30+40)/3 = 30
- ... index 6: (50+60+70)/3 = 60
- 앞의 2개(index 0, 1)는 3개가 안 모여서 NaN.

week1에서 MA5/MA20/MA60 만든 것과 같은 방식.

</details>

---

## Q7. 마지막 행 값 추출

<details>
<summary><b>💡 1차 힌트</b></summary>

- `iloc[-1]`은 **마지막 행**을 가리킨다.
- 특정 컬럼 값만 꺼내려면 Series에 `.iloc[-1]`을 붙이거나, 행을 먼저 꺼내서 `["컬럼"]`.

</details>

<details>
<summary><b>📖 2차 전체 설명</b></summary>

두 가지 방법 모두 된다:

```python
# 방법 1: 컬럼 Series 먼저, 마지막 원소
last_close = ma_df["종가"].iloc[-1]

# 방법 2: 마지막 행 먼저, 그 안에서 컬럼
last_close = ma_df.iloc[-1]["종가"]
```

**iloc vs loc**
- `iloc`: 정수 위치(positional). `-1`은 마지막.
- `loc`: 라벨(이름)로 접근. 날짜 인덱스면 `loc["2026-04-16"]`.

</details>

---

## Q8. 삼성전자 1년치 OHLCV

<details>
<summary><b>💡 1차 힌트</b></summary>

- 시그니처: `stock.get_market_ohlcv_by_date(시작일, 종료일, 티커)`
- 인자 순서 주의. 날짜가 앞, 티커가 뒤.

</details>

<details>
<summary><b>📖 2차 전체 설명</b></summary>

```python
samsung_df = stock.get_market_ohlcv_by_date(start_date, end_date, "005930")
samsung_df.tail()
```

**결과 DataFrame 구조**
- 인덱스: 날짜(`DatetimeIndex`)
- 컬럼: `시가 / 고가 / 저가 / 종가 / 거래량 / 등락률`
- 1년치면 주말·공휴일 빼고 보통 240~250일.

**에러 날 때**
- 빈 DataFrame이 반환되면 날짜 포맷(`YYYYMMDD`)이 잘못됐거나 티커가 틀린 경우.
- 네트워크 오류면 다시 실행.

</details>

---

## Q9. 3종목 dict + MA 컬럼 추가

<details>
<summary><b>💡 1차 힌트</b></summary>

- `for name, ticker in target_stocks.items()` 로 dict 순회
- 각 티커로 Q8과 같은 방식 조회 → `dfs[name] = df`
- 각 df에 `rolling(window=N).mean()` 3번 (5, 20, 60)

</details>

<details>
<summary><b>📖 2차 전체 설명</b></summary>

```python
dfs = {}
for name, ticker in target_stocks.items():
    df = stock.get_market_ohlcv_by_date(start_date, end_date, ticker)
    df["MA5"]  = df["종가"].rolling(window=5).mean()
    df["MA20"] = df["종가"].rolling(window=20).mean()
    df["MA60"] = df["종가"].rolling(window=60).mean()
    dfs[name] = df
```

**흔한 실수**
- 한 df에만 MA 계산하고 `dfs`에 같은 df 3번 넣기 → 세 종목 데이터가 똑같아짐.
- 반드시 반복문 **안에서** 매번 새 df를 받아야 한다.
- MA 컬럼 추가는 `dfs[name] = df` **전**이든 **후**든 관계없다 (같은 객체 참조).

</details>

---

## Q10. Candlestick + MA 라인 차트

<details>
<summary><b>💡 1차 힌트</b></summary>

- `go.Candlestick(x=, open=, high=, low=, close=)` — OHLC 매핑 필요
- `go.Scatter(x=, y=, name=)` — MA당 한 개씩 3개
- 모두 `go.Figure(data=[...])`의 리스트에 넣는다

</details>

<details>
<summary><b>📖 2차 전체 설명</b></summary>

```python
import plotly.graph_objects as go
df = dfs["삼성전자"]

fig = go.Figure(data=[
    go.Candlestick(
        x=df.index,
        open=df["시가"], high=df["고가"],
        low=df["저가"], close=df["종가"],
        name="캔들",
    ),
    go.Scatter(x=df.index, y=df["MA5"],  name="MA5"),
    go.Scatter(x=df.index, y=df["MA20"], name="MA20"),
    go.Scatter(x=df.index, y=df["MA60"], name="MA60"),
])
fig.update_layout(
    title="삼성전자 — 1년 주가 & 이평",
    xaxis_rangeslider_visible=False,
    template="plotly_dark",
)
fig.show()
```

**포인트**
- `x`는 모두 **같은 인덱스**(날짜). 캔들과 라인이 시간축을 공유해야 겹쳐 그려진다.
- `xaxis_rangeslider_visible=False`가 없으면 차트 아래에 미니맵이 붙는다 — 기호.
- MA60은 앞 59일이 NaN이지만 plotly가 알아서 빈 구간으로 처리.

</details>

---

## Q11. 차트 이미지 저장

<details>
<summary><b>💡 1차 힌트</b></summary>

- 한 줄이다: `fig.write_image("chart_test.png", engine="kaleido")`.
- `kaleido` 패키지가 깔려 있어야 한다 (사전 설치 셀에서 설치됨).

</details>

<details>
<summary><b>📖 2차 전체 설명</b></summary>

```python
fig.write_image("chart_test.png", width=1200, height=700, scale=2, engine="kaleido")
```

**파라미터**
- `width/height`: 픽셀 크기.
- `scale=2`: 해상도 2배. AI Vision이 세밀한 선(MA)을 더 잘 읽게 하려고 올린다.
- `engine="kaleido"`: Plotly를 정적 이미지로 바꾸는 백엔드. 명시 안 하면 경고 뜰 수 있다.

**에러 시**
- `ValueError: Kaleido not installed` → `!pip install kaleido==0.2.1 -q` 다시 실행.
- 0.2.1로 고정하는 이유: 최신 버전에서 Colab 호환 문제가 간헐적으로 있다.

</details>

---

## Q12. base64 인코딩 함수

<details>
<summary><b>💡 1차 힌트</b></summary>

- 파일을 **바이너리 모드**로 열기: `open(path, "rb")`
- `base64.b64encode(bytes)` → bytes 반환 → `.decode("utf-8")`로 문자열 변환

</details>

<details>
<summary><b>📖 2차 전체 설명</b></summary>

```python
def encode_image(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

img_b64 = encode_image("chart_test.png")
```

**왜 base64인가**
- OpenAI API는 JSON으로 요청을 받는다. JSON에 이진 바이트를 직접 못 넣는다.
- base64는 이진 → ASCII 문자열 변환 방식. 크기가 약 33% 커지지만 JSON에 안전하게 실린다.
- 나중에 `"data:image/png;base64,{img_b64}"` 형태로 API에 전달.

</details>

---

## Q13. Vision API 호출

<details>
<summary><b>💡 1차 힌트</b></summary>

- user content가 **문자열이 아니라 리스트**다.
- 리스트 요소 2개:
	1. `{"type": "text", "text": "..."}`
	2. `{"type": "image_url", "image_url": {"url": "data:image/png;base64,{img_b64}"}}`

</details>

<details>
<summary><b>📖 2차 전체 설명</b></summary>

```python
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {"role": "user", "content": [
            {"type": "text",
             "text": "이 차트는 삼성전자의 최근 1년 일봉이다. 이평선 배열을 중심으로 분석하라."},
            {"type": "image_url",
             "image_url": {"url": f"data:image/png;base64,{img_b64}"}},
        ]},
    ],
    max_tokens=500,
    temperature=0.3,
)
ai_analysis = response.choices[0].message.content
print(ai_analysis)
```

**구조 포인트**
- **멀티모달 메시지**: `content`가 문자열이면 텍스트만, 리스트면 텍스트+이미지 혼합.
- `data:image/png;base64,` 접두사가 빠지면 `400 invalid_image_url`.
- `temperature=0.3`: 분석은 낮게. 0.0이면 결정적, 1.0 이상은 창의적/불안정.
- 응답은 `response.choices[0].message.content`에 문자열로 들어 있다.

</details>
