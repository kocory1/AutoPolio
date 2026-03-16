## Week3 - GitHub OAuth 연동 & 로그인 후 레포 목록 노출

**브랜치:** `feature/week3-oauth-repo-list`

**주차 목표**
- GitHub OAuth redirect/callback 구현
- 토큰 저장(세션·DB 등) 연동
- 레포 목록 API 연동
- **마일스톤:** 로그인 후 레포 목록 노출

---

### 진행 순서

1. **API 명세서 피드백 반영** — 리뷰 피드백에 따른 명세 수정 먼저 반영 (**진행 중**)
2. OAuth redirect/callback 구현
3. 토큰 저장 및 세션 처리
4. 레포 목록 API 연동 → 로그인 후 레포 목록 노출

---

### 한 것

| 항목 | 내용 |
|------|------|
| 브랜치 | `feature/week3-oauth-repo-list` 생성 (origin/main 기준) |
| API 명세서 정리 | 필요 없는 문서 제거: `API_Full_Spec.md`, `API_GitHub_Portfolio_Spec.md` (PR 반려·중복 정리) |
| 통합 Full Spec | `docs/API_Full_Spec.md` 신규 작성 — Common / Auth / GitHub / Service 4개 명세를 한 문서에 통합, 각 영역별 설명·엔드포인트 요약표·공통 규칙·사용 시퀀스 포함. 상세 스키마는 기존 4개 문서 참조하도록 구성 |
| 채용공고·job_id 정책 | 아래 "API·DB 정책 수정 요약" 참고 |

#### API·DB 정책 수정 요약

- **POST /api/jobs/parse** (`API_Service_Spec.md`)
  - 입력 두 가지로 통일: **source_type=url**(url 필수, 크롤링+LLM 파싱, 동일 url이면 캐시 반환, 실패 시 400 CRAWL_FAILED), **source_type=manual**(url 없음, 6개 항목 직접 입력, position_title·company_name 필수, UUID로 항상 신규 저장).
  - 두 경우 모두 **jobs 테이블에 저장**, 응답에 **job_id** 반환. Response에 source_type, cached, created_at 추가. 에러: BAD_REQUEST, CRAWL_FAILED, UNAUTHORIZED.
- **POST /api/job-fit, /api/cover-letter/draft, /api/portfolio/generate** (`API_Service_Spec.md`)
  - 요청을 **parsed_job 객체** 대신 **job_id(string, N)** 만 받도록 변경. job_id 있으면 jobs 테이블에서 조회해 사용, 없으면 공고 맥락 없이 User DB 기준 범용 생성. Request Element 표·curl 예시 모두 job_id 기준으로 수정.
- **DB 스키마** (`AUTOFOLIO_DB_스키마_설계.md`)
  - 2.3 jobs 섹션: "POST /api/jobs/parse 호출 시 항상 저장. source_type=url은 url 기준 중복 체크·캐시 반환, source_type=manual은 url 없이 UUID로 신규 저장"으로 설명 수정.
  - 문서 이력 1.8 추가: jobs 저장 정책 확정(source_type=url / manual), 이후 API는 job_id 단일 입력으로 통일.

#### 자소서 다문항 지원 (draft / inspect · DB 분리)

- **POST /api/cover-letter/draft** (`API_Service_Spec.md`)
  - **Request:** 단일 문항 제거 → **questions**(array&lt;object&gt;, Y). 각 항목: question_text(Y), max_chars(Y), min_chars(N). 공통: job_id(N), tone(N).
  - **Response:** draft_session_id(string), **drafts[]**(draft_id, question_text, answer, char_count), used_assets, created_at. draft_id = DB cover_letter_items.id.
- **POST /api/cover-letter/inspect** (`API_Service_Spec.md`)
  - **Request:** 단일 question_text/answer 제거 → **draft_session_id**(Y), **answers[]**(Y). 각 항목: draft_id(Y), answer(Y). mode(N) 유지.
  - **Response:** inspection_session_id, **feedbacks[]**(draft_id, question_text, score, score_label, strengths, weaknesses, suggestions), overall_score, overall_score_label, inspected_at. 404: 세션 없음.
- **DB 스키마** (`AUTOFOLIO_DB_스키마_설계.md`)
  - **cover_letters** 제거 → **draft_sessions**(2.2) + **cover_letter_items**(2.3). jobs → 2.4, selected_repos → 2.5, asset_hierarchy → 2.6, portfolios → 2.7.
  - draft_sessions: id(PK), user_id, job_id(nullable), tone, created_at/updated_at. API draft_session_id = draft_sessions.id.
  - cover_letter_items: id(PK), session_id(FK), question_text, max_chars, min_chars, answer, round, thread_id, created_at/updated_at. API draft_id = cover_letter_items.id. round로 Inspector 재첨삭 이력 관리.
  - 문서 이력 1.9: 다문항 지원·세션/문항 분리, API 대응, round 설명 반영.

#### 임베딩 API · paths[] · asset_hierarchy 연동

- **POST /api/github/repos/{repo_id}/embedding** (`API_GitHub_Spec.md`)
  - **paths[] 선택 레벨 규칙:** 레포 전체 `["/"]`, 폴더 `["src/", "docs/"]`, 파일 개별 `["src/main.py", "README.md"]`, 혼합 가능. 백엔드: `/` = 전체 순회, 끝 `/` = 폴더 하위 재귀, 파일 경로 = 해당 파일만. 폴더+하위 파일 중복 시 폴더 기준 합산.
  - **전제:** 임베딩은 **selected_repos**에 등록된 레포만 가능. 미등록 repo_id → **403 FORBIDDEN**.
  - **Response:** **hierarchy_nodes_created**(integer) 추가 — asset_hierarchy 생성 노드 수(code+folder+project). 캐시 히트 시 0.
  - **asset_hierarchy 연동 비고:** PUT selected-repos → selected_repos upsert. POST embedding → asset_hierarchy 해당 selected_repo_id 전부 삭제 후 재생성 + ChromaDB upsert. GET embedding/status → 완성 여부 확인. type=project/folder/code, RAPTOR 순서 code→folder→project, asset_hierarchy.id = ChromaDB document id 동일.
- **DB 스키마** (`AUTOFOLIO_DB_스키마_설계.md`)
  - 2.6 asset_hierarchy: **임베딩 API와의 연동** 문단 추가. POST embedding 시 해당 selected_repo_id 행 전부 삭제 후 재생성, id = ChromaDB document id, selected_repos 미등록 레포는 403.
  - 문서 이력 1.10: asset_hierarchy API 연동 설명, selected_repos만 임베딩 가능, id=ChromaDB id 원칙.

---

### 앞으로 할 것

- [x] API 명세서 피드백 반영 — 통합 Full Spec 문서 작성 완료 (추가 피드백 있으면 이어서 반영)
- [ ] GitHub OAuth redirect/callback 구현
- [ ] 토큰 저장(세션/DB) 연동
- [ ] 레포 목록 API 연동
- [ ] 로그인 후 레포 목록 노출 (마일스톤)

---

**레퍼런스:** `docs/API_Full_Spec.md`, `docs/API_Auth_Spec.md`, `docs/API_GitHub_Spec.md`, `docs/API_Service_Spec.md`, `docs/API_Common.md`, `docs/AUTOFOLIO_DB_스키마_설계.md`, `docs/AUTOFOLIO_GitHub_OAuth_가이드.md`

---

## Week 3 추가 — API 명세 전면 수정 및 DB 스키마 개편

**작업 기간:** ~2026-03-16  
**작업자:** Ara5429

### 배경

PR 리뷰(kocory1) 피드백 및 팀 합의를 바탕으로 API 명세서와 DB 스키마를 전면 수정했다.

---

### 확정 결정 사항

| 항목 | 결정 |
|------|------|
| thread_id + round | ✅ 유지 (Inspector Human-in-the-loop MVP 포함) |
| asset_hierarchy.id = path 포함 | ✅ 유지 (ChromaDB 조인 + GitHub API 파일 접근용) |
| Inspector 재첨삭 MVP 포함 | ✅ 포함 |

---

### 수정된 파일 및 주요 변경 내용

#### `docs/AUTOFOLIO_DB_스키마_설계.md` (v1.10 → v1.11)
- draft_sessions + cover_letter_items → **drafts 단일 테이블** (MVP 단순화)
- 제거: tone, min_chars, thread_id → 유지로 재확정, jobs.questions, portfolios.description
- jobs 캐시 정책 제거 (항상 신규 저장)
- ER 다이어그램 전면 업데이트

#### `docs/API_Service_Spec.md`
- **POST /api/jobs/parse:** source_type=url(크롤링) \| manual(직접입력), 항상 jobs 저장 후 job_id 반환
- **POST /api/job-fit:** parsed_job 제거 → job_id 단일 입력, score 0~100 정수
- **POST /api/cover-letter/draft:** questions[] 다문항 입력 → drafts[] 반환, tone/min_chars 제거
- **POST /api/cover-letter/inspect:** answers[] 입력 → feedbacks[] 문항별 피드백, score 0~100
- **POST /api/portfolio/generate:** parsed_job/github_repo_ids 제거 → job_id만, selected_repos SSoT

#### `docs/API_GitHub_Spec.md`
- **GET /embedding/status 엔드포인트 삭제** (동기 처리)
- **POST /embedding:** paths[] 선택 레벨 규칙 비고 추가 (레포/폴더/파일/혼합)
- **POST /embedding:** hierarchy_nodes_created 응답 필드 추가
- **POST /embedding:** selected_repos 미등록 레포 403 에러 추가
- asset_hierarchy 연동 비고 섹션 추가

#### `docs/API_Common.md` / `docs/API_Full_Spec.md` / `docs/API_Auth_Spec.md`
- score_label 기준표 전체 삭제
- embedding/status 시퀀스에서 삭제, 번호 재조정 (8~13 → 8~12)

#### `docs/AUTOFOLIO_Writer_그래프_파이프라인_제안.md` (v1.10 → v1.11)
- API 입력에서 tone, min_chars 제거
- draft_session_id 제거, drafts 단일 테이블 연동으로 변경
- draft API 연동 캐시 문구 제거

#### `docs/AUTOFOLIO_Inspector_그래프_파이프라인_제안.md` (v1.3 → v1.4)
- inspect API 연동: draft_session_id 제거 → answers[].draft_id로 drafts 직접 조회
- score_label 제거, score 0~100 퍼센트로 변경

#### `docs/AUTOFOLIO_디렉토리_구조.md`
- src/db/models.py 테이블 목록: cover_letters → drafts 수정

#### `docs/AUTOFOLIO_User_Asset_스키마_설계.md`
- retrieve_user_assets top_k 기본값: 10 → 20 수정

---

### asset_hierarchy path 설계 근거 (팀 논의 결과)

- asset_hierarchy.id = `"owner/repo/src/auth/login.py"` 처럼 **path 자체를 id로 사용**한다.
- **이유 1:** ChromaDB document id와 동일하게 맞춰 SQLite ↔ ChromaDB 조인이 쉽다.
- **이유 2:** `POST /api/github/repos/{id}/embedding`에서 GitHub `GET /repos/{owner}/{repo}/contents/{path}` 호출 시 path를 그대로 재사용할 수 있다.
- **이유 3:** parent_id만 있으면 트리 구조는 알 수 있지만, 실제 파일 경로 문자열을 완전히 복원할 수 없으므로 id에 path를 포함해 단일 진실원(SSoT)로 둔다.

---

### 남은 작업

- [ ] `src/db/models.py`에 drafts 테이블 정의·마이그레이션 반영 확인
- [ ] `src/api/cover_letter.py`에서 questions[] 요청 / drafts[] 응답 구조 반영
- [ ] `src/api/jobs.py`에서 source_type=`url` \| `manual` 분기 및 저장 정책 구현 (둘 다 jobs 저장 + job_id 반환)
