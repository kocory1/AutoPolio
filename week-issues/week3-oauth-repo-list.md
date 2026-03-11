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
