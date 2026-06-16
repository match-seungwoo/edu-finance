# 1주차 강의 노트 (90분)

> 강사가 화면을 공유하며 따라가는 스크립트. 학생 Colab 노트북과 1:1 대응.

---

## 🎬 오프닝 (5분)

### 한 문장 훅

> "오늘 우리는 **AI에게 주식 차트를 보여주고 '이거 살까요?'라고 물어볼 겁니다.**
> 90분 뒤에는 여러분도 AI 퀀트 애널리스트 하나 옆구리에 끼고 집에 갑니다."

### 오늘 만들 것 시연 (3분)

- 완성된 노트북을 먼저 한 번 처음부터 끝까지 실행해서 보여준다.
- 학생이 "어? 저거 되네?" 하게 만드는 게 포인트.
- 특히 **AI가 차트를 보고 한글로 분석 내뱉는 장면**에서 멈춰서 반응 유도.

### 테마 선택 (2분)

학생에게 택 1 시킨다. 선택한 테마로 끝까지 간다.

| 테마 | 종목 (2~3개) | 티커 |
|---|---|---|
| 🔥 반도체 | 삼성전자 / SK하이닉스 / 한미반도체 | 005930 / 000660 / 042700 |
| 🔋 2차전지 | LG에너지솔루션 / 에코프로 / POSCO홀딩스 | 373220 / 086520 / 005490 |
| 🇺🇸 미국 테크 | NVIDIA / Microsoft / Apple | (yfinance: NVDA / MSFT / AAPL) |

> 💡 **팁:** 미국 테크를 고른 학생은 `pykrx` 대신 `yfinance`로 빠진다. 코드 구조는 동일.

---

## 📍 Step 1 — 환경 구축 & 데이터 로드 (20분)

### 1-1. 라이브러리 설치 (2분)

```python
!pip install pykrx openai plotly kaleido -q
```

**설명 포인트:**
- `pykrx`: KRX(한국거래소)에서 OHLCV 긁어오는 비공식 SDK
- `plotly`: 캔들차트 그리는 시각화 라이브러리 (웹 친화적)
- `kaleido`: Plotly를 이미지로 저장할 때 필요 (이거 빼먹으면 뒤에서 고생)
- `openai`: Vision API 호출용

### 1-2. API Key 세팅 (3분)

```python
from google.colab import userdata
OPENAI_API_KEY = userdata.get('OPENAI_API_KEY')
```

**라이브 시연:**
1. Colab 왼쪽 🔑 아이콘 클릭 → "새 보안 비밀" → 이름 `OPENAI_API_KEY`
2. 값에 붙여넣고 "노트북 액세스" 토글 ON
3. `.get()`으로 불러오기

**왜 이렇게 하나:** GitHub에 실수로 올려도 키 안 샌다. 습관화 중요.

### 1-3. 데이터 가져오기 (10분)

```python
from pykrx import stock
from datetime import datetime, timedelta

# 오늘 기준 1년치
end = datetime.today().strftime("%Y%m%d")
start = (datetime.today() - timedelta(days=365)).strftime("%Y%m%d")

target_stocks = {
    "삼성전자": "005930",
    "SK하이닉스": "000660",
}

dfs = {}
for name, ticker in target_stocks.items():
    df = stock.get_market_ohlcv_by_date(start, end, ticker)
    dfs[name] = df

dfs["삼성전자"].tail()
```

**설명 포인트 (금융):**
- 컬럼: `시가 / 고가 / 저가 / 종가 / 거래량`
- **수정주가(Adjusted Price)**: `pykrx`의 기본 반환은 원주가. 액면분할·유상증자 같은 이벤트로 가격이 튀어 보일 수 있다.
  - "삼성전자 2018년 50:1 액면분할 전 주가가 265만원이었어요. 데이터로 보면 그날 주가가 95% 빠진 것처럼 보이는데 실제론 주주가 손해 본 게 아님."
  - 실습에서는 최근 1년만 보니까 큰 문제 없음. 2회차에서 `adjusted=True` 옵션 설명 예정.

### 1-4. 학생이 직접 실행 (5분)

- 학생이 본인 노트북에서 위 코드를 타이핑/복붙 후 실행.
- **체크 포인트:** `df.tail()` 결과가 화면에 뜨면 "Step 1 완료" 이모지 찍게.

---

## 📍 Step 2 — 전략의 시각화 (30분)

### 2-1. 이동평균선 계산 (5분)

```python
for name, df in dfs.items():
    df['MA5']  = df['종가'].rolling(window=5).mean()
    df['MA20'] = df['종가'].rolling(window=20).mean()
    df['MA60'] = df['종가'].rolling(window=60).mean()
```

**설명 포인트 (금융):**
- MA5 = 최근 5거래일 평균 종가 → "단기 추세"
- MA20 = 약 1개월 → "중기 추세"
- MA60 = 약 3개월 → "장기 추세"
- 왜 평균을 볼까? "하루 종가는 기분 따라 흔들려요. 평균은 흐름을 보여줘요."

### 2-2. Plotly 캔들스틱 차트 (15분)

```python
import plotly.graph_objects as go

name = "삼성전자"
df = dfs[name]

fig = go.Figure(data=[
    go.Candlestick(
        x=df.index,
        open=df['시가'], high=df['고가'],
        low=df['저가'], close=df['종가'],
        name='캔들'
    ),
    go.Scatter(x=df.index, y=df['MA5'],  line=dict(color='orange', width=1.2), name='MA5'),
    go.Scatter(x=df.index, y=df['MA20'], line=dict(color='royalblue', width=1.2), name='MA20'),
    go.Scatter(x=df.index, y=df['MA60'], line=dict(color='firebrick', width=1.2), name='MA60'),
])

fig.update_layout(
    title=f'{name} — 1년 주가 & 이동평균선',
    template='plotly_dark',
    xaxis_rangeslider_visible=False,
    height=600,
)
fig.show()
```

**시연 포인트:**
- 마우스를 캔들 위에 올리면 시/고/저/종가 툴팁 뜸 → "이게 matplotlib랑 다른 점"
- 오른쪽 위 아이콘으로 줌/팬/카메라 가능

### 2-3. 골든크로스 / 데드크로스 해석 (10분)

차트에서 MA5가 MA20을 뚫고 올라가는 지점을 손가락으로 가리키며:

> **골든크로스:** "단기 추세가 중기 추세를 위로 돌파 = 매수 에너지 응축"
> **데드크로스:** "단기 추세가 중기 추세를 아래로 뚫음 = 매도 압력"

**솔직한 면책:**
- "이게 100% 맞으면 다 부자 됐겠죠. **과거 패턴일 뿐**이고, 이걸 AI가 어떻게 받아들이는지 보는 게 오늘의 진짜 재미입니다."

---

## 📍 Step 3 — AI Vision 분석 (30분) 🌟

여기가 오늘의 하이라이트. 학생들 집중 끌어올리기.

### 3-1. 차트를 이미지로 저장 (3분)

```python
fig.write_image("chart.png", width=1200, height=700, scale=2)
```

**설명:** `kaleido`가 백엔드로 Plotly를 PNG로 렌더링. `scale=2` 주면 해상도 2배 → AI가 선 더 잘 본다.

### 3-2. 이미지 → base64 인코딩 (5분)

```python
import base64

def encode_image(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

image_b64 = encode_image("chart.png")
```

**설명:** OpenAI API는 이미지를 base64 텍스트로 받는다. URL도 가능하지만 로컬 파일은 인코딩 필수.

### 3-3. GPT-4o Vision 호출 (15분)

```python
from openai import OpenAI
client = OpenAI(api_key=OPENAI_API_KEY)

system_prompt = """
너는 월스트리트 15년차 헤지펀드 퀀트 애널리스트야.
차트의 이동평균선 배열과 캔들 패턴을 보고 분석해.
금융 전문 용어를 쓰되, 초보자도 이해할 수 있게 설명해.
반드시 다음 형식으로만 답해:

📊 현재 추세: (한 줄)
🎯 핵심 시그널: (골든크로스/데드크로스/정배열/역배열 등 1~2개)
💡 투자 의견: (매수 / 보유 / 매도 중 택 1 + 3줄 이내 근거)
"""

response = client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": [
            {"type": "text", "text": f"이 차트는 {name}의 최근 1년 주가야. 분석해줘."},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}}
        ]}
    ],
    max_tokens=500,
)

analysis = response.choices[0].message.content
print(analysis)
```

**실시간 반응 유도:**
- 실행 버튼 누르기 전에 "자, 여러분 AI가 뭐라고 할 것 같아요?" 한 번 물어보기
- 실행 후 출력 나오면 10초 정도 같이 읽으며 감탄

**설명 포인트 (AI):**
- `gpt-4o` 모델은 텍스트 + 이미지 동시 입력 가능 ("멀티모달")
- `system_prompt`가 AI의 **페르소나와 출력 형식**을 고정. 프롬프트 엔지니어링의 핵심.
- 응답 형식을 강제하지 않으면 매번 다른 구조로 나와서 나중에 파싱 지옥.

### 3-4. 종목별 반복 (7분)

```python
results = {}
for name, df in dfs.items():
    # 차트 그리기 → 이미지 저장 → AI 호출
    ...
    results[name] = analysis
    print(f"\n=== {name} ===\n{analysis}\n")
```

**학생 미션:** 본인 테마 종목 2~3개를 모두 분석해보고, AI 의견을 비교.

---

## 📍 Step 4 — 결과 저장 & 회고 (10분)

### 4-1. CSV 저장 (3분)

```python
import pandas as pd

summary = pd.DataFrame([
    {"종목": name, "현재가": dfs[name]['종가'].iloc[-1], "AI_의견": results[name]}
    for name in dfs
])
summary.to_csv(f"analysis_{end}.csv", index=False, encoding='utf-8-sig')
```

**왜 저장하나:**
- 2주차에 이 CSV를 읽어서 포트폴리오 비중 계산의 재료로 쓴다.
- "오늘 만든 게 다음 주 재료" → 연결성 강조.

### 4-2. 회고 (5분)

학생에게 물어보기:
1. "AI 의견 중 가장 납득 안 되는 게 뭐였어요?"
2. "차트의 어떤 부분을 AI가 놓친 것 같아요?"
3. "오늘 분석한 종목 중 실제로 돈 넣는다면?"

이 질문들은 **4주차 스트레스 테스트**로 연결됨. 미리 떡밥 깔기.

### 4-3. 다음 주 예고 (2분)

> "오늘 여러분은 종목 **하나하나**를 봤어요.
> 다음 주에는 이 종목들을 **어떤 비율로 섞어야** 잘 섞었다고 소문이 날지를 AI랑 같이 고민합니다."

---

## ⏱ 시간 관리 치트시트

| 구간 | 시간 | 누적 |
|---|---|---|
| 오프닝 & 테마 선택 | 5분 | 0:05 |
| Step 1 | 20분 | 0:25 |
| Step 2 | 30분 | 0:55 |
| Step 3 | 30분 | 1:25 |
| Step 4 & 회고 | 10분 | **1:35** |

> 5분 여유 있음. Step 3에서 학생들이 막히기 쉬우니 이 버퍼를 여기에 쓰게 됨.
