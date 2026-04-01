# Week 5 작업 정리

> PR 본문에 그대로 붙여 넣을 수 있도록 요약·이슈·파일 목록까지 한 파일에 모았습니다.

---

## PR 제목 (예시)

```
Week 5: Jobs parse, Cover letter Draft, RAG/Chroma 정합, 대시보드·GitHub 임베딩 UX
```

---

## Summary (PR 본문용)

- **채용공고 저장**: `POST /api/jobs/parse` — SQLite `jobs`에 저장 후 `job_id` 반환 (manual / url).
- **자소서 Draft (Writer)**: `POST /api/cover-letter/draft` — 세션 필수, 선택 `job_id`로 공고 맥락 로드, LangGraph Writer 파이프라인.
- **RAG / Chroma 정합**: GitHub 임베딩 메타 `source: github`, `load_assets`에서 구 문서 호환, **임베딩 공간 불일치** 해결(OpenAI 임베딩으로 `query_embeddings` 검색).
- **대시보드 (`src/web/dashboard.py`)**: Job parse UI, Writer Draft UI, **레포 카드 탭(파일 선택 / 파일 보기 / 커밋)**, 카드 단위 히스토리 동기화·임베딩, **경로 인코딩 이슈** 대응, **페이지 로드 시 Chroma 임베딩 뱃지 동기화**.
- **백엔드**: `GET /api/user/embedding-status` — 선택 레포별 Chroma `user_assets_{user_id}`에 `repo` 메타 존재 여부로 embedded 여부 반환.

---

## API·백엔드

### 채용공고 저장 (parse)

- **`POST /api/jobs/parse`**: SQLite `jobs` 테이블에 공고 저장 후 `job_id` 반환.
- **manual**: 본문 직접 입력.
- **url**: 페이지를 가져와 파싱; `OPENAI_API_KEY`가 있으면 구조화 보조.

### 자소서 Draft (Writer)

- **`POST /api/cover-letter/draft`**: GitHub 로그인 세션 필수. 선택 `job_id`로 `jobs` + `job_parsed` 맥락 로드.
- LangGraph Writer: `retrieve_samples` → `load_assets` → `generate_draft` → `self_consistency` → `format_output`.
- 구현: `src/api/cover_letter.py`, `src/graphs/writer_graph/` (노드, 엣지, 프롬프트).

### 앱 등록

- `src/app/main.py`에 jobs·cover letter 라우터 등록.

### GitHub 임베딩 상태 (신규)

- **`GET /api/user/embedding-status`** (`src/api/github.py`)
  - 인증: 세션 `user_id` 필수.
  - `selected_repos` 목록의 각 `full_name`에 대해 Chroma 컬렉션 `user_assets_{user_id}`에서  
    `collection.get(where={"repo": {"$eq": full_name}}, limit=1)` — `ids`가 있으면 embedded.
  - 응답: `{ "status": { "<owner/repo>": true | false, ... } }`.

---

## GitHub 코드 임베딩·RAG

### 데모 흐름 (대시보드)

- `asset_hierarchy` ↔ `selected_repo_assets` 동기화, GitHub Contents API, (옵션) OpenAI 요약·임베딩, Chroma `user_assets_{user_id}`.
- 문서: `docs/API_GitHub_Spec.md` (임베딩 바디 등 실제 코드와 맞춤).

### 버그 수정 (핵심)

1. **`source` 메타데이터**  
   GitHub 파이프라인 `_normalize_metadata`에 `source: github` 추가. Chroma `where` 필터와 스키마 정합.

2. **`load_assets` 필터**  
   과거 문서에 `source`가 없을 수 있어 `retrieve_user_assets(..., source_filter=None)`로 조회.

3. **임베딩 공간 불일치 (Draft 빈 응답 원인)**  
   - 적재: OpenAI `text-embedding-3-small`.  
   - 조회: `query_texts`만 쓰면 컬렉션 기본 임베더(MiniLM 등)가 사용되어 차원·공간이 달라짐.  
   - **해결**: `OPENAI_API_KEY`가 있을 때 STAR 쿼리를 동일 `OpenAIEmbedder`로 임베딩한 뒤 `query_embeddings`로 검색 (`src/service/rag/user_assets.py`).

---

## 프론트·대시보드 (`src/web/dashboard.py`)

### 공통

- Job parse 패널 (`job_id` 자동 채움), Cover letter Draft 패널, GitHub 임베딩 안내 문구.

### 레포 카드 (임베딩 데모 그리드) — 상세

- **탭 3개**: `[파일 선택] [파일 보기] [커밋]` — `repoCardMap.activeTab` (기본 `'files'`).
- **파일 선택**: 파일 트리 체크박스, 파일 선택 저장, **히스토리 → SQLite** (`sync-from-assets`), **임베딩** (카드 단건: PUT assets → sync → POST embedding; 상단 `embedRef` / `include_summaries`와 동일 규칙).
- **파일 보기**: `selectedAssetKeys` 중 `code:` 경로만 드롭다운 — 선택 시 `GET .../contents?path=...&encoding=raw`, 카드 내 `<pre>` 표시. 카드별 `ref`는 비우면 쿼리 미전송(기본 브랜치).
- **커밋**: `author`(비우면 서버에서 로그인 유저), `per_page`(기본 10), 커밋 조회 — 상위 10건을 `sha(7) · message · date · files_changed` 형태로 표시.
- **에러**: fetch 실패 시 `alert` 대신 카드 내 에러 영역에 `접근 실패: ...` 형식.

### 경로 인코딩 (FastAPI `{repo_id:path}` 호환)

- **문제**: `encodeURIComponent(full_name)` 시 `owner/repo` → `owner%2Frepo`가 되어 FastAPI가 path로 인식하지 못해 404 / fetch 실패.
- **해결**: 임베딩·파일·내용·커밋 요청 URL의 경로 구간에는 `encodeURIComponent(full_name)` 대신  
  `full_name.replace(/ /g, '%20')`만 적용(슬래시 유지).  
  Query(`path`, `ref`, `author` 등)는 기존처럼 `encodeURIComponent` 유지.

### 임베딩 뱃지 동기화 (페이지 새로고침)

- `loadMe()` → `loadSelectedReposUI()` 완료 후 **`GET /api/user/embedding-status`** 호출.
- 응답 `status`로 `embeddingStatusCache` 갱신 후 **`renderAllRepoCards()`** 재호출 → ✅/⬜ 뱃지가 Chroma 실제 상태와 일치.

### 기타 (raw string)

- `dashboard.py`는 Python raw string이라 JS 문자열 이스케이프 주의(줄바꿈 등).

---

## 구현·이슈 해결 요약 (타임라인식)

| 이슈 | 원인 | 해결 |
|------|------|------|
| `%2F`로 인코딩된 레포 경로 | `full_name`을 `encodeURIComponent` → 슬래시가 `%2F` | 경로에는 슬래시 유지, 공백만 `%20` |
| 탭/기능 분산 | 단일 패널에 기능 몰림 | 탭 3개 + `activeTab` 상태 |
| 뱃지와 실제 Chroma 불일치 | 세션 내 캐시만 갱신, 새로고침 시 초기화 | `GET /api/user/embedding-status` + 캐시 + 재렌더 |
| raw string 내 JS `\n` | `\\n` vs `\n` 혼동 | 커밋 목록 등 실제 줄바꿈에 맞게 `.join('\n')` 정리 |

---

## 의존성

- `pyproject.toml` / `poetry.lock`: 예) `httpx` 등 공고 URL fetch용.

---

## 테스트

- `tests/api/test_cover_letter.py`, `tests/api/test_jobs_parse.py`
- `tests/service/rag/test_user_assets.py` (OpenAI 쿼리 경로·기존 STAR 쿼리)
- `tests/graphs/writer_graph/` 등 Writer 노드
- 기준: 전체 pytest 통과(주차 마감 시점 기준).

---

## 문서

- `docs/API_GitHub_Spec.md`, `docs/API_Service_Spec.md` 갱신.

---

## 참고·후속

- Draft 응답에 `error`가 있어도 HTTP 200에서 본문만 비는 경우가 있었음 → API 레이어에서 그래프 `error`를 노출하는 개선은 후속 과제로 남길 수 있음.
- `used_assets.github_repos`는 응답 스키마 상 플레이스홀더에 가까움.
- `GET /api/user/embedding-status`에 대한 단위/API 테스트 추가는 선택 과제.

---

## 변경 파일 참고 (PR 리뷰용 체크리스트)

- **API / 서비스**: `src/api/github.py`, `src/api/jobs.py`, `src/api/cover_letter.py`, `src/service/rag/user_assets.py`, `src/service/rag/passed_samples.py`, …
- **Writer 그래프**: `src/graphs/writer_graph/node.py`, `prompts.py`, `state.py`, …
- **대시보드**: `src/web/dashboard.py`
- **테스트**: `tests/api/`, `tests/service/rag/`, `tests/graphs/writer_graph/`, …
- **스크립트(선택)**: `scripts/load_passed_cover_letters.py`

(정확한 diff는 `git diff main...week5` 또는 PR Files changed 탭 참고.)
