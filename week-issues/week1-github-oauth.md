## Week1 - GitHub OAuth 프로젝트 셋업

**주차 목표**
- GitHub OAuth 기반 로그인 플로우를 설계하고, 로컬 환경에서 Web Application Flow를 한 번 끝까지 태워본다.
- `AUTOFOLIO_GitHub_OAuth_가이드.md` 내용을 실제 코드/환경에 녹이기 위한 작업 계획 수립.

**이번 주 작업 범위**
1. GitHub OAuth: 프로젝트 셋업 공유
2. GitHub OAuth App 등록 (MVP 기준 OAuth App 우선)
3. 로컬 로그인 플로우 테스트 (`/authorize` → `callback` → `access_token` → `/user`, `/user/repos`)

---

### 1. 레퍼런스 문서 요약
- Web Application Flow 사용: `authorize` → `access_token` 교환 → GitHub API 호출.
- Client Secret은 반드시 백엔드에서만 사용하고, 환경 변수로 관리.
- 권장 Scope: `read:user`, `repo` (공개만이면 `public_repo`로 축소 가능).
- CSRF 방지를 위해 `state`, 보안 강화를 위해 PKCE(`code_verifier`, `code_challenge`) 사용 권장.
- 콜백 URL은 GitHub OAuth App에 등록된 host/port와 일치해야 함.

---

### 2. 이번 주 TODO
- [x] GitHub OAuth App 생성 (로컬용 Callback: `http://localhost:8000/callback` 등록)
- [x] 로컬 환경용 Client ID / Client Secret을 환경 변수로 세팅 (`GITHUB_OAUTH_CLIENT_ID`, `GITHUB_OAUTH_CLIENT_SECRET`)
- [x] 로컬 테스트 스크립트에서 `code` → `access_token` 교환 및 `GET /user`, `GET /user/repos` 호출까지 플로우 검증
- [ ] GitHub 로그인 시작 엔드포인트 설계 (`/api/auth/github/login` 또는 유사 경로)
- [ ] GitHub 콜백 엔드포인트 설계 (`/api/auth/github/callback`)
- [ ] 프로젝트 구조에 맞춰 OAuth 플로우를 백엔드 코드로 이식 (테스트 스크립트 → 실제 API 레이어)
- [ ] 토큰 저장/세션 전략 초안 정리 (DB/세션/쿠키 등) 및 문서화

---

### 3. 진행 로그
- 2026-02-26
  - [x] 원격 `main` 기준 코드 업데이트 확인 (`git fetch origin` → up to date)
  - [x] 브랜치 생성: `feature/github-oauth-login`
  - [x] GitHub OAuth 가이드 문서 정독 및 핵심 포인트 정리 (본 문서 1, 2절)
  - [x] 로컬 Web Application Flow 테스트 스크립트 초안 작성 (`scripts/github_oauth_local_test.py`)
    - 환경 변수: `GITHUB_OAUTH_CLIENT_ID`, `GITHUB_OAUTH_CLIENT_SECRET`
    - Redirect URI: `http://localhost:8000/callback`
    - Flow: authorize → callback(code,state) → access_token 교환 → `/user`, `/user/repos` 호출
  - [x] 실제 GitHub 계정(`Ara5429`)으로 OAuth 플로우 실행 및 유저 정보/레포 목록 조회 성공
    - 확인한 레포 예시: `2025_AI_PROJECT3`, `fastapi`, `langchain-kr`, `modern-software-dev-assignments`, `subway-rag-chatbot`
