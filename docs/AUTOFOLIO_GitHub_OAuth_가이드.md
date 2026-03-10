# Autofolio GitHub OAuth 가이드

**문서 버전:** 1.0  
**기준:** [AUTOFOLIO_API_스펙.md](AUTOFOLIO_API_스펙.md), [API_GitHub_Portfolio_Spec.md](API_GitHub_Portfolio_Spec.md)

---

## 1. 개요

Autofolio는 **Web Application Flow**로 GitHub 로그인을 구현한다.  
유저가 "GitHub로 연결" 클릭 → GitHub 인증 → 콜백으로 `code` 수신 → `access_token` 교환 → API 호출에 사용.

> 참고: GitHub는 **GitHub App**을 새 프로젝트에 추천하지만, OAuth App이 구현이 더 단순하다. MVP는 OAuth App으로 시작해도 무방.

---

## 2. OAuth App 등록

1. **GitHub** → 프로필 사진 → **Settings** → **Developer settings** → **OAuth Apps** → **New OAuth App**
2. 입력:
   - **Application name**: Autofolio (또는 서비스명)
   - **Homepage URL**: `https://your-domain.com`
   - **Authorization callback URL**: `https://your-domain.com/api/auth/github/callback`  
     (로컬: `http://localhost:3000/api/auth/github/callback` 등)
3. **Register application** 클릭
4. **Client ID** 확인 (공개 가능)
5. **Generate a new client secret** → **Client Secret** 복사 (한 번만 표시, 안전하게 보관)

> Callback URL은 **하나만** 등록 가능. 개발/운영이 다르면 환경별로 앱을 따로 만들거나, 프론트에서 redirect_uri를 넘기는 방식으로 처리.

---

## 3. Web Application Flow (3단계)

### Step 1: 유저를 GitHub 인증 페이지로 보내기

**요청 (리다이렉트):**

```
GET https://github.com/login/oauth/authorize
```

| 파라미터 | 필수 | 설명 |
|----------|------|------|
| `client_id` | ✅ | OAuth App의 Client ID |
| `redirect_uri` | 강력 권장 | 콜백 URL (앱에 등록한 것과 일치) |
| `scope` | 선택 | 권한 범위 (아래 참고) |
| `state` | 강력 권장 | CSRF 방지용 랜덤 문자열 (세션/쿠키에 저장 후 검증) |
| `code_challenge` | 권장 | PKCE용 (아래 참고) |
| `code_challenge_method` | 권장 | `S256` |

**예시 URL:**

```
https://github.com/login/oauth/authorize?client_id=YOUR_CLIENT_ID&redirect_uri=https://your-domain.com/api/auth/github/callback&scope=repo%20read:user&state=RANDOM_STATE_STRING
```

유저가 허용하면 GitHub가 **redirect_uri**로 리다이렉트하며 `code`와 `state`를 쿼리로 넘긴다.

---

### Step 2: code로 access_token 받기

**GitHub가 리다이렉트하는 URL 예:**

```
https://your-domain.com/api/auth/github/callback?code=abc123...&state=RANDOM_STATE_STRING
```

1. **state 검증**: 저장해 둔 state와 일치하는지 확인 (CSRF 방지)
2. **code**로 토큰 요청 (이 요청은 **반드시 백엔드**에서 수행, client_secret 노출 금지):

```
POST https://github.com/login/oauth/access_token
Content-Type: application/json
Accept: application/json
```

**Body (JSON):**

| 필드 | 필수 | 설명 |
|------|------|------|
| `client_id` | ✅ | Client ID |
| `client_secret` | ✅ | Client Secret |
| `code` | ✅ | 콜백으로 받은 code (10분 만료) |
| `redirect_uri` | 강력 권장 | Step 1에서 썼던 것과 동일 |
| `code_verifier` | PKCE 썼을 때 | Step 1의 code_challenge를 만든 원본 값 |

**응답 예 (Accept: application/json):**

```json
{
  "access_token": "gho_xxxx...",
  "token_type": "bearer",
  "scope": "repo,read:user"
}
```

---

### Step 3: access_token으로 API 호출

**유저 정보 조회:**

```
GET https://api.github.com/user
Authorization: Bearer gho_xxxx...
```

**레포 목록 조회 (Autofolio 핵심):**

```
GET https://api.github.com/user/repos
Authorization: Bearer gho_xxxx...
```

이 토큰을 세션/DB에 저장해 두고, 레포 목록·코드·커밋 조회 시 사용.

---

## 4. Autofolio에 필요한 Scope

| Scope | 용도 |
|-------|------|
| `read:user` | 로그인 유저 식별 (이메일, 로그인 ID 등) |
| `repo` | 비공개 포함 전체 레포 접근 (레포 목록, 코드, 커밋) |

공개 레포만 쓰면 `public_repo`로 줄일 수 있음. 비공개도 보여주려면 `repo`.

**요청 예:**

```
scope=read:user repo
```

---

## 5. PKCE (권장)

Authorization Code를 가로채도 토큰 교환을 못 하게 하려면 PKCE 사용.

1. **code_verifier**: 랜덤 문자열 (43~128자)
2. **code_challenge**: `BASE64URL(SHA256(code_verifier))`
3. Step 1에서 `code_challenge`, `code_challenge_method=S256` 전달
4. Step 2에서 `code_verifier` 전달 (code_verifier는 세션 등에 보관)

---

## 6. 백엔드 구현 포인트

| 단계 | 담당 | 비고 |
|------|------|------|
| Step 1 | FE 또는 BE | 유저를 `authorize` URL로 리다이렉트. state, PKCE 값 생성 후 세션/쿠키에 저장 |
| Step 2 | **BE만** | `access_token` 요청 시 **client_secret** 사용 → BE에서만 처리 |
| Step 3 | BE | 토큰으로 `GET /user`, `GET /user/repos` 등 호출 |

- **client_secret**은 환경 변수로 관리, 프론트/클라이언트에 노출 금지.
- **access_token** 저장 시 암호화·만료 정책 고려 (GitHub OAuth 토큰은 만료 없음이지만, 재발급·폐기 정책은 서비스에서 정의).

---

## 7. Redirect URL 규칙 (GitHub 정리)

- `redirect_uri`를 넘기면, 그 값의 **host + port**가 OAuth App에 등록한 Callback URL과 **일치**해야 함.
- **path**는 등록한 path의 **서브경로**까지 허용.

예: Callback이 `https://example.com/auth/callback` 이면  
- ✅ `https://example.com/auth/callback`  
- ✅ `https://example.com/auth/callback/extra`  
- ❌ `https://example.com/other`

---

## 8. 참고 링크

- [Authorizing OAuth Apps (GitHub Docs)](https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/authorizing-oauth-apps)
- [Creating an OAuth App](https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/creating-an-oauth-app)
- [Scopes for OAuth apps](https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/scopes-for-oauth-apps)

---

## 9. 문서 관계

- API 스펙: [AUTOFOLIO_API_스펙.md](AUTOFOLIO_API_스펙.md)
- GitHub API 명세: [API_GitHub_Portfolio_Spec.md](API_GitHub_Portfolio_Spec.md)

---

## 10. 문서 이력

- 1.0 (2026-02-12): 초안. Web Application Flow, 등록, scope, PKCE, BE 역할 정리.
