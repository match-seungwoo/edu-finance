# 🤖 AI Quant-Mate Session 2 실습 템플릿
# 주제: 지능형 포트폴리오 비중 관리 및 리스크 분석

import pandas as pd
import numpy as np

# 1. 가상 데이터 생성 (실습용)
# 학생들은 나중에 이 부분을 본인의 CSV 파일 로드 코드로 바꿉니다.
data = {
    "ticker": ["NVDA", "AMD", "TSM", "AAPL", "MSFT"],
    "name": ["NVIDIA", "AMD", "TSMC", "Apple", "Microsoft"],
    "quantity": [10, 15, 20, 5, 5],
    "avg_price": [800, 120, 100, 170, 400],
    "current_price": [950, 140, 110, 190, 420],
    "sector": ["AI/반도체", "AI/반도체", "반도체", "IT/기기", "IT/소프트웨어"]
}

df = pd.DataFrame(data)
print("--- 원본 데이터 ---")
print(df.head())

# 2. 평가금액 계산
# 평가금액(Value) = 수량(Quantity) * 현재가(Current Price)
df["value"] = df["quantity"] * df["current_price"]

# 3. 총 자산 합계
total_value = df["value"].sum()

# 4. 종목별 비중 계산
df["weight"] = df["value"] / total_value

print("\n--- 비중 계산 결과 ---")
print(df[["name", "value", "weight"]])

# 5. 섹터별 집계 (Groupby 활용)
# 섹터별로 비중을 합산하여 쏠림 현상을 확인합니다.
sector_weights = (
    df.groupby("sector")["weight"]
    .sum()
    .reset_index()
    .sort_values(by="weight", ascending=False)
)

print("\n--- 섹터별 비중 현황 ---")
print(sector_weights)

# 6. HHI(집중도 지표) 계산
# HHI = 각 섹터 비중의 제곱의 합
hhi = (sector_weights["weight"] ** 2).sum()

# 7. 결과 대시보드 출력
print("\n" + "="*40)
print(f"📊 포트폴리오 분석 리포트")
print("="*40)
print(f"💰 총 자산 가치: ${total_value:,.0f}")
print(f"🔍 섹터 집중도(HHI): {hhi:.3f}")

# HHI 기준에 따른 간단 비평
if hhi > 0.25:
    status = "⚠️ 고위험 (매우 집중됨)"
elif hhi > 0.15:
    status = "⚖️ 주의 (집중됨)"
else:
    status = "✅ 양호 (잘 분산됨)"
print(f"🛡️ 리스크 상태: {status}")

print("\n📈 상세 섹터 비중:")
for _, row in sector_weights.iterrows():
    print(f"- {row['sector']}: {row['weight']:.1%}")

# 8. AI 비평을 위한 프롬프트 생성용 데이터
analysis_summary = {
    "sector_data": sector_weights.to_dict(orient="records"),
    "hhi_score": round(hhi, 3)
}
print("\n--- AI에게 전달할 데이터 ---")
print(analysis_summary)