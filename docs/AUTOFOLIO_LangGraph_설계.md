# Autofolio LangGraph 설계

**문서 버전:** 0.7 (초안)  
**목적:** Phase 1·2·3 오케스트레이션을 LangGraph로 설계. 1~2주 공통 설계 산출물.

---

## 1. 개요

| # | 그래프 | Phase | 입력 | 출력 |
|---|--------|-------|------|------|
| 1 | **포트폴리오 생성** | 1 | User 프로필, 에셋 (RAPTOR·Asset 결과) | 포트폴리오(웹/구조화) |
| 2 | **전략 수립** | 2 | **문항**(자소서 문항), 공고(파싱), User 에셋 | 문항 유형, 매칭 에셋, Gap, 전략 JSON |
| 3 | **Writer** | 3 | 전략, 에셋, 합격 샘플(Retrieval), 문항 | 자소서 초안 |
| 4 | **Inspector** | 3 | 초안, 전략, 에셋, (선택) 유저 수정본 | 보완 제안, Human-in-the-loop |

- **문항**은 자소서 문항(채용처가 낸 질문)으로, **2번 전략 수립·3번 Writer**에서만 사용. 1번 포트폴리오 생성은 문항 없음.
- **전략 수립**은 별도 API로 노출하지 않음. 자소서 초안(draft) 요청 시 내부에서 전략 수립 그래프를 호출한 뒤 Writer로 이어지는 구조.
- Job Fit는 그래프 없이 단일 API(User DB 프로필·임베딩 vs 공고 파싱 API 반환값 비교 → 점수)로 처리.

---

## 2. 포트폴리오 생성 그래프 (1번)

**용도:** User 프로필·에셋(RAPTOR·Asset 결과) → STAR 문장 생성 → Self-Consistency 검증 → 포트폴리오 생성. **문항 미사용.**

### 2.1 노드·엣지 (초안)

```
[START] → load_profile → build_star_sentence → self_consistency ──(통과)──→ build_portfolio → [END]
                                    ↑                │
                                    │                └──(실패 & retry < N)──→ build_star_sentence (피드백 반영 재생성)
                                    │                └──(실패 & retry ≥ N)──→ __fallback__ 또는 build_portfolio
                                    └────────────────────────────────────────── consistency_feedback 전달
```

| 노드 | 역할 | 입출력(State) |
|------|------|----------------|
| `load_profile` | User 프로필·에셋 로드 (P1 API 또는 DB) | 입력: `user_id` / 출력: `profile`, `assets` |
| `build_star_sentence` | 프로필·에셋 → STAR 성과 문장 후보 생성. **재진입 시** `consistency_feedback`를 입력으로 받아, 실패한 문장·구간만 보정하거나 피드백 반영해 재생성. | 입력: `profile`, `assets`, (재진입 시) `consistency_feedback` / 출력: `star` |
| `self_consistency` | **환각 체크** + **STAR 충실도 평가**. 실패 시 **어디가 문제인지** 구체적으로 State에 기록해 재생성 시 참고되도록 함. | 입력: `star`, `profile`, `assets` / 출력: `is_hallucination`, `is_star`, (실패 시) `consistency_feedback` |
| `build_portfolio` | 검증된 STAR·프로필·에셋 → 포트폴리오 | 입력: `star`, `profile`, `assets` / 출력: `portfolio` |

**재진입 시 달라지는 점**
- `self_consistency`가 실패 시 **`consistency_feedback`**를 State에 채움. 예: `{ "hallucination": [ { "sentence_id": 2, "reason": "프로필에 없는 기술 스택 언급" } ], "star_fidelity": [ { "sentence_id": 1, "missing": ["Result"], "suggestion": "결과 수치·영향 추가" } ] }`.
- `build_star_sentence`는 **첫 진입**이면 `profile`+`assets`만 사용, **재진입**이면 `consistency_feedback`를 함께 받아 해당 문장만 재생성하거나 프롬프트에 “다음 지적 반영” 형태로 넣어 결과가 달라지도록 함.

**Self-Consistency 상세**
- **환각 체크:** 생성된 STAR 문장이 프로필·에셋에 근거한지 검사. 실패 시 문장 ID·근거 없는 내용·이유를 `consistency_feedback.hallucination`에 기록.
- **STAR 충실도:** 각 문장의 S/T/A/R 충족 여부 평가. 미충족 시 문장 ID·부족 요소·보완 제안을 `consistency_feedback.star_fidelity`에 기록.
- **재시도 상한:** `star_retry_count >= max_star_retries`이면 재생성 대신 `__fallback__` 또는 검증 없이 `build_portfolio`로 진행(정책 선택).

### 2.2 State (초안)

```python
class PortfolioState(TypedDict, total=False):
    user_id: str
    profile: dict
    assets: list
    star: list                 # build_star_sentence 출력 (STAR 성과 문장 목록)
    is_hallucination: bool     # self_consistency 환각 체크 통과 여부
    is_star: bool              # self_consistency STAR 충실도 통과 여부
    star_retry_count: int      # build_star_sentence 재진입 횟수
    portfolio: dict | str
    consistency_feedback: dict  # 검증 실패 시 재생성용: { "hallucination": [...], "star_fidelity": [...] }
```

---

## 3. 전략 수립 그래프 (2번)

**용도:** **문항**(자소서 문항) + 공고 + 에셋 → 문항 유형 분류, 매칭 에셋 선정, Gap 분석, 전략 JSON 생성.  
**노출:** 별도 API 없음. 자소서 초안(draft) 요청 시 내부에서 이 그래프를 호출한 뒤 Writer로 이어짐.

### 3.1 노드·엣지

```
[START] → classify_question → select_assets → gap_analysis → build_strategy → [END]
                ↓ (에러 시)              ↓                        ↓
            __fallback__ 또는 종료
```

| 노드 | 역할 | 입출력(State) |
|------|------|----------------|
| `classify_question` | 문항 유형 분류 (동기/역량/협업/문제해결 등) | 입력: `question`, `job_parsed` / 출력: State에 `question_type` 등 반영 |
| `select_assets` | 문항·공고에 맞는 에셋 조회 (P1 또는 내부 API) | 입력: `user_profile_id`, `job_parsed`, `question` / 출력: `assets` |
| `gap_analysis` | 부족 역량·Gap 분석 | 입력: `assets`, `job_parsed` / 출력: `gaps` |
| `build_strategy` | 전략 JSON 조립 (문항 유형, 메인/보조 에셋, Gap) | 출력: `strategy` |

### 3.2 State (초안)

```python
# TypedDict 예시
class StrategyState(TypedDict, total=False):
    question: str
    job_parsed: dict       # 채용 공고 파싱 결과
    user_profile_id: str
    question_type: str
    assets: list
    gaps: list
    strategy: dict         # 최종 전략 JSON
    error: str
```

### 3.3 호출 API

- (선택) 에셋 조회: P1 User 프로필/에셋 API 또는 내부 서비스.

### 3.4 (옵션) 문항별 멀티에이전트

**아이디어:** 자소서 문항이 여러 개일 때, **문항별로 전략 수립 서브그래프(에이전트)를 병렬** 실행.

- **장점:** 문항 간 독립 처리 → 병렬화로 지연 감소, 문항 수가 많아도 확장 용이. 문항별 State 분리로 에러 격리.
- **구조:** 상위 그래프에서 `questions: list[str]` 수신 → 각 `question`마다 동일한 전략 수립 플로우(classify → select_assets → gap_analysis → build_strategy)를 **별도 에이전트/서브그래프**로 실행 → 결과를 `strategies: list[dict]`로 수집.
- **공유 컨텍스트:** `job_parsed`, `user_profile_id`(또는 `user_id`)는 모든 문항 에이전트에 동일하게 전달.
- **고려:** API/LLM 호출 수 증가(문항 수 × 1). 동시 실행 수 제한(rate limit, 비용) 있으면 문항 단위 스로틀링 또는 순차 처리 옵션 두는 것이 좋음.

```
[START] → (questions 분배) → [에이전트_문항1] → strategy_1 ─┐
                         → [에이전트_문항2] → strategy_2 ─┼→ aggregate_strategies → [END]
                         → [에이전트_문항3] → strategy_3 ─┘
```

---

## 4. Writer 그래프 (3번)

**용도:** 전략 + 에셋 + 합격 자소서 샘플 → 자소서 초안 생성.

### 4.1 노드·엣지

```
[START] → load_context → retrieve_samples → generate_draft → format_output → [END]
                              ↑
                    합격 자소서 검색 모듈 호출 (별도 API 아님)
```

| 노드 | 역할 | 입출력(State) |
|------|------|----------------|
| `load_context` | 전략·에셋·문항 로드, State 채우기 | 입력: `strategy`, `assets`, `question` |
| `retrieve_samples` | **합격 자소서 검색 모듈** 호출 (문항/회사/키워드) — 내부 모듈, 대외 API 아님 | 입력: `question`, (선택) `job_parsed` / 출력: `samples` |
| `generate_draft` | LLM으로 초안 생성 (전략+에셋+샘플 참고) | 출력: `draft` |
| `format_output` | 글자수·형식 정리 | 출력: `draft` 최종 |

### 4.2 State (초안)

```python
class WriterState(TypedDict, total=False):
    strategy: dict
    assets: list
    question: str
    samples: list          # 합격 자소서 검색 모듈 결과
    draft: str
    messages: list         # (선택) 대화 이력
```

### 4.3 호출 모듈 (API 아님)

- **합격 자소서 검색 모듈**: 문항/회사/연도/키워드 → 유사 합격 자소서 목록.  
  Writer 그래프 내부에서 **모듈 호출**로 사용. 대외 REST API로 노출할 필요 없음.

---

## 5. Inspector 그래프 (4번)

**용도:** 초안 + 전략 + 에셋 → 보완 제안. 유저 수정 후 재첨삭(Human-in-the-loop).

### 5.1 노드·엣지

```
[START] → load_draft → analyze → suggest → [Human 입력 대기]
                                              ↓
                                    re_inspect (round < N) → analyze → ...
                                              ↓
                                    end (round >= N 또는 유저 종료)
```

| 노드 | 역할 | 입출력(State) |
|------|------|----------------|
| `load_draft` | 초안·전략·에셋 로드 | 입력: `draft`, `strategy`, `assets` |
| `analyze` | LLM으로 보완점 분석 | 출력: `suggestions` |
| `suggest` | 제안 문장/리스트 반환 (API 응답) | 출력: `suggestions` |
| (Human) | 유저가 초안 수정 | State에 `user_edited` 반영 |
| `re_inspect` | 수정본으로 다시 analyze (round 증가) | 조건: `round < max_rounds` |

### 5.2 State (초안)

```python
class InspectorState(TypedDict, total=False):
    draft: str
    strategy: dict
    assets: list
    suggestions: list
    user_edited: str       # 유저가 수정한 초안
    round: int
```

### 5.3 조건 엣지

- `suggest` 이후: Human 입력 대기 → `round < N` 이면 `re_inspect`, 아니면 `end`.

---

## 6. 그래프가 호출하는 API·모듈 정리

| 호출 주체 | 대상 | 제공 | 비고 |
|-----------|------|------|------|
| Writer `retrieve_samples` | 합격 자소서 검색 **모듈** (문항/회사/연도/키워드) | 내부 모듈 | 별도 API 노출 없음 |
| 전략 `select_assets` | User 에셋/프로필 조회 | P1 API 또는 DB | (선택) |
| 포트폴리오 `load_profile` | User 프로필·에셋 조회 | P1 API 또는 DB | (선택) |

---

## 7. 미정·토의 항목

- [ ] State 필드명·타입 최종화 (Pydantic vs TypedDict)
- [ ] 에러/재시도: `__fallback__` 노드 동작, 재시도 횟수
- [ ] Inspector `max_rounds` 기본값
- [ ] LangGraph 버전·패키지 (langgraph, langgraph-core 등)
- [ ] 그래프 컴파일 후 FastAPI 엔드포인트 노출 방식 (invoke/stream)

---

## 8. 문서 이력

- 0.1: LangGraph 설계 초안. 전략/Writer/Inspector 노드·엣지·State, API 호출 목록.
- 0.2: 1번을 **포트폴리오 생성** 그래프로 추가(문항 미사용). 2번 전략 수립에서만 문항 사용. 그래프 4개로 정리.
- 0.3: 1번 그래프 플로우를 `load_profile → build_star_sentence → self_consistency → build_portfolio`로 변경. `self_consistency`에 환각 체크·STAR 충실도 평가 로직 추가.
- 0.4: 검증 실패 시 재진입 시 **consistency_feedback** 전달, `build_star_sentence`가 피드백 반영해 재생성하도록 명시. State에 `consistency_feedback`, `star_retry_count` 추가, 재시도 상한으로 fallback 분기 명시.
- 0.5: 1번 그래프 State 스키마 정리 — `user_id`, `profile`, `assets`, `star`, `is_hallucination`, `is_star`, `star_retry_count`, `portfolio`, `consistency_feedback`.
- 0.6: 2번 그래프에 문항별 멀티에이전트 옵션(3.4) 추가 — 문항별 병렬 전략 수립, 공유 컨텍스트, aggregate 정리.
- 0.7: 전략 수립 별도 API 없음(draft 시 내부 호출) 명시. Job Fit = User DB vs 공고 파싱 API 반환값. 합격 자소서 검색을 API → 모듈 호출로 변경.
