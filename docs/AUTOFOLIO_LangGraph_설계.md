# Autofolio LangGraph 설계

**문서 버전:** 1.5  
**목적:** Phase 1·2·3 오케스트레이션을 LangGraph로 설계. 1~2주 공통 설계 산출물.

---

## 1. 개요

| # | 그래프 | Phase | 입력 | 출력 |
|---|--------|-------|------|------|
| 1 | **포트폴리오 생성** | 1 | User 프로필, 에셋 (RAPTOR·Asset 결과) | 포트폴리오(웹/구조화) |
| 2 | **Writer** | 3 | user_id, 문항, 합격 샘플(Retrieval) → 유저 DB(에셋) | 자소서 초안 |
| 3 | **Inspector** | 3 | 초안, (선택) 유저 수정본 (에셋·합격 샘플은 load_draft에서 무조건 재조회) | 보완 제안, Human-in-the-loop |

- draft 시 Writer 그래프 내부에서 에셋 조회(load_assets) 수행.
- **전략 수립 그래프는 현재 범위에서 사용하지 않는다.**
- Job Fit는 그래프 없이 단일 API(User DB 프로필·임베딩 vs 공고 파싱 API 반환값 비교 → 점수)로 처리한다.

---

## 2. 포트폴리오 생성 그래프 (1번)

**용도:** User 프로필·에셋(RAPTOR·Asset 결과) → STAR 문장 생성 → Self-Consistency 검증 → 포트폴리오 생성. **문항 미사용.**

### 2.1 노드·엣지 (초안)

```
[START] → load_profile → build_star_sentence → self_consistency ──(통과)──→ build_portfolio → [END]
                                    ↑                │
                                    │                └──(실패 & retry < 3)──→ build_star_sentence (피드백 프롬프트 반영 재생성)
                                    │                └──(실패 & retry >= 3)──→ build_portfolio
                                    └────────────────────────────────────────── consistency_feedback 전달
```

- **검증 실패 시:** `consistency_feedback`를 프롬프트에 담아 `build_star_sentence` 재호출. LangGraph 활용 핵심.
- **max_star_retries:** 3. 재시도 상한 초과 시 build_portfolio로 진행 (fallback 노드 없음)

| 노드 | 역할 | 입출력(State) |
|------|------|----------------|
| `load_profile` | User 프로필·에셋 로드 (P1 API 또는 DB) | 입력: `user_id` / 출력: `profile`, `assets` |
| `build_star_sentence` | 프로필·에셋 → STAR 생성. **재진입 시** `consistency_feedback` 프롬프트 반영 | 입력: `profile`, `assets`, (재진입) `consistency_feedback` / 출력: `star` |
| `self_consistency` | 환각 체크 + STAR 충실도. 실패 시 `consistency_feedback`, `star_retry_count` 증가 | 입력: `star`, `profile`, `assets` / 출력: `is_hallucination`, `is_star`, `consistency_feedback`, `star_retry_count` |
| `build_portfolio` | STAR·프로필·에셋 → 포트폴리오 | 입력: `star`, `profile`, `assets` / 출력: `portfolio` |

### 2.2 구현 상세 (노드 미구현, 문서만)

| 항목 | 내용 |
|------|------|
| **Hallucination 체크** | STAR 문장에 **Retrieval(profile, assets)에 없는 내용**이 포함되면 실패. 없는 경험·지어낸 수치·근거 없는 주장 등. LLM으로 검증. |
| **build_star_sentence 재생성** | 검증 실패 시 `consistency_feedback`를 프롬프트에 담아 **실제 LLM 호출**로 STAR 재생성. (노드 구현 시 적용) |
| **load_profile 실패** | user_id 없음·조회 실패 등은 **나중에 처리** 예정. |

### 2.3 State (초안)

```python
class PortfolioState(TypedDict, total=False):
    user_id: str
    profile: dict
    assets: list
    star: list
    is_hallucination: bool
    is_star: bool
    star_retry_count: int
    portfolio: dict | str
    consistency_feedback: dict
```

---

## 3. Writer 그래프 (2번)

**용도:** 문항 + 합격 자소서 샘플 → 유저 DB(에셋) 조회 → 자소서 초안 생성.

**상세:** `AUTOFOLIO_Writer_그래프_파이프라인_제안.md` 참고.

### 3.1 노드·엣지 (요약)

```
[START] → retrieve_samples → load_assets → generate_draft → self_consistency ──(통과)──→ format_output → [END]
    │            │                │                ↑                                │
    │            │  유사 샘플      │  유저 DB(에셋)   └──(실패 & retry < 3)──→ generate_draft (피드백 반영 재생성)
    │            │                │                └──(실패 & retry >= 3)──→ format_output
    │            └──(검증 실패)──→ END   └──(조회 실패)──→ END
```

- **순서:** 문항 → 유사 샘플 → **유저 DB(에셋)** → 초안 → 체크 → 교정 → 출력.
- **검증 실패 시:** `consistency_feedback`를 프롬프트에 담아 `generate_draft` 재호출.
- **max_draft_retries:** 3. 재시도 상한 초과 시 format_output으로 진행.

| 노드 | 역할 | 입출력(State) |
|------|------|----------------|
| `retrieve_samples` | 진입 시 검증 + 합격 자소서 검색. 못 찾아도 load_assets 진행 | 입력: `question`, `max_chars`, `job_parsed` / 출력: `samples` (검증 실패만 `error`) |
| `load_assets` | 유저 DB에서 에셋 조회. 문항/공고 기반 선별 | 입력: `user_id`, `question`, `job_parsed` / 출력: `assets` 또는 `error` |
| `generate_draft` | LLM 초안 생성. **재진입 시** `consistency_feedback` 프롬프트 반영 | 입력: `assets`, `samples`, `question`, `job_parsed`, (재진입) `consistency_feedback` / 출력: `draft` |
| `self_consistency` | 환각 체크. 실패 시 `consistency_feedback`, `draft_retry_count` 증가 | 입력: `draft`, `assets` / 출력: `is_hallucination`, `consistency_feedback`, `draft_retry_count` |
| `format_output` | 글자수·형식 정리 | 입력: `draft`, `max_chars` / 출력: `draft` |

### 3.2 State (초안)

```python
class WriterState(TypedDict, total=False):
    user_id: str
    assets: list
    question: str
    max_chars: int
    job_parsed: dict
    samples: list
    draft: str
    is_hallucination: bool
    draft_retry_count: int
    consistency_feedback: dict
    messages: list
    error: str
```

---

## 4. Inspector 그래프 (3번)

**용도:** 초안 + 에셋·합격 샘플 → 보완 제안. 유저 수정 후 재첨삭(Human-in-the-loop).

**상세:** `AUTOFOLIO_Inspector_그래프_파이프라인_제안.md` 참고.

### 4.1 노드·엣지

```
[START] → load_draft → analyze → suggest → [Human 입력 대기]
    │          │            │                    │
    │          │            │  유저 수정 후 재호출  │
    │          │            └──────── re_inspect ──→ load_draft → ...
    │          └── 무조건 에셋·합격 샘플 재조회      round < N
    └──(draft 없음)──→ END                        round >= N → end
```

| 노드 | 역할 | 입출력(State) |
|------|------|----------------|
| `load_draft` | 진입 검증 + **무조건** 에셋·합격 샘플 재조회 | 입력: `draft`, `user_id`, `question`, `job_parsed` / 출력: `assets`, `samples` (실패 시 `error`) |
| `analyze` | LLM 보완점 분석 → suggestions 직접 출력 | 입력: `draft`, `assets`, `samples`, `user_edited`, `round` / 출력: `suggestions` |
| `suggest` | 제안 반환 (interrupt 지점) | 입력: `suggestions` / 출력: `suggestions` |
| `re_inspect` | 수정본 재검토 | 입력: `user_edited`, `round` / 출력: `draft`, `round` |

### 4.2 State (초안)

```python
class InspectorState(TypedDict, total=False):
    draft: str
    assets: list
    samples: list
    suggestions: list
    user_edited: str
    round: int
    error: str
```

---

## 5. 그래프가 호출하는 API·모듈 정리

| 호출 주체 | 대상 | 제공 | 비고 |
|-----------|------|------|------|
| Writer `retrieve_samples` | 합격 자소서 검색 **모듈** (문항/회사/연도/키워드) | 내부 모듈 | 별도 API 노출 없음 |
| Writer `load_assets` | User 에셋/프로필 조회 | P1 API 또는 DB | 유저 DB에서 에셋 조회 |
| Inspector `load_draft` | User 에셋·합격 자소서 **무조건 재조회** | P1 API 또는 DB, 내부 모듈 | Writer와 동일 모듈 재사용 |
| 포트폴리오 `load_profile` | User 프로필·에셋 조회 | P1 API 또는 DB | (선택) |

---

## 6. 미정·토의 항목

- [ ] State 필드명·타입 최종화 (Pydantic vs TypedDict)
- [x] 포트폴리오: 검증 실패 시 피드백 프롬프트 반영 재생성 루프. fallback 노드 없음.
- [x] Inspector `max_rounds` 기본값 5
- [ ] LangGraph 버전·패키지 (langgraph, langgraph-core 등)
- [ ] 그래프 컴파일 후 FastAPI 엔드포인트 노출 방식 (invoke/stream)

---

## 7. 문서 이력

- 0.1: LangGraph 설계 초안.
- 0.2: 포트폴리오 그래프 추가.
- 0.3: 포트폴리오 검증 루프 상세화.
- 0.6: 합격 자소서 검색을 API → 모듈 호출로 변경.
- 1.0 (2026-03-04): 전략 수립 그래프 제거, Portfolio/Writer/Inspector 3개 체계로 정리.
- 1.1: 포트폴리오 fallback 제거, self_consistency 1회만(재시도 없음). max_star_retries=3 참고용.
- 1.2: 포트폴리오·Writer 검증 실패 시 피드백 프롬프트 반영 재생성 루프 복원. LangGraph 활용.
- 1.3: Writer에 load_assets 노드 추가. 문항 → 유사 샘플 → 유저 DB(에셋) → 초안 순서 확정.
- 1.4: Inspector load_draft 무조건 에셋·합격 샘플 재조회. re_inspect → load_draft. samples, error State 추가.
- 1.5: Inspector max_rounds 기본값 5 확정.
