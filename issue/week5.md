# Week 5 작업 정리

## 개요

자기소개서 Writer(코드 RAG + 채용공고 맥락), 채용공고 파싱 API, 대시보드 연동, GitHub 임베딩·RAG 검색 일관성 수정을 포함한 한 주차 작업입니다.

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

## 프론트·대시보드

- `src/web/dashboard.py`: Job parse 패널(`job_id` 자동 채움), Cover letter Draft 패널, GitHub 임베딩 안내 문구 등.

## 의존성

- `pyproject.toml` / `poetry.lock`: 예) `httpx` 등 공고 URL fetch용.

## 테스트

- `tests/api/test_cover_letter.py`, `tests/api/test_jobs_parse.py`
- `tests/service/rag/test_user_assets.py` (OpenAI 쿼리 경로·기존 STAR 쿼리)
- `tests/graphs/writer_graph/` 등 Writer 노드
- 기준: 전체 pytest 통과(주차 마감 시점 기준).

## 문서

- `docs/API_GitHub_Spec.md`, `docs/API_Service_Spec.md` 갱신.

## 참고

- Draft 응답에 `error`가 있어도 HTTP 200에서 본문만 비는 경우가 있었음 → API 레이어에서 그래프 `error`를 노출하는 개선은 후속 과제로 남길 수 있음.
- `used_assets.github_repos`는 응답 스키마 상 플레이스홀더에 가까움.
