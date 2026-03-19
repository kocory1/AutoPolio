## Autofolio Auth API 테스트 이슈 정리

**버전:** 1.0  
**작성일:** 2026-03-16

### 1. 배경

GitHub OAuth 기반 로그인 플로우 구현에 앞서, FastAPI 레벨에서 인증 관련 엔드포인트의 동작을 보장하기 위해 API 단위 테스트를 추가/정비했다.  
DB 스키마 변경(`users` 테이블 확장)과 세션 미들웨어 도입이 함께 이루어져, 이를 통합적으로 검증하는 테스트가 필요했다.

---

### 2. 관련 변경 사항 요약

- **DB 스키마 (`users` 테이블)**
  - 컬럼 추가:
    - `github_id INTEGER`
    - `email TEXT`
    - `avatar_url TEXT`

- **GitHub OAuth 전용 모듈**
  - 파일: `src/service/git_hub/oauth.py`
  - 주요 함수:
    - `build_authorize_url(client_id, redirect_uri, state, scope="read:user user:email")`
    - `async exchange_code_for_token(code, client_id, client_secret, redirect_uri)`
    - `async get_github_user(access_token)`

- **Auth 라우터 추가**
  - 파일: `src/api/auth.py`
  - 엔드포인트:
    - `GET /api/auth/github/login`
    - `GET /api/auth/github/callback`
    - `GET /api/auth/logout`
    - `GET /api/me`
  - 공통 특징:
    - `response_model=None` 명시
    - 에러 형식: `{"error": "ERROR_CODE", "message": "설명"}`

- **FastAPI 엔트리포인트 수정**
  - 파일: `src/app/main.py`
  - 변경점:
    - `SessionMiddleware` 추가 (`secret_key = SESSION_SECRET or "dev-secret"`)
    - `auth_router` 등록
    - FastAPI 메타데이터 설정:
      - `title="Autofolio API"`
      - `description="From Code to Career — 증거 기반 개발자 이력서 생성 서비스"`
      - `version="1.0.0"`
      - `docs_url="/docs"`, `openapi_url="/openapi.json"`

---

### 3. 테스트 파일 개요 (`tests/api/test_auth.py`)

- **공통 설정**
  - `TestClient` 사용, `follow_redirects=False`로 302 직접 검증
  - `unittest.mock.patch`로 GitHub 외부 호출 mock
  - `SessionMiddleware`와 동일한 포맷으로 세션 쿠키 생성:
    - `TimestampSigner("dev-secret")` + base64-encoded JSON payload
  - `mock_env` fixture:
    - `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`, `GITHUB_REDIRECT_URI` 환경변수 세팅

- **세션 헬퍼**
  - Starlette `SessionMiddleware`가 사용하는 형식에 맞게 테스트에서 직접 세션 쿠키 생성:
    - `payload = b64encode(json.dumps(data).encode()).decode()`
    - `signed = TimestampSigner(secret_key).sign(payload)`
    - `client.cookies.set("session", signed)`

---

### 4. 개별 테스트 케이스

#### 4.1 `GET /api/auth/github/login`

1. **`test_login_returns_302`**
   - 환경:
     - `mock_env`로 GitHub OAuth 환경변수 세팅
   - 요청:
     - `GET /api/auth/github/login` (`follow_redirects=False`)
   - 기대:
     - `status_code == 302`

2. **`test_login_location_contains_github`**
   - 환경:
     - `mock_env`
   - 요청:
     - `GET /api/auth/github/login`
   - 기대:
     - `response.headers["location"]`에  
       `"github.com/login/oauth/authorize"` 포함

#### 4.2 `GET /api/auth/github/callback`

3. **`test_callback_success`**
   - 환경:
     - 세션: `_set_session(client, {"oauth_state": "test_state"})`
     - `mock_env`
     - Mock 대상 (함수 직접 import 기준):
       - `patch("src.api.auth.exchange_code_for_token", return_value="test_access_token")`
       - `patch("src.api.auth.get_github_user", {...})`
   - 요청:
     - `GET /api/auth/github/callback?code=test_code&state=test_state`
   - 기대:
     - `status_code == 302`
     - `Location == "/dashboard"`
     - `exchange_code_for_token`, `get_github_user` 각 1회 호출
   - 구현상 포인트:
     - `users` upsert 시 DB 오류가 나도 `try/except`로 예외를 잡고, 세션 발급/리다이렉트는 계속 진행.

4. **`test_callback_invalid_state`**
   - 환경:
     - 세션: `_set_session(client, {"oauth_state": "correct_state"})`
   - 요청:
     - `GET /api/auth/github/callback?code=test_code&state=wrong_state`
   - 기대:
     - `status_code == 400`
     - `body["error"] == "BAD_REQUEST"`

5. **`test_callback_missing_code`**
   - 환경:
     - 세션 없음
   - 요청:
     - `GET /api/auth/github/callback?state=test_state` (code 누락)
   - 기대:
     - `status_code == 400`
     - `body["error"] == "BAD_REQUEST"`

#### 4.3 `GET /api/auth/logout`

6. **`test_logout_always_302`**
   - 환경:
     - 세션 없이 호출
   - 요청:
     - `GET /api/auth/logout`
   - 기대:
     - `status_code == 302`

7. **`test_logout_redirects_to_root`**
   - 요청:
     - `GET /api/auth/logout`
   - 기대:
     - `response.headers["location"] == "/"`

#### 4.4 `GET /api/me`

8. **`test_me_authenticated`**
   - 환경:
     - `_set_session`으로 아래 값 저장:
       - `user_id = "test-user-id"`
       - `github_login = "testuser"`
       - `github_id = 12345`
       - `email = "test@example.com"`
       - `avatar_url = "https://avatars.githubusercontent.com/u/12345"`
   - 구현:
     - `auth.py`의 `/api/me`는 우선 DB에서 `users` 조회를 시도하고, 예외/미존재 시 세션 정보를 fallback으로 사용.
   - 요청:
     - `GET /api/me`
   - 기대:
     - `status_code == 200`
     - 응답 바디:
       - `user_id == "test-user-id"`
       - `github_login == "testuser"`
       - `github_id == 12345`
       - `email == "test@example.com"`
       - `avatar_url == "https://avatars.githubusercontent.com/u/12345"`

9. **`test_me_unauthorized`**
   - 환경:
     - 세션 없음
   - 요청:
     - `GET /api/me`
   - 기대:
     - `status_code == 401`
     - `body["error"] == "UNAUTHORIZED"`

---

### 5. 최종 결과 및 메모

- 실행: `poetry run pytest tests/api/test_auth.py -v`
- 결과:
  - **9개 테스트 전부 PASS**
  - 경고 2개: `connect()` coroutine 미-await 관련 런타임 워닝 (테스트 동작에는 영향 없음, 추후 비동기 DB 유틸 정리 시 함께 정리 가능)

### 6. 후속 작업 아이디어

- `/api/me`에서 DB 조회와 세션 fallback 로직을 별도 서비스 함수로 분리해 재사용성/테스트 용이성 향상.
- Auth 라우터에 대한 통합 테스트를 추가해, 실제 GitHub OAuth App과 연동되는 end-to-end 플로우도 검증(로컬/스테이징 환경 기준).

