## Autofolio 인증 API 명세

**버전:** 1.0  
**최종 정리일:** 2025-03-09

이 문서는 Autofolio의 **인증 관련 API**(GitHub OAuth 로그인, 로그아웃, 현재 유저 조회)를 정의한다.  
인증이 완료된 뒤 사용하는 GitHub·서비스 API는 각각 `API_GitHub_Spec.md`, `API_Service_Spec.md`를 참고한다.

---

### 공통 규칙

> 공통 요청 형식, 공통 에러 코드, score_label 기준은 `API_Common.md` 참고.

- **인증 흐름:**  
  `GET /api/auth/github/login` → 브라우저가 GitHub OAuth authorize URL로 이동 → 사용자 승인 →  
  `GET /api/auth/github/callback`(code, state 수신) → 서버가 access_token 교환 및 세션 발급 →  
  이후 `GET /api/me`로 현재 로그인 유저 확인, 다른 API는 세션 쿠키 또는 `Authorization: Bearer <app-session-token>`으로 호출.

-- **에러 응답 포맷(공통):**

```json
{
  "error": "ERROR_CODE",
  "message": "사람이 읽을 수 있는 에러 설명"
}
```

---

## 1. GitHub 로그인 시작

### 1.1 GET `/api/auth/github/login`

- **설명:** GitHub OAuth authorize URL로 리다이렉트한다. client_id, redirect_uri, scope, state는 서버에서 자동 생성한다.

#### 1. Request Syntax

```bash
curl -i -X GET "https://example.com/api/auth/github/login"
```

#### 2. Request Header

| Header | 설명 | 필수 |
|--------|------|------|
| (없음) | 쿠키/Authorization 불필요 | N |

#### 3. Request Element

- Path/Query/Body 없음.

#### 4. Response

**302 Found**  
- `Location` 헤더에 GitHub OAuth authorize URL이 담겨 해당 URL로 리다이렉트된다.

| 상태코드 | error | 발생조건 |
|----------|-------|----------|
| 500 | INTERNAL_SERVER_ERROR | GitHub OAuth 환경변수(client_id 등) 미설정 |

> 공통 에러(400/401/403/404/500/502)는 공통 규칙 참고.

---

## 2. GitHub OAuth 콜백

### 2.1 GET `/api/auth/github/callback`

- **설명:** GitHub에서 전달한 `code`, `state`를 받아 access_token을 교환하고 세션을 생성한다. state 불일치 시 400, 성공 시 세션 쿠키를 발급한 뒤 302로 리다이렉트한다.

#### 1. Request Syntax

```bash
curl -i -X GET "https://example.com/api/auth/github/callback?code=abc123&state=xyz789"
```

#### 2. Request Header

| Header | 설명 | 필수 |
|--------|------|------|
| (없음) | 쿠키/Authorization 불필요 | N |

#### 3. Request Element

| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| code | string | Y | GitHub에서 전달하는 인증 코드 |
| state | string | Y | CSRF 방지용 검증 값 |

#### 4. Response

**302 Found**  
- `Location`: `/dashboard` (성공 시 앱 대시보드로 리다이렉트).  
- `Set-Cookie` 헤더로 세션 쿠키 발급.

| 상태코드 | error | 발생조건 |
|----------|-------|----------|
| 400 | BAD_REQUEST | state 불일치 또는 code 누락 |
| 500 | INTERNAL_SERVER_ERROR | GitHub token API 오류 등 서버/외부 오류 |

> 공통 에러(400/401/403/404/500/502)는 공통 규칙 참고.

---

## 3. 로그아웃

### 3.1 GET `/api/auth/logout`

- **설명:** 세션을 무효화하고 로그아웃한다. 이미 세션이 없어도 302를 반환한다.

#### 1. Request Syntax

```bash
curl -i -X GET "https://example.com/api/auth/logout" \
  -H "Cookie: session=..."
```

#### 2. Request Header

| Header | 설명 | 필수 |
|--------|------|------|
| Cookie | 세션 쿠키 (있으면 무효화 대상) | N |

#### 3. Request Element

- Path/Query/Body 없음. 세션 쿠키만 사용.

#### 4. Response

**302 Found**  
- `Location`: `/` (루트로 리다이렉트).

| 상태코드 | error | 발생조건 |
|----------|-------|----------|
| (없음) | — | 에러 응답 없음, 항상 302 반환 |

---

## 4. 현재 유저 조회

### 4.1 GET `/api/me`

- **설명:** 현재 로그인한 유저 정보를 반환한다. 사용자 식별은 세션 쿠키 또는 `Authorization: Bearer <app-session-token>`에서 서버가 추출한다.

#### 1. Request Syntax

```bash
curl -X GET "https://example.com/api/me" \
  -H "Authorization: Bearer <app-session-token>"
```

#### 2. Request Header

| Header | 설명 | 필수 |
|--------|------|------|
| Cookie | 세션 쿠키 (인증된 경우) | Cookie 또는 Authorization 중 하나 필수 |
| Authorization | `Bearer <app-session-token>` | Cookie 또는 Authorization 중 하나 필수 |

#### 3. Request Element

- Path/Query/Body 없음.

#### 4. Response

**200 OK**

```json
{
  "user_id": "uuid-internal-12345",
  "github_login": "Ara5429",
  "github_id": 12345678,
  "email": "user@example.com",
  "avatar_url": "https://avatars.githubusercontent.com/u/12345678?v=4"
}
```

| 필드 | 타입 | 설명 |
|------|------|------|
| user_id | string | 내부 사용자 식별자 |
| github_login | string | GitHub 로그인 아이디 |
| github_id | integer | GitHub 유저 numeric ID |
| email | string | 이메일 주소 |
| avatar_url | string | 프로필 이미지 URL |

| 상태코드 | error | 발생조건 |
|----------|-------|----------|
| 401 | UNAUTHORIZED | 세션 없음 또는 만료 |

> 공통 에러(400/401/403/404/500/502)는 공통 규칙 참고.

---

## API 사용 시퀀스

1. GET /api/auth/github/login — GitHub 로그인 시작 (Auth)
2. GET /api/auth/github/callback — 세션 발급 완료 (Auth)
3. GET /api/me — 유저 정보 확인 (Auth)
4. GET /api/github/repos — 레포 목록 조회 (GitHub)
5. PUT /api/user/selected-repos — 레포 선택 저장 (GitHub)
6. POST /api/user/documents — 이력서/포트폴리오 업로드 (Service, 선택)
7. POST /api/github/repos/{id}/embedding — 임베딩 생성 (GitHub)
8. GET /api/github/repos/{id}/embedding/status — 임베딩 완료 확인 (GitHub)
9. POST /api/jobs/parse — 채용공고 입력·저장 (Service). 응답 job_id는 10·11·13번에서 선택 사용
10. POST /api/job-fit — 적합도 점수 확인 (Service)
11. POST /api/cover-letter/draft — 자소서 초안 생성 (Service)
12. POST /api/cover-letter/inspect — 자소서 검수 (Service)
13. POST /api/portfolio/generate — 포트폴리오 생성 (Service)

6번(문서 업로드)은 선택 단계이며, 이력서/포트폴리오 문서가 없어도 자소서·포트폴리오 생성은 GitHub 임베딩만으로 진행 가능하다.
