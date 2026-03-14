# Writer 그래프 파이프라인 제안

**문서 버전:** 1.10  
**기준:** [AUTOFOLIO_LangGraph_설계.md](AUTOFOLIO_LangGraph_설계.md) §3, [AUTOFOLIO_RAG_파이프라인_핵심.md](AUTOFOLIO_RAG_파이프라인_핵심.md), [AUTOFOLIO_API_스펙.md](AUTOFOLIO_API_스펙.md)

---

## 1. 개요

**역할:** 문항 입력 → 유사 자소서 샘플 → 유저 DB(에셋) 조회 → 초안 작성 → 체크 → 아웃풋 교정 → 출력.

**호출 경로:** `POST /api/cover-letter/draft` (body: `questions[]` 다문항) → **Writer 그래프**를 문항별로 호출 (에셋 조회는 그래프 내부 `load_assets`) → `draft_session_id` + `drafts[]` 반환. (전략 수립 없음)

**API 입력:** `job_id`(선택), `tone`(선택), `questions[]` (각 항목: question_text, max_chars, min_chars 선택)  
**그래프 입력(문항 1개 기준):** `user_id`, `question`, `max_chars` (및 `job_parsed`, `tone` 선택)  
**출력:** `draft_session_id`, `drafts[]` (draft_id, question_text, answer, char_count)

---

## 2. 파이프라인 플로우

```
[START] → retrieve_samples → load_assets → generate_draft → self_consistency ──(통과)──→ format_output → [END]
    │            │                │                ↑                                │
    │            │                │                └──(실패 & retry < 3)──→ generate_draft (피드백 반영 재생성)
    │            │                │                └──(실패 & retry >= 3)──→ format_output
    │            │                └────────────────────────────────────── consistency_feedback 전달
    │            │  유사 자소서 샘플 검색
    │            └──(검증 실패)──→ END
    │  유저 DB(에셋) 조회
    └──(조회 실패)──→ END
```

- **순서:** 문항 입력 → 유사 샘플 → **유저 DB(에셋)** → 초안 → 체크 → 교정 → 출력.
- **검증 실패 시:** `consistency_feedback`를 프롬프트에 담아 `generate_draft` 재호출. **LangGraph 활용 핵심.**
- **max_draft_retries:** 3. 재시도 상한 초과 시 format_output으로 진행 (fallback 노드 없음)


| 순서  | 노드                 | 역할                                               | 입력(State)                                                                   | 출력(State)                                                                |
| --- | ------------------ | ------------------------------------------------ | --------------------------------------------------------------------------- | ------------------------------------------------------------------------ |
| 1   | `retrieve_samples` | **진입 시 검증** (question, max_chars). 합격 자소서 검색. 못 찾아도 load_assets 진행 | `question`, `max_chars`, `job_parsed`                                       | (통과) `samples` / (검증 실패만) `error` → END                                         |
| 2   | `load_assets`      | **유저 DB**에서 에셋 조회. 문항/공고 기반 관련 에셋 선별 | `user_id`, `question`, `job_parsed`                                         | (통과) `assets` / (실패) `error` → END                                        |
| 3   | `generate_draft`   | LLM 초안 생성. **재진입 시** `consistency_feedback` 프롬프트 반영 | `assets`, `samples`, `question`, `job_parsed`, (재진입) `consistency_feedback` | `draft`                                                                  |
| 4   | `self_consistency` | **환각 체크**. 실패 시 피드백 기록 → generate_draft 재호출 | `draft`, `assets`, `draft_retry_count`                                      | `is_hallucination`, (실패 시) `consistency_feedback`, `draft_retry_count`+1 |
| 5   | `format_output`    | 글자수·형식 정리 (max_chars 필수)                              | `draft`, `max_chars` (유저 입력)                                             | `draft` (최종)                                                             |


---

## 3. State 정의

```python
from typing import TypedDict


class WriterState(TypedDict, total=False):
    """Writer 그래프 State.

    - user_id: 사용자 식별자 (load_assets에서 유저 DB 조회용)
    - assets: 매칭된 에셋 목록 (load_assets 출력)
    - question: 자소서 문항 (질문 텍스트)
    - max_chars: 글자수 제한. **유저 입력** (draft API 요청 시 필수)
    - job_parsed: 채용 공고 파싱 결과 (기업명, 인재상 등 — retrieve_samples·load_assets·generate_draft 참고)
    - samples: 합격 자소서 검색 모듈 결과 (retrieve_samples 출력)
    - draft: LLM 초안 (generate_draft 출력, format_output에서 정제)
    - is_hallucination: self_consistency 환각 체크 통과 여부
    - draft_retry_count: generate_draft 재진입 횟수 (피드백 반영 재생성)
    - consistency_feedback: 검증 실패 시 재생성용 피드백 (프롬프트에 반영)
    - messages: (선택) 대화 이력 — 스트리밍/디버깅용
    - error: 에러 메시지 — retrieve_samples·load_assets 검증/조회 실패 시
    """

    user_id: str
    assets: list
    question: str
    max_chars: int  # 유저 입력. 필수.
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

## 4. 노드 상세

### 4.1 retrieve_samples

- **역할:** **진입 시** 필수 필드(`question`, `max_chars`) 검증. 통과 시 합격 자소서 검색 **모듈** 호출. (에셋은 load_assets에서 이후 조회)
- **입력:** `question`, `max_chars`, `job_parsed` (State에서 읽음. `job_parsed`는 선택)
- **출력:** (통과) `samples` / (검증 실패만) `error` → END
- **검증:** `question`, `max_chars` 없으면 `error` 설정 후 반환. 조건 엣지로 END 분기.
- **검색:** 검증 통과 시 문항/회사/연도/키워드로 유사 합격 자소서 목록 조회.
- **출력:** `samples` (list of dict: 문항, 답변, 회사, 연도 등)
- **모듈 인터페이스 (제안):**
  ```python
  def retrieve_passed_cover_letters(
      question: str,
      company_name: str | None = None,
      position: str | None = None,
      year: int | None = None,
      keywords: list[str] | None = None,
      top_k: int = 5,
  ) -> list[dict]:
      """문항/회사/연도/키워드 → 유사 합격 자소서 목록."""
  ```
- **대외 API:** 없음. Writer 그래프 내부에서만 호출.
- **samples 못 찾아도 load_assets로 진행:** 검색 결과 없음(빈 리스트) 또는 검색 모듈 에러 시에도 `error` 설정하지 않음. `samples=[]`로 load_assets → generate_draft 진행. `generate_draft`는 assets만으로도 초안 생성 가능.

### 4.2 load_assets

- **역할:** **유저 DB**에서 에셋 조회. 문항/공고 기반 관련 에셋 선별. retrieve_samples 통과 후 수행.
- **입력:** `user_id`, `question`, `job_parsed` (State에서 읽음)
- **출력:** (통과) `assets` / (실패) `error` → END
- **조회:** `user_id`로 P1 API 또는 DB에서 에셋 조회. 문항·공고(job_parsed) 기반으로 관련 에셋 선별.
- **조회 실패 시:** `error` 설정 후 반환. 조건 엣지로 END 분기.

### 4.3 generate_draft

- **역할:** 에셋 + 샘플 + 문항 → LLM으로 자소서 초안 생성. **재진입 시** `consistency_feedback`를 프롬프트에 반영.
- **입력:** `assets`, `samples`, `question`, `job_parsed`, (재진입 시) `consistency_feedback`
- **출력:** `draft` (원시 텍스트)
- **프롬프트 구성 (제안):**
  - 시스템: "증거 기반 자소서 작성. 에셋에 근거한 내용만 사용. 환각 금지."
  - 사용자: `question` + `assets` 요약 + `samples` 예시(일부) + `job_parsed`(기업 인재상 등)
  - **재진입 시:** "다음 지적을 반영해 수정: {consistency_feedback}"

### 4.4 self_consistency

- **역할:** **환각 체크**. 실패 시 `consistency_feedback` 기록 → `generate_draft` 재호출 (피드백 프롬프트 반영).
- **입력:** `draft`, `assets`, `draft_retry_count`
- **출력:** `is_hallucination`, (실패 시) `consistency_feedback`, `draft_retry_count`+1
- **상세:**
  - 생성된 draft가 assets에 근거한지 검사. 없는 경험·지어낸 수치·근거 없는 주장이 있으면 실패.
  - 실패 시: `consistency_feedback`에 문장/구간·근거 없는 내용·이유 기록. `draft_retry_count` 증가. → `generate_draft` 재호출.
  - 재시도 상한(3회) 초과 시 format_output으로 진행.

### 4.5 format_output

- **역할:** 글자수 제한·줄바꿈·불필요 공백 정리. **max_chars 필수.**
- **입력:** `draft`, `max_chars` (유저가 draft API 요청 시 제공)
- **출력:** `draft` (최종, API 응답에 그대로 사용. State의 draft 필드 덮어쓰기)
- **글자수·형식 규칙:**
  - **max_chars:** **유저 입력** (draft API body에 `max_chars` 필수). 자소서 문항은 채용공고 파싱 대상 아님. 유저가 직접 입력.
  - 줄바꿈: 연속 공백·빈 줄 정리. 문단 구분 유지.
  - 띄어쓰기: 한국어 맞춤법 검사는 MVP 범위 외. 불필요 공백만 제거.

---

## 5. 엣지 (조건 분기)


| From             | To               | 조건                                              |
| ---------------- | ---------------- | ----------------------------------------------- |
| START            | retrieve_samples | -                                               |
| retrieve_samples | load_assets      | (검증 통과 시. samples 못 찾아도 진행)              |
| retrieve_samples | END              | (검증 실패 시만. `error` 설정)                       |
| load_assets     | generate_draft   | (통과 시)                                        |
| load_assets     | END              | (조회 실패 시. `error` 설정)                       |
| generate_draft   | self_consistency | -                                               |
| self_consistency | format_output    | 통과 또는 `draft_retry_count >= 3`               |
| self_consistency | generate_draft   | 실패 & `draft_retry_count < 3` (피드백 프롬프트 반영 재생성) |
| format_output    | END              | -                                               |

---

## 6. draft API와의 연동

```
[클라이언트] POST /api/cover-letter/draft
    body: { "job_id": "..." (선택), "tone": "professional"|"friendly"|"concise" (선택),
            "questions": [ { "question_text": "...", "max_chars": 500, "min_chars": 0 (선택) }, ... ] }
         │  다문항(3~5개) 한 번에 입력. user_id는 인증에서 추출.
         ▼
[서버] 1. job_id 있으면 공고 파싱 결과 조회 (또는 캐시) → job_parsed
      2. draft_sessions 레코드 생성 후, 문항별 cover_letter_items 생성
      3. Writer 그래프를 문항별로 호출 (user_id, question, max_chars, job_parsed, tone)
         → retrieve_samples → load_assets → generate_draft → self_consistency → format_output
      4. draft_session_id + drafts[] (draft_id, question_text, answer, char_count) 반환
```

---

## 7. 구현 구조 (portfolio_graph 패턴 따름)

```
src/graphs/writer_graph/
├── __init__.py
├── state.py      # WriterState
├── node.py       # retrieve_samples, load_assets, generate_draft, self_consistency, format_output
├── edge.py       # after_retrieve_samples, after_load_assets, after_self_consistency
└── graph.py      # build_writer_graph()
```

---

## 8. 비판적 검토 (수용 전 고려 사항)

| 항목 | 검토 내용 | 결론 |
|------|----------|------|
| **검증 실패 시 피드백 반영** | consistency_feedback를 프롬프트에 담아 generate_draft 재호출. LangGraph 활용 핵심. | 재시도 최대 3회. 상한 초과 시 format_output |
| **전략 수립** | 전략 수립 그래프 없음. 에셋 조회는 Writer 내부 load_assets에서 수행. | 전략 수립 제거 확정 |
| **유저 DB 조회 순서** | 문항 → 유사 샘플 → **유저 DB(에셋)** → 초안. 기본 중 기본. | retrieve_samples 다음 load_assets |
| **samples 빈 리스트** | samples 없이도 assets로 생성 가능. | 그대로 진행, 프롬프트에 "샘플 없음" 명시 |
| **문항 입력** | 자소서 문항은 **유저 입력**. draft API body에 `questions[]` (각 항목: question_text, max_chars 필수, min_chars 선택) 필수. | 채용공고 파싱 대상 아님. [AUTOFOLIO_채용공고파싱전략.md](AUTOFOLIO_채용공고파싱전략.md) |

---

## 9. 문서 관계

- 에셋 조회·API 모듈: [AUTOFOLIO_LangGraph_설계.md](AUTOFOLIO_LangGraph_설계.md) §5
- Inspector 그래프: [AUTOFOLIO_LangGraph_설계.md](AUTOFOLIO_LangGraph_설계.md) §4
- 합격 자소서 검색 모듈: [AUTOFOLIO_16주_계획표.md](AUTOFOLIO_16주_계획표.md) 4주, 8주
- 채용공고 파싱: [AUTOFOLIO_채용공고파싱전략.md](AUTOFOLIO_채용공고파싱전략.md) (자소서 문항은 유저 입력)

---

## 10. 문서 이력

- 1.0: 문서 기반 Writer 그래프 파이프라인 제안. State·노드·엣지·draft 연동 정리.
- 1.1: generate_draft 이후 self_consistency 로직 추가. 환각 체크·전략 충실도·재진입·fallback 분기.
- 1.2: max_draft_retries 기본값·fallback 정책, samples 빈 리스트 처리, format_output↔문항 메타·비판적 검토 섹션 추가.
- 1.3: 각 노드별 입력·출력 명시. load_context, __fallback__, generate_draft(job_parsed), self_consistency(draft_retry_count), format_output(question_meta) 보완.
- 1.4: self_consistency 1회만(재시도·fallback 제거). 전략 충실도·strategy 제거. max_chars 필수, 채용공고 파싱에 자소서_문항 추가 반영.
- 1.5: 자소서 문항(질문+글자수) **유저 입력**으로 변경. 채용공고 파싱에서 자소서_문항 제거. draft API body에 `question_text`, `max_chars` 필수.
- 1.6: 전략 수립 없음 확정. draft 시 에셋 조회만 수행.
- 1.7: load_context 제거. retrieve_samples 진입 시 검증 통합.
- 1.8: 검증 실패 시 피드백 프롬프트 반영 재생성 루프 복원. consistency_feedback, draft_retry_count.
- 1.9: load_assets 노드 추가. 문항 → 유사 샘플 → **유저 DB(에셋)** → 초안 순서 확정. 에셋 조회를 Writer 그래프 내부로 이동.
- 1.10: draft API 다문항 반영. 요청은 questions[], 응답은 draft_session_id + drafts[]. 그래프는 문항별 호출, DB는 draft_sessions/cover_letter_items.

