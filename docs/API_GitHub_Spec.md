## Autofolio GitHub API 명세

**버전:** 1.0  
**최종 정리일:** 2025-03-04

이 문서는 Autofolio에서 사용하는 **GitHub 연동 전용 API**를 정리한 것이다.  
인증(/api/auth/github/*, /api/me 등)은 별도 문서를 따르고, 여기서는 GitHub 레포·파일·커밋·임베딩 관련 엔드포인트만 다룬다.  
선택 레포 조회/저장은 `/api/user/selected-repos`(User API)로 제공한다.

---

### 공통 규칙

> 공통 요청 형식, 공통 에러 코드, score_label 기준은 `API_Common.md` 참고.

- **Base URL (GitHub):** `/api/github`
- **Base URL (User·선택 레포):** `/api/user`
- **인증:** 세션 쿠키 또는 `Authorization: Bearer <app-session-token>`
- **에러 응답 포맷(공통):**

```json
{
  "error": "ERROR_CODE",
  "message": "사람이 읽을 수 있는 에러 설명"
}
```

---

## 1. 레포지토리 목록

### 1.1 GET `/api/github/repos`

- **설명:** 로그인 유저의 GitHub 레포 목록 조회  
- **비고:** sort / direction / type 은 서버 고정값으로 처리되며, 클라이언트는 노출하지 않는다.

#### 1. Request Syntax

```bash
curl -X GET "https://example.com/api/github/repos?page=1&per_page=30" \
  -H "Authorization: Bearer <app-session-token>"
```

#### 2. Request Header

| Header | 설명 | 필수 |
|--------|------|------|
| Cookie | 세션 쿠키 (인증된 경우) | Cookie 또는 Authorization 중 하나 필수 |
| Authorization | `Bearer <app-session-token>` | Cookie 또는 Authorization 중 하나 필수 |

#### 3. Request Element

| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| page | integer | N | 페이지 번호(1-base), default=1 |
| per_page | integer | N | 페이지당 레포 수, default=30 |

#### 4. Response

**200 OK**

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
      "default_branch": "main",
      "pushed_at": "2026-02-20T12:34:56Z"
    }
  ],
  "page": 1,
  "per_page": 30,
  "total_count": 42
}
```

| 상태코드 | error | 발생조건 |
|----------|-------|----------|
| 401 | UNAUTHORIZED | 세션 만료 또는 미인증 |
| 502 | GITHUB_UPSTREAM_ERROR | GitHub 레포 목록 조회 실패 |

> 공통 에러(400/401/403/404/500/502)는 공통 규칙 참고.

---

## 2. 선택 레포 (User API)

### 2.1 GET `/api/user/selected-repos`

- **설명:** 현재 로그인 유저가 포트폴리오/임베딩 대상으로 선택한 레포 목록 조회

#### 1. Request Syntax

```bash
curl -X GET "https://example.com/api/user/selected-repos" \
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
  "selected_repos": [
    { "id": 123, "full_name": "Ara5429/subway-rag-chatbot" },
    { "id": 456, "full_name": "kocory1/AutoPolio" }
  ]
}
```

| 상태코드 | error | 발생조건 |
|----------|-------|----------|
| 401 | UNAUTHORIZED | 로그인 필요 |

> 공통 에러(400/401/403/404/500/502)는 공통 규칙 참고.

---

### 2.2 PUT `/api/user/selected-repos`

- **설명:** 포트폴리오/임베딩 대상으로 사용할 “선택 레포” 목록 저장(갱신)

#### 1. Request Syntax

```bash
curl -X PUT "https://example.com/api/user/selected-repos" \
  -H "Authorization: Bearer <app-session-token>" \
  -H "Content-Type: application/json" \
  -d '{"repo_ids":[123,456],"full_names":["Ara5429/subway-rag-chatbot"],"replace":true}'
```

#### 2. Request Header

| Header | 설명 | 필수 |
|--------|------|------|
| Cookie | 세션 쿠키 (인증된 경우) | Cookie 또는 Authorization 중 하나 필수 |
| Authorization | `Bearer <app-session-token>` | Cookie 또는 Authorization 중 하나 필수 |
| Content-Type | `application/json` | Y |

#### 3. Request Element

| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| repo_ids | array&lt;integer&gt; | N | GitHub 레포 numeric ID 목록 (repo_ids 또는 full_names 중 최소 하나 권장) |
| full_names | array&lt;string&gt; | N | `"owner/name"` 형식 레포 목록 |
| replace | boolean | N | true: 기존 선택 목록 덮어쓰기, false: 기존 목록에 병합, default=true |

#### 4. Response

**200 OK**

```json
{
  "selected_repos": [
    { "id": 123, "full_name": "Ara5429/subway-rag-chatbot" },
    { "id": 456, "full_name": "kocory1/AutoPolio" }
  ]
}
```

| 상태코드 | error | 발생조건 |
|----------|-------|----------|
| 400 | BAD_REQUEST | repo_ids와 full_names 모두 없음 |
| 401 | UNAUTHORIZED | 로그인 필요 |

> 공통 에러(400/401/403/404/500/502)는 공통 규칙 참고.

---

## 3. 파일/콘텐츠 조회

### 3.1 GET `/api/github/repos/{repo_id}/files`

- **설명:** 레포의 파일/디렉터리 트리 조회 (임베딩·포트폴리오 대상 선택용)

#### 1. Request Syntax

```bash
curl -X GET "https://example.com/api/github/repos/123/files?path=/&depth=2&ref=main" \
  -H "Authorization: Bearer <app-session-token>"
```

#### 2. Request Header

| Header | 설명 | 필수 |
|--------|------|------|
| Cookie | 세션 쿠키 (인증된 경우) | Cookie 또는 Authorization 중 하나 필수 |
| Authorization | `Bearer <app-session-token>` | Cookie 또는 Authorization 중 하나 필수 |

#### 3. Request Element

| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| repo_id | integer \| string | Y | Path. GitHub 레포 numeric ID 또는 `"owner/name"` |
| path | string | N | 조회 시작 디렉터리 경로, default="/" |
| depth | integer | N | 탐색 최대 깊이, default=2 |
| ref | string | N | 브랜치명 또는 커밋 SHA, default=레포 default_branch |

#### 4. Response

**200 OK**

```json
{
  "repo_id": 123,
  "ref": "main",
  "root": "src/",
  "tree": [
    { "path": "src/", "type": "dir" },
    { "path": "src/app/", "type": "dir" },
    { "path": "src/app/main.py", "type": "file" },
    { "path": "README.md", "type": "file" }
  ]
}
```

| 상태코드 | error | 발생조건 |
|----------|-------|----------|
| 403 | FORBIDDEN | 해당 레포 접근 권한 없음 |
| 404 | NOT_FOUND | 레포 또는 경로 없음 |

> 공통 에러(400/401/403/404/500/502)는 공통 규칙 참고.
| 502 | GITHUB_UPSTREAM_ERROR | GitHub 트리 조회 실패 |

---

### 3.2 GET `/api/github/repos/{repo_id}/contents`

- **설명:** 특정 파일의 raw 내용 조회 (코드/문서 읽기, 임베딩 입력용)

#### 1. Request Syntax

```bash
curl -X GET "https://example.com/api/github/repos/123/contents?path=README.md&ref=main&encoding=raw" \
  -H "Authorization: Bearer <app-session-token>"
```

#### 2. Request Header

| Header | 설명 | 필수 |
|--------|------|------|
| Cookie | 세션 쿠키 (인증된 경우) | Cookie 또는 Authorization 중 하나 필수 |
| Authorization | `Bearer <app-session-token>` | Cookie 또는 Authorization 중 하나 필수 |

#### 3. Request Element

| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| repo_id | integer \| string | Y | Path. GitHub 레포 ID 또는 `"owner/name"` |
| path | string | Y | 파일 경로, 예: `README.md`, `src/main.py` |
| ref | string | N | 브랜치명 또는 커밋 SHA, default=레포 default_branch |
| encoding | string | N | `raw` \| `base64`, default=raw |

#### 4. Response

**200 OK (encoding=raw)**  
- Content-Type: `text/plain` 또는 `application/octet-stream`  
- Body: 파일 내용 그대로

예:

```text
# AutoPolio

From Code to Career – 증거 기반 개발자 이력서
```

**200 OK (encoding=base64)**

```json
{
  "repo_id": 123,
  "path": "README.md",
  "ref": "main",
  "encoding": "base64",
  "content": "IyBBdXRvUG9saW8KCiBGcm9tIENvZGUgdG8gQ2FyZWVyIC3CqC4uLg=="
}
```

| 상태코드 | error | 발생조건 |
|----------|-------|----------|
| 400 | BAD_REQUEST | path 쿼리 파라미터 누락 |
| 403 | FORBIDDEN | 해당 레포 접근 권한 없음 |

> 공통 에러(400/401/403/404/500/502)는 공통 규칙 참고.
| 404 | NOT_FOUND | 레포 또는 파일 없음 |
| 502 | GITHUB_UPSTREAM_ERROR | GitHub 콘텐츠 조회 실패 |

---

## 4. 커밋 조회 + 집계

### 4.1 GET `/api/github/repos/{repo_id}/commits`

- **설명:** 레포 커밋 목록 조회. author 필터로 “내 커밋만” 조회 및 집계 가능.

#### 1. Request Syntax

```bash
curl -X GET "https://example.com/api/github/repos/123/commits?author=Ara5429&per_page=30&page=1" \
  -H "Authorization: Bearer <app-session-token>"
```

#### 2. Request Header

| Header | 설명 | 필수 |
|--------|------|------|
| Cookie | 세션 쿠키 (인증된 경우) | Cookie 또는 Authorization 중 하나 필수 |
| Authorization | `Bearer <app-session-token>` | Cookie 또는 Authorization 중 하나 필수 |

#### 3. Request Element

| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| repo_id | integer \| string | Y | Path. GitHub 레포 ID 또는 `"owner/name"` |
| author | string | N | GitHub 로그인 ID 또는 이메일, default=현재 로그인 유저 |
| path | string | N | 특정 파일/디렉터리만 대상으로 커밋 조회 |
| since | string | N | ISO8601, 이 시각 이후 커밋만 |
| until | string | N | ISO8601, 이 시각 이전 커밋만 |
| per_page | integer | N | default=30 |
| page | integer | N | default=1 |

#### 4. Response

**200 OK**

```json
{
  "repo_id": 123,
  "ref": "main",
  "author": "Ara5429",
  "path": "src/",
  "summary": {
    "total_commits": 42,
    "author_commits": 18,
    "files_changed_total": 130,
    "date_range": {
      "from": "2025-01-01T00:00:00Z",
      "to": "2026-02-10T09:00:00Z"
    }
  },
  "commits": [
    {
      "sha": "abc123def456789012345678901234567890abcd",
      "message": "feat: RAG 검색 성능 개선",
      "author": {
        "login": "Ara5429",
        "name": "Ara",
        "email": "example@example.com"
      },
      "html_url": "https://github.com/owner/repo/commit/abc123def456789012345678901234567890abcd",
      "files_changed": 5,
      "date": "2026-02-10T09:00:00Z"
    }
  ],
  "page": 1,
  "per_page": 30
}
```

| 상태코드 | error | 발생조건 |
|----------|-------|----------|
| 403 | FORBIDDEN | 해당 레포 접근 권한 없음 |
| 404 | NOT_FOUND | 레포 없음 |

> 공통 에러(400/401/403/404/500/502)는 공통 규칙 참고.
| 502 | GITHUB_UPSTREAM_ERROR | GitHub 커밋 조회 실패 |

---

## 5. 임베딩 API

### 5.1 POST `/api/github/repos/{repo_id}/embedding`

- **설명:** 지정된 레포/경로에 대해 임베딩을 생성하고 VectorDB/DB에 저장한 뒤, 요약 정보를 반환.

#### 1. Request Syntax

```bash
curl -X POST "https://example.com/api/github/repos/123/embedding" \
  -H "Authorization: Bearer <app-session-token>" \
  -H "Content-Type: application/json" \
  -d '{"paths":["src/","README.md"],"branch":"main","strategy":"code_and_docs_v1","force_refresh":false}'
```

#### 2. Request Header

| Header | 설명 | 필수 |
|--------|------|------|
| Cookie | 세션 쿠키 (인증된 경우) | Cookie 또는 Authorization 중 하나 필수 |
| Authorization | `Bearer <app-session-token>` | Cookie 또는 Authorization 중 하나 필수 |
| Content-Type | `application/json` | Y |

#### 3. Request Element

| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| repo_id | integer \| string | Y | Path. GitHub 레포 ID 또는 `"owner/name"` |
| paths | array&lt;string&gt; | Y | 비어 있지 않은 배열 |
| branch | string | N | default=레포 default_branch |
| strategy | string | N | default=code_and_docs_v1 |
| force_refresh | boolean | N | default=false |

#### 4. Response

**200 OK (임베딩 생성 및 저장 완료)**

```json
{
  "repo_id": 123,
  "branch": "main",
  "paths": ["src/", "README.md"],
  "strategy": "code_and_docs_v1",
  "status": "completed",
  "embedding": {
    "chunks_indexed": 128,
    "dimensions": 1536,
    "total_tokens": 45231,
    "storage": {
      "type": "vectordb",
      "index_name": "autofolio_github_repo_123_main",
      "last_updated_at": "2026-03-04T10:23:45Z"
    }
  }
}
```

**200 OK (캐시 히트, 이미 최신 상태)**

```json
{
  "repo_id": 123,
  "branch": "main",
  "paths": ["src/"],
  "strategy": "code_and_docs_v1",
  "status": "completed",
  "embedding": {
    "chunks_indexed": 128,
    "dimensions": 1536,
    "total_tokens": 45231,
    "storage": {
      "type": "vectordb",
      "index_name": "autofolio_github_repo_123_main",
      "last_updated_at": "2026-03-01T09:00:00Z"
    },
    "cache_hit": true
  }
}
```

| 상태코드 | error | 발생조건 |
|----------|-------|----------|
| 400 | BAD_REQUEST | paths가 비어 있거나 배열이 아님 |
| 401 | UNAUTHORIZED | 로그인 필요 |
| 403 | FORBIDDEN | 해당 레포 접근 권한 없음 |
| 404 | NOT_FOUND | 레포 없음 |
| 409 | EMBEDDING_IN_PROGRESS | 해당 레포/브랜치에 대한 임베딩 작업이 이미 진행 중 |
| 502 | EMBEDDING_FAILED | 임베딩 생성 중 오류 |

> 공통 에러(400/401/403/404/500/502)는 공통 규칙 참고.

---

### 5.2 GET `/api/github/repos/{repo_id}/embedding/status`

- **설명:** 비동기 임베딩 작업의 현재 상태 조회

#### 1. Request Syntax

```bash
curl -X GET "https://example.com/api/github/repos/123/embedding/status?branch=main" \
  -H "Authorization: Bearer <app-session-token>"
```

#### 2. Request Header

| Header | 설명 | 필수 |
|--------|------|------|
| Cookie | 세션 쿠키 (인증된 경우) | Cookie 또는 Authorization 중 하나 필수 |
| Authorization | `Bearer <app-session-token>` | Cookie 또는 Authorization 중 하나 필수 |

#### 3. Request Element

| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| repo_id | integer \| string | Y | Path. GitHub 레포 ID 또는 `"owner/name"` |
| branch | string | N | 브랜치명, default=레포 default_branch |

#### 4. Response

**200 OK**

```json
{
  "repo_id": 123,
  "branch": "main",
  "status": "in_progress",
  "started_at": "2026-03-04T10:20:00Z",
  "completed_at": null,
  "error_message": null
}
```

| 필드 | 타입 | 설명 |
|------|------|------|
| repo_id | integer | 레포 ID |
| branch | string | 브랜치명 |
| status | string | queued \| in_progress \| completed \| failed |
| started_at | string \| null | ISO8601, 작업 시작 시각 (시작 전이면 null) |
| completed_at | string \| null | ISO8601, 완료 시각 (미완료면 null) |
| error_message | string \| null | 실패 시 오류 메시지 (정상이면 null) |

| 상태코드 | error | 발생조건 |
|----------|-------|----------|
| 401 | UNAUTHORIZED | 로그인 필요 |
| 404 | NOT_FOUND | 해당 레포/브랜치에 대한 임베딩 작업 없음 |

> 공통 에러(400/401/403/404/500/502)는 공통 규칙 참고.
