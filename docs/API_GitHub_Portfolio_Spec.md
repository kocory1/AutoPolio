## GitHub OAuth & 포트폴리오 API 명세 (초안)

이 문서는 RCV 인턴 Week2 이슈 `week2-github-api-spec.md` 기반으로 정리한
**GitHub OAuth · 레포/커밋 조회 · 임베딩/포트폴리오용 API 명세서 초안**이다.

**레퍼런스:** `AUTOFOLIO_16주_계획표.md`, `AUTOFOLIO_LangGraph_설계.md`, `AUTOFOLIO_임베딩전략.md`, week1-github-oauth, week2-github-api-spec.

---

### API 목차 (전체)

| 구분 | 메서드 | 경로 | 설명 |
|------|--------|------|------|
| 인증 | GET | `/api/auth/github/login` | GitHub OAuth 시작(리다이렉트) |
| 인증 | GET | `/api/auth/github/callback` | OAuth 콜백, 토큰 교환·세션 생성 |
| 인증 | GET | `/api/auth/logout` | 로그아웃 |
| 인증 | POST | `/api/auth/github/disconnect` | GitHub 연동 해제(토큰 삭제, **MVP 이후 TODO**) |
| 유저 | GET | `/api/me` | 현재 로그인 유저 정보 |
| 유저 | GET / PUT | `/api/user/selected-repos` | 선택 레포 목록 조회/저장 |
| GitHub | GET | `/api/github/repos` | 로그인 유저 레포 목록 |
| GitHub | GET | `/api/github/repos/{id}` | 레포 단건 상세 |
| GitHub | GET | `/api/github/repos/{id}/files` | 레포 파일/폴더 트리 |
| GitHub | GET | `/api/github/repos/{id}/contents` | 특정 파일 raw 내용(코드/문서 읽기) |
| GitHub | GET | `/api/github/repos/{id}/commits` | 커밋 목록(author 필터 가능) |
| GitHub | POST | `/api/github/repos/{id}/embedding` | 임베딩 생성/갱신 요청(비동기) |

**공통 인증:** 세션 쿠키 또는 `Authorization: Bearer <app-session-token>`.  
**공통 상태코드:** 200 정상, 302 리다이렉트, 400 잘못된 요청, 401 미인증, 403 권한 없음, 404 없음, 500 서버 오류, 502 Upstream(GitHub) 오류.

---

### 1. 인증 흐름 (OAuth)

#### 1.1 `GET /api/auth/github/login`

- **역할**: GitHub OAuth authorize URL로 리다이렉트.
- **요청**
  - 쿼리 없음 (서버가 `client_id`, `redirect_uri`, `scope`, `state` 생성).
- **응답**
  - `302 Found` → `https://github.com/login/oauth/authorize?...`
- **에러**
  - `500 INTERNAL_SERVER_ERROR`: 서버 설정 오류 (env 미설정 등).

#### 1.2 `GET /api/auth/github/callback`

- **역할**: GitHub에서 `code`, `state`를 받고 access_token 교환.
- **요청 쿼리**
  - `code`: string (필수)
  - `state`: string (필수, CSRF 방지용)
- **동작**
  - 세션에 저장해 둔 `state`와 비교 → 불일치 시 400.
  - `code`로 GitHub `access_token` 교환.
  - 내부 `user_id`를 발급/조회 후 DB에 GitHub 토큰 저장.
- **응답**
  - `302 Found` → 프론트엔드 (예: `/dashboard`)
  - 세션/쿠키에 로그인 상태 저장 (예: 내부 `session_id`).
- **에러**
  - `400 BAD_REQUEST`: state 불일치, code 누락.
  - `500 INTERNAL_SERVER_ERROR`: GitHub API 오류 등.

#### 1.3 `GET /api/auth/logout`

- **역할**: 세션 무효화, 로그아웃.
- **요청**: 쿠키/세션.
- **응답**: `302` → 로그인 페이지 또는 `/`.
- **에러**: 없음(세션 없어도 302).

#### 1.4 `POST /api/auth/github/disconnect` (MVP 이후 TODO)

- **역할**: GitHub 연동 해제. DB에서 해당 유저의 GitHub access_token 삭제.  
  - **MVP에서는 구현하지 않고**, 로그아웃만 제공한다.
- **요청**: 쿠키/세션.
- **응답(향후 계획)**: `200` + `{"ok": true}` 또는 `302` → 설정/대시보드.
- **에러(향후 계획)**: `401` 세션 없음.

---

### 2. 유저/선택 레포 API

#### 2.0 `GET /api/me`

- **역할**: 현재 로그인 유저 정보(내부 user_id, GitHub login, 이메일 등).
- **요청**: 세션 쿠키 또는 `Authorization: Bearer <app-session-token>`.
- **응답 200 예시**

```json
{
  "user_id": "uuid-internal",
  "github_login": "Ara5429",
  "github_id": 174741358,
  "email": "user@example.com",
  "avatar_url": "https://avatars.githubusercontent.com/..."
}
```

- **에러**: `401` 세션 없음.

#### 2.0-2 `GET /api/user/selected-repos`

- **역할**: 유저가 “선택한 레포” 목록 조회(포트폴리오/임베딩 대상).
- **요청**: 세션.
- **응답 200 예시**

```json
{
  "selected_repos": [
    { "id": 123, "full_name": "Ara5429/subway-rag-chatbot" }
  ]
}
```

#### 2.0-3 `PUT /api/user/selected-repos`

- **역할**: 선택 레포 목록 저장(덮어쓰기).
- **요청 본문**: `{"repo_ids": [123, 456]}` 또는 `{"full_names": ["owner/repo1"]}`.
- **응답**: `200` + 동일 스키마 또는 `{"ok": true}`.
- **에러**: `400` 잘못된 형식, `401` 세션 없음.

---

### 3. 레포/커밋/파일 조회 API

#### 3.1 `GET /api/github/repos`

- **역할**: 로그인 유저의 GitHub 레포 목록 조회.
- **요청 헤더**
  - 세션 쿠키 또는 `Authorization: Bearer <app-session-token>`.
- **쿼리 파라미터**
  - `per_page`: integer, 옵션, 기본=30 — 페이지당 레포 수.
  - `page`: integer, 옵션, 기본=1 — 페이지 번호(1-base).
  - `sort`: string, 옵션, 기본=`pushed` — `created` \| `updated` \| `pushed` \| `full_name`.
  - `direction`: string, 옵션, 기본=`desc` — `asc` \| `desc`.
  - `type`: string, 옵션, 기본=`owner` — `all` \| `owner` \| `member`.
- **응답 200 예시**

```json
{
  "repos": [
    {
      "id": 123,
      "full_name": "Ara5429/subway-rag-chatbot",
      "description": "지하철 경로 안내 RAG 챗봇",
      "private": false,
      "language": "Python",
      "stargazers_count": 10,
      "forks_count": 1,
      "pushed_at": "2026-02-20T12:34:56Z"
    }
  ]
}
```

- **에러**
  - `401 UNAUTHORIZED`: 세션 없음/만료.
  - `502 BAD_GATEWAY`: GitHub API 실패.

#### 3.2 `GET /api/github/repos/{id}`

- **역할**: 레포 단건 상세(메타데이터, default_branch, language 등). 레포 선택/임베딩 대상 확인용.
- **요청**: 세션. Path `id`는 레포 ID 또는 `owner/repo` 문자열.
- **응답 200**: GitHub `/repos/{owner}/{repo}` 응답 필드 중 필요한 것만 정제( id, full_name, description, private, language, stargazers_count, forks_count, default_branch, pushed_at 등).
- **에러**: `403` 권한 없음, `404` 없음, `502` GitHub 오류.

#### 3.3 `GET /api/github/repos/{id}/commits`

- **역할**: 특정 레포의 커밋 목록 조회. **author 필터로 “내 커밋만” 집계 가능.**
- **요청 파라미터**
  - `id`: 내부에서 `owner/repo`로 매핑되는 레포 식별자.
- **쿼리**
  - `author` (옵션): GitHub 로그인 ID 또는 이메일. 기본값=현재 로그인 유저.
  - `path` (옵션): 특정 파일/디렉터리만 보고 싶을 때.
- **응답 200 예시**

```json
{
  "commits": [
    {
      "sha": "abc123...",
      "message": "feat: RAG 검색 성능 개선",
      "author": {
        "login": "Ara5429",
        "name": "Ara",
        "email": "example@example.com"
      },
      "html_url": "https://github.com/owner/repo/commit/abc123...",
      "files_changed": 5,
      "date": "2026-02-10T09:00:00Z"
    }
  ]
}
```

- **에러**
  - `403 FORBIDDEN`: 접근 권한 없는 레포.
  - `502 BAD_GATEWAY`: GitHub API 실패.

#### 3.4 `GET /api/github/repos/{id}/files`

- **역할**: 레포 파일/디렉터리 트리 조회 (임베딩·포트폴리오 대상 선택에 사용).
- **쿼리**
  - `path` (옵션, 기본="/"): 조회 시작 디렉터리.
  - `depth` (옵션): 최대 깊이 제한.
- **응답 200 예시**

```json
{
  "tree": [
    {"path": "README.md", "type": "file"},
    {"path": "src/", "type": "dir"},
    {"path": "src/app/main.py", "type": "file"}
  ]
}
```

- **에러**: `403`, `404`, `502`.

#### 3.5 `GET /api/github/repos/{id}/contents`

- **역할**: 특정 **파일**의 raw 내용 조회(코드/문서 읽기). `AUTOFOLIO_임베딩전략.md`의 Leaf 레벨·RAPTOR 수집에 사용.
- **쿼리**
  - `path`: string (필수). 예: `README.md`, `src/main.py`.
- **응답**: `200` + 본문은 **텍스트** (Content-Type: text/plain 또는 application/octet-stream). 또는 JSON으로 `{"content": "base64..."}` 디코딩해서 사용.
- **에러**: `400` path 누락, `404` 파일 없음, `403` 권한 없음, `502` GitHub 오류.
- **비고**: 디렉터리 path면 트리 목록 반환(동일 시 `GET .../files?path=` 로 통일 가능).

---

### 4. 임베딩 API (RAPTOR 폴더 기반 설계와 연계)

#### 4.1 `POST /api/github/repos/{id}/embedding`

- **역할**: 특정 레포(or 서브트리)에 대한 임베딩 생성/갱신 요청.
- **요청 본문 예시**

```json
{
  "paths": ["src/", "README.md"],
  "strategy": "code_and_docs_v1"
}
```

- **응답 202 예시**

```json
{
  "status": "queued",
  "job_id": "embed_20260303_001",
  "repo_id": 123
}
```

- **비고**
  - 실제 임베딩 생성은 LangGraph/Worker에서 비동기로 처리.
  - `AUTOFOLIO_임베딩전략.md`의 폴더 기반 RAPTOR 구조에 맞춰,
    - `src/github_embedding/embedding/` 패키지가
      - GitHub 트리 → 청크 생성
      - LLM 요약 → 임베딩 생성/저장
      - 조회 인터페이스를 담당.

---

### 5. 로컬 실험 코드 vs 실서비스 백엔드 로직

| 구분 | 파일 | 역할 | 실서비스에서의 위치 |
|------|------|------|---------------------|
| 로컬 실험 | `scripts/github_oauth_local_test.py` | 브라우저 열어서 OAuth 플로우 전체를 내 PC에서 테스트 | FastAPI의 `/api/auth/github/login`, `/callback`으로 기능 이전 |
| 로컬 실험 | `scripts/github_repo_describe_practice.py` | access_token으로 레포/README 읽고 LLM으로 설명 생성 | `/api/github/repos`, `/api/github/repos/{id}/files` + LangGraph/Writer 그래프 조합으로 대체 |
| 로컬 실험 | `scripts/github_code_and_commits_experiment.py` | README 말고 **실제 코드 파일** 내용 읽기, **타인 레포**에서 `author=본인` 으로 내 커밋만 조회 가능 여부 검증 | 코드 읽기 → Contents API(raw), 내 커밋만 → `/repos/{o}/{r}/commits?author=login` 로 서비스 API에 반영 |
| 서비스 유틸 | `src/github_embedding/login/__init__.py` | GitHub OAuth·레포/커밋/트리 조회 함수 모음 | FastAPI 라우터에서 직접 호출하는 “서비스 계층” 유틸 |
| 서비스 유틸(계획) | `src/github_embedding/embedding/` | 트리→청크, 요약·임베딩 생성 | 임베딩 생성 API와 LangGraph 노드에서 사용 |

요약하면:

- **Week1**: 스크립트로 OAuth·GitHub API를 **로컬에서 검증**.
- **Week2**:  
  - `src/github_embedding/login`에 공용 유틸 함수로 정리.  
  - 이 명세서 + FastAPI 라우터에서 이 유틸을 사용해 **실제 서비스 API**로 승격시키는 단계.

