## Week 4 이슈 정리: Auth + GitHub OAuth

### 목표
1. FastAPI에서 인증 관련 엔드포인트 4개를 실제 동작하도록 구현한다.
2. GitHub OAuth 로직을 서비스 단에서 분리해 유지보수 가능하게 한다.
3. `/api/me`가 로그인 후 세션 기반으로 동작하는지 대충이라도 프론트로 확인한다.
4. OpenAPI를 `docs/openapi.json`로 내보내 문서 동기화를 돕는다.

---

### 구현/수정된 내용

#### 1) SQLite `users` 스키마 확장(팀원 머지 포함)
- `users` 테이블에 아래 컬럼을 추가:
  - `github_id INTEGER`
  - `email TEXT`
  - `avatar_url TEXT`

#### 2) GitHub OAuth 전용 모듈 추가
- `src/service/git_hub/oauth.py`
  - `build_authorize_url(client_id, redirect_uri, state, scope)`
  - `exchange_code_for_token(code, client_id, client_secret, redirect_uri)`
  - `get_github_user(access_token)` (현재 `GET https://api.github.com/user` 호출)

#### 3) Auth API 라우터 구현
- `src/api/auth.py`
  - `GET /api/auth/github/login`
    - 세션에 `oauth_state` 저장(이미 있으면 재사용)
    - GitHub authorize URL로 302 리다이렉트
  - `GET /api/auth/github/callback`
    - `code/state` 누락 시 `400 BAD_REQUEST`
    - 세션 state 검증 후 토큰 교환/유저 조회
    - `users` upsert 수행(실패해도 세션 발급은 계속 진행)
    - `request.session`에 최소 사용자 정보 저장:
      - `user_id`, `github_login`, `github_id`, `email`, `avatar_url`
    - 성공 시 `/dashboard`로 302
  - `GET /api/auth/logout`
    - 세션 clear 후 `/`로 302
  - `GET /api/me`
    - DB 조회 실패/미존재 시 세션 fallback으로 응답
    - 응답 포맷: `{ user_id, github_login, github_id, email, avatar_url }`

#### 4) FastAPI 미들웨어/라우터/메타데이터
- `src/app/main.py`
  - `SessionMiddleware` 추가 및 설정
  - `auth_router` 라우팅 포함
  - OpenAPI 메타데이터(title/description/version/docs/openapi_url) 세팅

#### 5) “아주 대충” 프론트 확인용 페이지
- `src/app/main.py`에 HTML을 임시로 내장:
  - `GET /dashboard`와 `GET /` 제공
  - 로그인/로그아웃 버튼
  - 페이지 로드 시 `fetch('/api/me', { credentials: 'include' })` 결과 출력

#### 6) OpenAPI export 스크립트
- `scripts/export_openapi.py`
  - `app.openapi()`를 `docs/openapi.json`로 저장

#### 7) GitHub API(임베딩 전까지) 라우터 추가
- `src/service/git_hub/repos.py`
  - `list_user_repos`
  - `resolve_repo_owner_repo`
  - `list_repo_files_tree` (Contents API 기반)
  - `get_repo_content` (raw/base64)
  - `list_repo_commits`
- `src/api/github.py`
  - `GET /api/github/repos`
  - `GET /api/user/selected-repos`
  - `PUT /api/user/selected-repos`
  - `GET /api/github/repos/{repo_id}/files`
  - `GET /api/github/repos/{repo_id}/contents`
  - `GET /api/github/repos/{repo_id}/commits`
- `src/service/user/repos.py`
  - `get_selected_repos_detailed`
  - `upsert_selected_repos`
- `src/app/main.py`
  - `github_router` 라우팅 포함

---

### 테스트
- `tests/api/test_auth.py`
  - FastAPI `TestClient` 기반으로 인증 흐름 테스트 추가
  - GitHub 외부 호출은 `unittest.mock.patch`로 mock
  - 실행 결과: `poetry run pytest tests/api/test_auth.py -v`에서 **9/9 PASS**
- `tests/api/test_github_api.py`
  - GitHub 외부 호출은 `unittest.mock.patch`로 mock
  - 선택 레포는 SQLite DB에 직접 저장/조회 검증
  - 실행 결과: `poetry run pytest tests/api/test_github_api.py -v`에서 **9/9 PASS**

---

### 현재 상태에 대한 주의사항(중요)
- 이번 주 구현은 “GitHub OAuth + GitHub user(profile) 조회”까지가 핵심이며,
- 문서에 있는 GitHub REST 라우터 중
  - 레포 목록/선택 레포/파일/콘텐츠/커밋 조회
  - (임베딩 단계 제외)
  까지는 FastAPI 라우팅으로 노출되도록 구현을 완료했다.
- `POST /api/github/repos/{id}/embedding` (임베딩 단계)는 이번 문서 범위에서 제외되어, 다음 단계에서 구현이 필요하다.

---

### 다음 할 일 아이디어
1. `src/api`에 `/api/github/*` 라우터 추가(레포 목록/선택/임베딩) 및 실제 세션 `access_token` 사용 연결
2. 임베딩 API(`POST /api/github/repos/{id}/embedding`) 실제 구현(TDD + mock 외부호출) 진행
3. `print([DEBUG]...)` 로그는 운영용으로 제거/로깅 레벨 전환

