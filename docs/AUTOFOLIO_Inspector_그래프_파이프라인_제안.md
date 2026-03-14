# Inspector 그래프 파이프라인 제안

**문서 버전:** 1.3  
**기준:** [AUTOFOLIO_LangGraph_설계.md](AUTOFOLIO_LangGraph_설계.md) §4, [AUTOFOLIO_RAG_파이프라인_핵심.md](AUTOFOLIO_RAG_파이프라인_핵심.md), [AUTOFOLIO_API_스펙.md](AUTOFOLIO_API_스펙.md)

---

## 1. 개요

**역할:** 초안 + 에셋 + 합격 샘플 → LLM 보완점 분석 → 첨삭 제안 반환. 유저 수정 후 재첨삭(Human-in-the-loop).

**호출 경로:** `POST /api/cover-letter/inspect` → **Inspector 그래프** → 보완 제안 반환. Human 수정 후 재호출로 반복 첨삭.

**입력:** `draft` (초안), `user_edited` (선택, 유저 수정본), `question` (선택), `job_parsed` (선택)  
**출력:** `suggestions` (보완 제안 목록)

- **에셋·합격 샘플:** 입력으로 받지 않음. `load_draft`에서 **무조건** 유저 DB·자소서 DB 재조회.

---

## 2. 파이프라인 플로우

```
[START] → load_draft → analyze → suggest ──(interrupt)──→ [Human 입력 대기]
    │          │            │        │                            │
    │          │            │        │  유저 수정 후 재호출         │
    │          │            │        │                            ▼
    │          │            │        └──────────────── re_inspect ──→ load_draft → analyze → ...
    │          │            │  LLM 보완점 분석 → suggestions 직접 출력    round < max_rounds
    │          │            └── 에셋·합격 샘플 참고                        round >= max_rounds → END
    │          └── 무조건 에셋 + 합격 샘플 재조회 (user_id, question, job_parsed)
    └──(draft 없음)──→ END
```

- **순서:** draft 검증 → **load_draft**(에셋·합격 샘플 무조건 재조회) → analyze → suggest → **interrupt** (Human 대기).
- **Human-in-the-loop:** `suggest` 완료 후 **interrupt_after**. 클라이언트가 `user_edited`로 재호출 시 `re_inspect` → `load_draft` → `analyze` → `suggest` 반복. `round >= max_rounds`이면 END.
- **max_rounds:** 5 (기본). 재첨삭 라운드 상한.

| 순서 | 노드        | 역할                                               | 입력(State)                          | 출력(State)                    |
| --- | ----------- | -------------------------------------------------- | ----------------------------------- | ----------------------------- |
| 1   | `load_draft` | **진입 시 검증** (draft 필수). **무조건** 에셋·합격 샘플 재조회 | `draft`, `user_id`, `question`, `job_parsed`, `user_edited` | `draft`, `assets`, `samples` / (실패) `error` → END |
| 2   | `analyze`   | LLM 보완점 분석 → **suggestions 직접 출력**         | `draft`, `assets`, `samples`, `user_edited`, `round` | `suggestions`                 |
| 3   | `suggest`   | 제안 반환. **interrupt 후 Human 대기**              | `suggestions`                       | `suggestions`                 |
| 4   | `re_inspect`| **재호출 시**. user_edited → draft 갱신, round 증가 | `user_edited`, `round`              | `draft`, `round`              |

---

## 3. State 정의

```python
from typing import TypedDict


class InspectorState(TypedDict, total=False):
    """Inspector 그래프 State. (기존 LangGraph §4 정렬)

    - draft: 초안 (Writer 출력 또는 이전 라운드 user_edited)
    - assets: 에셋 목록 (load_draft에서 무조건 재조회)
    - samples: 합격 자소서 목록 (load_draft에서 무조건 재조회)
    - suggestions: 보완 제안 목록 (analyze 출력, suggest 반환)
    - user_edited: 유저가 수정한 초안 (재호출 시 draft로 사용)
    - round: 재첨삭 라운드 (0=최초, 1+=재첨삭)
    - error: 검증/조회 실패 시 에러 메시지
    """

    draft: str
    assets: list
    samples: list
    suggestions: list
    user_edited: str
    round: int
    error: str
```

- `user_id`, `question`, `job_parsed`는 API에서 주입. State에는 보관하지 않거나 선택 필드로 둠.

---

## 4. 노드 상세

### 4.1 load_draft

- **역할:** **진입 시** 필수 필드(`draft`) 검증. `user_edited` 있으면 재첨삭 모드로 `draft` 갱신. **무조건** 에셋·합격 샘플 재조회.
- **입력:** `draft`, `user_edited`, `user_id`, `question`, `job_parsed` (API에서 전달)
- **출력:** (통과) `assets`, `samples` / (검증·조회 실패) `error` → END
- **검증:** `draft` 없고 `user_edited`도 없으면 `error` 설정 후 반환.
- **재첨삭:** `user_edited` 있으면 `draft = user_edited`, `round += 1`.
- **재조회 (무조건):**
  - **에셋:** Writer `load_assets`와 동일. `user_id` + `question` + `job_parsed`로 유저 DB 조회.
  - **합격 샘플:** Writer `retrieve_samples`와 동일. `question` + `job_parsed`로 자소서 DB 검색.
- **모듈:** Writer 그래프의 `load_assets`, `retrieve_passed_cover_letters` 재사용.

### 4.2 analyze

- **역할:** LLM으로 초안의 **보완점 분석** → **suggestions 직접 출력**. 에셋 근거, STAR 구조, 표현, 글자수 등.
- **입력:** `draft`, `assets`, `samples`, `user_edited`, `round`
- **출력:** `suggestions` (list of dict: 구간, 제안 내용, 근거, 우선순위 등)
- **프롬프트 구성 (제안):**
  - 시스템: "자소서 첨삭 전문가. 에셋에 근거한 보완 제안. 환각 금지."
  - 사용자: `draft` + `assets` 요약 + `samples` 예시(일부)
  - **재첨삭 시:** "이전 라운드 제안 반영 후 수정된 초안입니다. 추가 보완점을 분석해 주세요."

### 4.3 suggest

- **역할:** 제안 반환. `suggestions` 그대로 전달. **interrupt 지점**.
- **입력:** `suggestions`
- **출력:** `suggestions` (API 응답에 그대로 사용)
- **interrupt:** 이 노드 **이후** Human 입력 대기. LangGraph `interrupt_after=["suggest"]` 사용.

### 4.4 re_inspect

- **역할:** **재호출 시** Human이 수정한 초안 반영. `user_edited` → `draft` 갱신, `round` 증가.
- **입력:** `user_edited`, `round` (State에서 읽음)
- **출력:** `draft` (user_edited로 갱신), `round` (+1)
- **실행 시점:** interrupt 이후 클라이언트가 `user_edited`로 invoke 재호출 시. `re_inspect` → `load_draft` → `analyze` → `suggest` 순으로 진행.

---

## 5. 엣지 (조건 분기)

| From       | To          | 조건                                  |
| ---------- | ----------- | ------------------------------------- |
| START      | load_draft  | -                                     |
| load_draft | analyze     | (통과)                                |
| load_draft | END         | (검증·조회 실패. `error` 설정)        |
| analyze    | suggest     | -                                     |
| suggest    | re_inspect  | (interrupt 후 재호출 시 이 노드부터)   |
| re_inspect | load_draft  | `user_edited` 있음, `round < max_rounds` |
| re_inspect | END         | `user_edited` 없음 또는 `round >= max_rounds` |

---

## 6. Human-in-the-loop 구현 방식

**LangGraph `interrupt_after` 사용:**

```python
# graph.py
compiled = graph.compile(checkpointer=..., interrupt_after=["suggest"])
```

- `suggest` 완료 후 그래프 **중단**. 클라이언트에 `suggestions` 반환.
- **엣지:** `suggest` → `re_inspect` (재호출 시 이 노드부터 실행)
- 유저가 초안 수정 후 `user_edited`로 **같은 스레드(thread_id)** 에서 `invoke` 재호출.
- `re_inspect`에서 `user_edited` → `draft` 갱신, `round` 증가.
- `round >= max_rounds`이면 END. 그 전까지 `re_inspect` → `load_draft` → `analyze` → `suggest` → interrupt 반복.

**API 호출 패턴 (제안):**

```
1차: POST /api/cover-letter/inspect
     body: { "draft": "...", "job_id": "..." (선택) }
     → load_draft(에셋·샘플 재조회) → analyze → suggest → suggestions 반환, thread_id 반환

2차~: POST /api/cover-letter/inspect (같은 thread_id로 재호출)
      body: { "user_edited": "...", "thread_id": "..." }
      → re_inspect → load_draft → analyze → suggest → 새 suggestions 반환
```

---

## 7. inspect API와의 연동

```
[클라이언트] POST /api/cover-letter/inspect
    body: { "draft_session_id": "...", "answers": [ { "draft_id": "...", "answer": "..." }, ... ], "mode": "full_review"|"quick_check" (선택) }
         │  세션 전체 문항 답변 한 번에 전달. draft_id는 draft 응답의 draft_id(cover_letter_items.id).
         ▼
[서버] 1. draft_session_id로 세션·문항 조회
      2. 문항별로 Inspector 그래프 invoke (또는 배치). thread_id 있으면 checkpointer에서 상태 복원
         → 1차: load_draft → analyze → suggest → interrupt
         → 2차~: re_inspect → load_draft → analyze → suggest → interrupt / (round >= max) END
      3. feedbacks[] (draft_id, question_text, score, score_label, strengths, weaknesses, suggestions) + overall_score, overall_score_label, inspected_at 반환
```

---

## 8. 구현 구조 (portfolio_graph·writer_graph 패턴 따름)

```
src/graphs/inspector_graph/
├── __init__.py
├── state.py      # InspectorState
├── node.py       # load_draft, analyze, suggest, re_inspect
├── edge.py       # after_load_draft, after_re_inspect
└── graph.py      # build_inspector_graph(checkpointer=..., interrupt_after=["suggest"])
```

---

## 9. 비판적 검토 (수용 전 고려 사항)

| 항목 | 검토 내용 | 결론 |
|------|----------|------|
| **에셋·합격 샘플 무조건 재조회** | 입력으로 받지 않고 매번 load_draft에서 재조회. | RAG·기존 docs 정렬 |
| **Human-in-the-loop** | interrupt_after + checkpointer로 상태 유지. | LangGraph 표준 패턴 |
| **max_rounds** | 5 기본. 무한 반복 방지. | 토의 후 확정 |
| **load_draft 실패** | draft 없음·user_id 없음·조회 실패 시 END. | 에러 반환 |

---

## 10. 문서 관계

- Writer 그래프: [AUTOFOLIO_Writer_그래프_파이프라인_제안.md](AUTOFOLIO_Writer_그래프_파이프라인_제안.md)
- LangGraph 설계: [AUTOFOLIO_LangGraph_설계.md](AUTOFOLIO_LangGraph_설계.md) §4
- RAG 파이프라인: [AUTOFOLIO_RAG_파이프라인_핵심.md](AUTOFOLIO_RAG_파이프라인_핵심.md)
- API 스펙: [AUTOFOLIO_API_스펙.md](AUTOFOLIO_API_스펙.md)
- 16주 계획표: [AUTOFOLIO_16주_계획표.md](AUTOFOLIO_16주_계획표.md)

---

## 11. 문서 이력

- 1.0: Inspector 그래프 파이프라인 제안 초안. Portfolio·Writer 패턴 참고. Human-in-the-loop(interrupt) 반영.
- 1.1: 기존 docs 정렬. load_draft로 통합, analyze→suggestions 직접 출력, suggest 패스스루. **에셋·합격 샘플 무조건 재조회** 반영.
- 1.2: 플로우 다이어그램 수정. re_inspect → load_draft → analyze (load_draft 누락 보완).
- 1.3: inspect API 다문항·세션 반영. 요청: draft_session_id + answers[] (draft_id, answer). 응답: feedbacks[] + overall_score, overall_score_label.
