# Program 4 — 외교 성명문 문화코드 정량 분석

> 같은 사건을 두고 **UN · 한국 · 중국 · France Diplomatie** 가 *어떻게 다른 단어로* 말하는가를
> 실제 수집한 외교 성명문 데이터로 정량 분석하는 6세션 + 과제 교육 프로그램.

학생 주도 데이터 저널리즘 프로젝트. 외교 인턴십 경험·한중프 3개 언어 능력·저널리즘/영화 배경을
가진 학생이 **도메인 지식을 분석 차원 설계와 결과 검증에 직접 투입**하도록 설계되었다.

---

## 1. 무엇을 분석하나 — 3종 코퍼스 (실제 수집)

| 주제군 | 사건 수 | 기간 | 외교 당사자성 |
|---|---|---|---|
| 🟦 우크라이나 전쟁 | 12 | 2022-02~ | **높음** (직접 이해당사자) |
| 🟥 가자 / 이스라엘-팔레스타인 | 10 | 2023-10~ | **높음** |
| 🟩 AI 거버넌스 | 8 | 2023~ | **낮음** ("한 발 떨어진" 글로벌 거버넌스) |

**30개 사건 × 4개 소스**의 공식 성명문을 4개 정부/국제기구 사이트에서 **실제로 스크래핑**했다.

### 수집 결과 (data/backup/)
- **raw 195건 → 정제 183건**, 30/30 사건 커버
- 소스별: UN 44 · 한국(KR) 26 · 중국(CN) 60 · 프랑스(FR) 65
- 모든 문서 `collected_via = live_scrape` (실제 수집). **백업(JSON/CSV) 동봉** → 라이브 스크래핑이 막혀도 노트북이 항상 동작.

> 데이터 출처: `press.un.org`(UN), `mofa.go.kr/eng`(한국), `fmprc.gov.cn/eng` 정례 브리핑(중국),
> `diplomatie.gouv.fr/en`(프랑스). UN/프랑스 과거분은 Internet Archive raw 스냅샷으로 복구.
> 재수집 코드는 `scrapers/` 에 전부 공개 (재현성).

---

## 2. 6개 분석 차원

| # | 차원 | 무엇을 재나 | 방법 |
|---|---|---|---|
| 1 | **Directness Index** | 능동/수동 비율 + 우회표현 ("Russia attacked" vs "civilians were attacked") | spaCy |
| 2 | **Verb Strength Ladder** | note<acknowledge<regret<concern<deplore<condemn<demand | spaCy lemma |
| 3 | **Subject Pattern** | 주어 분포 (we / 국가 / 국제사회 / 모든 당사자) | spaCy |
| 4 | **Mutuality Index** | 양면적 표현 밀도 (mutual, both sides, all parties...) | 사전 |
| 5 | **Hedging Density** | 완곡/유보어 밀도 (may, appears to, possibly...) | 사전 |
| 6 | **Silence Map** | 어느 소스가 어느 사건에 *침묵*했나 | 커버리지 |

**Hybrid 방법론** — "계산은 코드(결정론), 의미 해석은 LLM(Claude), 판단은 인간."
규칙 기반 측정과 Claude 의미 분석을 교차 검증한다.

---

## 3. 세션 구성 (코퍼스 3종 = 3주제)

**주제1 · 우크라이나 (s1~s4)** — 전체 파이프라인을 깊게 훈련
| 세션 | 내용 | 노트북 |
|---|---|---|
| **s1** | 수집·정제 — 데이터 존재 확인, 스키마, 정제 철학, 침묵 지도 | `session1/` |
| **s2** | 구조 분석 (spaCy) — directness · verb strength · subject 직접 구현 | `session2/` |
| **s3** | 의미 분석 (Claude) — mutuality · hedging · framing, hybrid 교차검증 | `session3/` |
| **s4** | 검증 + 시각화 — 6차원 종합, 교차언어 spot check, **측정 타당성 비판** | `session4/` |

**주제2 · 가자 (s5~s6)** — 압축 재적용 + 시계열
| 세션 | 내용 | 노트북 |
|---|---|---|
| **s5** | 파이프라인 빠른 재적용 + 우크라이나 vs 가자 비교 (Q2) | `session5/` |
| **s6** | 시계열 입장 변화 (Q3) + Visual Essay 산출물 + 종합 | `session6/` |

**주제3 · AI 거버넌스 (과제)** — 혼자 처음부터 끝까지
| 산출물 | 내용 |
|---|---|
| `homework/ai_governance_assignment.ipynb` | 학생용 (빈칸 + 서술형) |
| `homework/ai_governance_answerkey.ipynb` | 정답지 (완성본 + 강사 메모) |
| `homework/README.md` | 과제 안내 + 채점 루브릭(100점) |

각 세션은 **단계별 실습 노트북**(`sessionN.ipynb`) + **강사 강의 스크립트**(`lecture_notes.md`)로 구성.
입문자 대상 풀 스캐폴딩: 마크다운 설명 → 코드 → `# TODO`/`# CHECK` + `<details>힌트`.

---

## 4. 핵심 발견 (실데이터 기준)

> 📄 연구 질문 **Q1·Q2·Q3에 대한 정식 답변**은 [`conclusion.md`](conclusion.md) 참고.


1. **🇨🇳 중국 외교언어 = 양면성.** Mutuality Index(1000단어당)에서 중국이 모든 주제에서 압도적 1위:
   우크라이나 CN 10.1 ≫ KR 7.2 > UN 3.7 > FR 1.1 / 가자 CN 11.2. "all parties · dialogue" 패턴이 실데이터로 재현.
2. **📏 "중국이 가장 강경하다"는 측정 착시였다 (s4 백미).** Verb Strength *최댓값*은 문서 길이와 강하게 상관
   (강도동사 개수 vs 길이 r=0.94). 중국 브리핑이 길어서 높게 나온 것. **1000단어당 밀도로 정규화하면 순위가 뒤집혀
   한국이 1위(8.45), 중국이 최하(3.37)** — "짧지만 직설적인" 한국. → *숫자를 믿기 전에 왜 그런지 의심하라.*
3. **🤫 한국의 선택적 침묵.** 한국은 ICC 영장·ICJ 명령·댐 파괴 같은 법적·기술적 변곡점엔 침묵하고,
   침공·1주년 같은 상징적 사건엔 말한다 (우크라이나·가자 공통 패턴).
4. **⏱ 일관성 vs 유연성 (Q3).** 시계열 분산 분석: UN이 가장 일관(분산 최소), 한국이 가장 유연(변동 최대).
5. **🌐 당사자성 가설 지지.** 저당사자성 주제(AI)는 고당사자성(전쟁) 대비 협력적 언어 ~2배,
   동사 강도 밀도 ~절반. 또 **프랑스는 AI 거버넌스에 자기 MFA 성명 트리에서 구조적으로 부재**(정상회의 별도 포털) — 그 자체가 침묵 지도의 발견.

---

## 5. 실행 방법

### Colab (권장)
1. 이 `program4` 폴더를 GitHub repo로 올리거나 Colab에 업로드.
2. 각 노트북 첫 셀(환경 설정)이 `data/backup/` 을 자동 탐색한다.
3. **API 키(s3, 선택):** Colab 좌측 🔑 → `ANTHROPIC_API_KEY` 등록.
   키가 없어도 s3는 `DEMO_MODE`(예시 결과)로 끝까지 돌아간다.

### 로컬 (Jupyter)
```bash
pip install spacy plotly anthropic pandas
python -m spacy download en_core_web_sm
# program4/ 에서 노트북 실행
```

### 데이터 재수집 (선택)
```bash
cd scrapers
python scrape_un.py && python scrape_kr.py && python scrape_cn.py && python scrape_fr.py
python build_corpus.py   # raw 병합 → backup
python clean_corpus.py   # 정제 → corpus_clean
```

---

## 6. 파일 맵

```
program4/
├── README.md                    이 문서
├── diplo_analysis.py            6개 차원 분석 툴킷 (s4부터 import)
├── nb.py                        노트북 빌더 헬퍼
├── _build_s*.py, _build_hw.py   노트북 재생성 스크립트 (program4 루트에서 실행)
├── scrapers/
│   ├── events.py                30개 사건 + 스키마 정의 (single source of truth)
│   ├── scrape_{un,kr,cn,fr}.py  소스별 실제 스크래퍼
│   ├── build_corpus.py          병합 + 백업 생성
│   └── clean_corpus.py          정제 패스
├── data/
│   ├── raw/{UN,KR,CN,FR}.json   소스별 원수집
│   └── backup/                  ★ 분석용 백업 (corpus_clean.json/csv, coverage, manifest)
├── session1~6/
│   ├── sessionN.ipynb           단계별 실습 노트북
│   └── lecture_notes.md         강사 강의 스크립트
└── homework/
    ├── ai_governance_assignment.ipynb   과제(빈칸)
    ├── ai_governance_answerkey.ipynb    정답지
    └── README.md                        채점 루브릭
```

---

## 7. 정직성 / 한계

- 모든 측정은 **영문 텍스트** 기준(소스가 영문판 제공). 원어 뉘앙스 검증은 학생의 한중프 능력으로 spot check(s4).
- 규칙·사전 기반 측정은 외교 언어의 미묘함을 일부 놓친다 → Claude 의미 분석으로 보완하되 **교차검증** 필수.
- 일부 사건·소스는 표본이 작다(특히 AI 거버넌스 n=21, 프랑스 AI=0). 결론은 *경향*으로만 진술하고 과일반화 금지.
- 중국 정례 브리핑은 주제 문단만 추출했다 → 맥락 손실 가능. 정제 규칙은 `clean_corpus.py` 에 공개.

---

## 8. 분석 프레임워크 평가 및 확장 로드맵

### 8.1 현재 프레임워크는 적절한가 — 평가

**적절하다, 목적에 대해서는.** 6차원은 (1) 이론·도메인 주도라 해석 가능하고, (2) 규칙+LLM hybrid로 검증 가능하며, (3) 외교 직관("concern vs grave concern")을 측정으로 옮긴 것이 강점이다. 학생 주도 프로젝트로서 과하지도 부족하지도 않다.

**다만 구조적 약점 3가지가 있다:**
- **표면적(bag-of-words).** 사전 카운트는 *누구에게* 적용된 단어인지 모른다. "Russia and Ukraine should both restrain"의 "both"와, 중국의 일반 협력어 "cooperation"을 같은 mutuality로 센다. **부정(negation)도 못 잡는다** ("no mutual interest"도 +1).
- **영문 단일언어.** 번역이 뉘앙스를 평탄화한다. 정작 학생의 최대 자산(한·중·프)이 측정에 들어가 있지 않다.
- **귀속(attribution) 부재.** 직설성은 능동/수동까지만 본다. 외교의 핵심 변수인 **"누구를 가해자로 지목했는가"** 가 측정 차원으로 없다.

### 8.2 추가하면 좋을 분석 차원 (프레임워크)

| 차원 | 무엇을 잡나 | 신호 | 난이도 |
|---|---|---|---|
| ⭐ **Event Naming / 완곡명명** | 사건을 뭐라 *부르나*: invasion/war/aggression vs conflict/crisis/situation | 매우 높음 | 낮음 |
| ⭐ **Blame Attribution / 귀속** | 가해 행위의 주체를 누구로 명시(named/implied/none) | 핵심 | 중간 |
| ⭐ **Targeted Sentiment / 대상별 태도** | 한 성명 안에서 러시아 vs 우크라이나에 대한 감정 비대칭 | 높음 | 중간 |
| **Deontic Modality / 당위강도** | call upon < urge < demand < must — 행동 촉구의 강도 | 높음 | 낮음 |
| **Specificity / 구체성** | 숫자·날짜·지명 vs 추상어 (모호함 = 회피 신호) | 중간 | 낮음 |
| **Moral Framing** | 피해·공정·주권 등 가치 프레임 (Moral Foundations) | 중간 | 중간 |

> **가장 추천: Event Naming.** 노력 대비 신호가 압도적이다. "중국은 conflict/crisis, 프랑스는 aggression/invasion"이라는 가설은 한 단어 카운트로 정량화되고, 6차원 전체를 한 줄로 요약하는 헤드라인이 된다.

### 8.3 추가하면 좋을 NLP 기법 (기존 차원 강화)

| 기법 | 어떤 차원을 고치나 | ROI |
|---|---|---|
| ⭐ **부정·범위 처리 (negation scope)** | mutuality/hedging 정확도 — 오탐 제거 | 높음·쉬움 |
| ⭐ **의존구문 SVO 추출 (+ coreference)** | 직설성·주어·**귀속**을 "누가-무엇을-누구에게" 그래프로 격상 | 높음·중간 |
| ⭐ **원어 분석 (cross-lingual)** | 영문 결과를 한·중·프 원문(stanza/multilingual spaCy)으로 재측정·대조 | **최고 (프로젝트 신뢰성의 결정타)** |
| **임베딩 사전 확장** | mutuality/hedging 사전을 임베딩 최근접어로 반자동 확장(패러프레이즈 포착) | 높음·중간 |
| **임베딩 소스간 거리** | Q1의 "차이"를 *문장 임베딩 거리* 단일 지표로 정량화 (같은 사건, 소스쌍 코사인 거리) | 높음·중간 |
| **토픽 모델링 (BERTopic)** | "framing" — 같은 사건에서 소스별로 *무엇을 강조*하나(인도주의 vs 주권 vs 법) | 중간 |
| **Keyness (log-likelihood)** | TF-IDF보다 정확한 소스간 변별어 비교 (코퍼스 언어학 표준) | 중간·쉬움 |
| **대상별 감정 (ABSA/Claude)** | Targeted Sentiment 차원 구현 | 중간 |

### 8.4 권장 — 실제로 추가할 Top 3

연구 가치와 학생 자산(트릴링구얼)을 함께 고려하면:

1. **원어 분석(cross-lingual) 검증 모듈** — 한·중·프 원문에서 핵심 차원(상호성·동사강도·event naming)을 재측정해 영문 결과와 대조. *이것이 이 프로젝트를 "또 하나의 텍스트 분석"에서 "신뢰할 수 있는 연구"로 바꾼다.*
2. **Event Naming 차원** — 쉽고 신호 강함. 즉시 헤드라인.
3. **SVO + 부정 처리로 Blame Attribution 차원 신설** — 직설성을 "누구를 가해자로 지목했나"로 격상.

### 8.5 하지 말 것 (과적합 경계)

- 6차원을 **딥러닝 블랙박스로 대체하지 말 것** — 해석가능성이 이 프로젝트의 정체성. 추가 기법은 항상 *기존 해석가능 지표를 보강*하는 방향으로.
- 토픽모델링·임베딩은 **탐색/검증 보조**로만, 메인 결론 근거로 단독 사용 금지(표본 작음).
