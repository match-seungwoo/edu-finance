# 1주차 — AI 차트 리더(Chart Reader) 만들기

> **"AI에게 내 주식 차트를 읽히고, 분석을 받아보자"**

## 🎯 학습 목표

90분 후, 학생은 다음을 할 수 있게 됩니다.

1. `pykrx`로 국내 주식의 1년치 OHLCV 데이터를 가져온다.
2. `plotly`로 이동평균선이 포함된 인터랙티브 캔들차트를 그린다.
3. 그 차트 이미지를 GPT-4o Vision에게 전달해 "퀀트 애널리스트 의견"을 받아낸다.
4. 결과(데이터프레임 + AI 코멘트)를 파일로 저장한다.

## 🏆 최종 결과물

- **내가 고른 테마의 대장주 2~3개**를 비교 분석한 Colab 노트북
- `chart.png` (Plotly 차트 이미지)
- `analysis_YYYYMMDD.csv` (다음 주 포트폴리오 구성에 쓸 재료)
- AI가 생성한 3줄 투자 코멘트

## 🧰 준비물

| 항목 | 설명 |
|---|---|
| Google 계정 | Colab 접속용 |
| OpenAI API Key | [platform.openai.com](https://platform.openai.com) → API keys |
| 테마 선택 | 반도체 / 2차전지 / 미국 테크 중 하나 |

### 💳 API Key 주의

- 키는 절대 노트북에 하드코딩하지 않는다. `from google.colab import userdata`로 Colab Secrets에 저장한다.
- GPT-4o Vision 1회 호출 비용은 대략 $0.01~0.02 수준. 실습 전체가 $1 미만이다.

## 📂 파일 구성

| 파일 | 용도 |
|---|---|
| `lecture_notes.md` | 강사가 들고 진행하는 90분 스크립트 |
| `student_notebook.ipynb` | 학생이 Colab에 업로드해서 실습하는 노트북 |
| `instructor_guide.md` | 자주 나오는 질문, 막히는 지점, 확장 아이디어 |
| `homework.md` | 다음 주까지 해올 과제 |

## 🔗 전체 커리큘럼 내 위치

```
[1주차] 차트 분석  →  [2주차] 포트폴리오 비중  →  [3주차] DB 저장
  ↓
AI가 내뱉은 "의견"이 3주차에 SQLite에 쌓이기 시작 → 4주차 스트레스 테스트의 재료
  ↓
7주차에 pykrx 로직이 FastAPI /api/chart 엔드포인트로 승격됨
```

1주차에 작성한 코드의 **모든 줄**이 이후 주차에서 재활용됩니다. 버리는 코드 없음.
