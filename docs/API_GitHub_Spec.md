## Autofolio GitHub API 명세

**버전:** 1.0  
**최종 정리일:** 2025-03-04

이 문서는 Autofolio에서 사용하는 **GitHub 연동 전용 API**를 정리한 것이다.  
인증(/api/auth/github/*, /api/me 등)은 별도 문서를 따르고, 여기서는 GitHub 레포·파일·커밋·임베딩 관련 엔드포인트만 다룬다.

---

### 공통 규칙

- **Base URL:** `/api/github`
- **인증:** 세션 쿠키 또는 `Authorization: Bearer <app-session-token>`
- **에러 응답 포맷(공통):**

```json
{
  "error": "ERROR_CODE",
  "message": "사람이 읽을 수 있는 에러 설명"
}
```

---

## 1. 레포지토리 목록 / 선택

### 1.1 GET `/api/github/repos`

- **설명:** 로그인 유저의 GitHub 레포 목록 조회

#### Request

- **Headers**
  - 세션 쿠키 또는 `Authorization: Bearer <app-session-token>`
- **Query Parameters**
  - `per_page`: integer, optional, default=30  
    페이지당 레포 수
  - `page`: integer, optional, default=1  
    페이지 번호(1-base)
  - `sort`: string, optional, default=`pushed`  
    - 허용값: `created` \| `updated` \| `pushed` \| `full_name`
  - `direction`: string, optional, default=`desc`  
    - 허용값: `asc` \| `desc`
  - `type`: string, optional, default=`owner`  
    - 허용값: `all` \| `owner` \| `member`

#### Response

- **200 OK**

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

- **401 UNAUTHORIZED**

```json
{
  "error": "UNAUTHORIZED",
  "message": "Session expired or invalid."
}
```

- **502 BAD_GATEWAY**

```json
{
  "error": "GITHUB_UPSTREAM_ERROR",
  "message": "Failed to fetch repositories from GitHub."
}
```

---

### 1.2 POST `/api/github/repos/select`

- **설명:** 사용자가 포트폴리오/임베딩 대상으로 사용할 “선택 레포” 목록 저장

#### Request

- **Headers**
  - 세션 쿠키 또는 `Authorization: Bearer <app-session-token>`
- **Body (JSON)**

```json
{
  "repo_ids": [123, 456],
  "full_names": ["Ara5429/subway-rag-chatbot"],
  "replace": true
}
```

- `repo_ids`: array\<integer>, optional  
- `full_names`: array\<string>, optional (`"owner/name"` 포맷)  
- `replace`: boolean, optional, default=true  
  - true: 기존 선택 목록을 덮어쓰기  
  - false: 기존 목록에 병합

#### Response

- **200 OK**

```json
{
  "selected_repos": [
    { "id": 123, "full_name": "Ara5429/subway-rag-chatbot" },
    { "id": 456, "full_name": "kocory1/AutoPolio" }
  ]
}
```

- **400 BAD_REQUEST**

```json
{
  "error": "BAD_REQUEST",
  "message": "At least one of repo_ids or full_names must be provided."
}
```

- **401 UNAUTHORIZED**

```json
{
  "error": "UNAUTHORIZED",
  "message": "Login required."
}
```

---

## 2. 파일/콘텐츠 조회

### 2.1 GET `/api/github/repos/{repo_id}/files`

- **설명:** 레포의 파일/디렉터리 트리 조회 (임베딩·포트폴리오 대상 선택용)

#### Request

- **Path Parameters**
  - `repo_id`: integer or string, required  
    GitHub 레포 numeric ID 또는 `"owner/name"`
- **Query Parameters**
  - `path`: string, optional, default="/"  
    조회 시작 디렉터리 경로
  - `depth`: integer, optional, default=2  
    탐색 최대 깊이
  - `ref`: string, optional, default=레포 default_branch  
    브랜치명 또는 커밋 SHA

#### Response

- **200 OK**

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

- **403 FORBIDDEN**

```json
{
  "error": "FORBIDDEN",
  "message": "You do not have access to this repository."
}
```

- **404 NOT_FOUND**

```json
{
  "error": "NOT_FOUND",
  "message": "Repository or path not found."
}
```

- **502 BAD_GATEWAY**

```json
{
  "error": "GITHUB_UPSTREAM_ERROR",
  "message": "Failed to fetch tree from GitHub."
}
```

---

### 2.2 GET `/api/github/repos/{repo_id}/contents`

- **설명:** 특정 파일의 raw 내용 조회 (코드/문서 읽기, 임베딩 입력용)

#### Request

- **Path Parameters**
  - `repo_id`: integer or string, required
- **Query Parameters**
  - `path`: string, required  
    예: `"README.md"`, `"src/main.py"`
  - `ref`: string, optional, default=레포 default_branch
  - `encoding`: string, optional, default=`raw`  
    - 허용값: `raw` \| `base64`

#### Response

- **200 OK (encoding=raw)**  
  - Body: `text/plain` 또는 `application/octet-stream` – 파일 내용 그대로

예:

```text
# AutoPolio

From Code to Career – 증거 기반 개발자 이력서
...
```

- **200 OK (encoding=base64)**  

```json
{
  "repo_id": 123,
  "path": "README.md",
  "ref": "main",
  "encoding": "base64",
  "content": "IyBBdXRvUG9saW8KCiBGcm9tIENvZGUgdG8gQ2FyZWVyIC3CqC4uLg=="
}
```

- **400 BAD_REQUEST**

```json
{
  "error": "BAD_REQUEST",
  "message": "path query parameter is required."
}
```

- **403 / 404 / 502** – 공통 에러 포맷 사용

---

## 3. 커밋 조회 + 집계

### 3.1 GET `/api/github/repos/{repo_id}/commits`

- **설명:** 레포 커밋 목록 조회. `author` 필터로 “내 커밋만” 조회 및 집계 가능.

#### Request

- **Path Parameters**
  - `repo_id`: integer or string, required
- **Query Parameters**
  - `author`: string, optional, default=현재 로그인 GitHub 로그인  
    - GitHub 로그인 ID 또는 이메일
  - `path`: string, optional  
    - 특정 파일/디렉터리만 대상으로 커밋 조회
  - `since`: string, optional, ISO8601  
    - 이 시각 이후 커밋만
  - `until`: string, optional, ISO8601  
    - 이 시각 이전 커밋만
  - `per_page`: integer, optional, default=30
  - `page`: integer, optional, default=1

#### Response

- **200 OK**

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
  ],
  "page": 1,
  "per_page": 30
}
```

- **403 / 404 / 502** – 공통 에러 포맷 사용

---

## 4. 임베딩 API

### 4.1 POST `/api/github/repos/{repo_id}/embedding`

- **설명:** 지정된 레포/경로에 대해 임베딩을 생성하고 VectorDB/DB에 저장한 뒤, 요약 정보를 반환.

#### Request

- **Path Parameters**
  - `repo_id`: integer or string, required
- **Body (JSON)**

```json
{
  "paths": ["src/", "README.md"],
  "branch": "main",
  "strategy": "code_and_docs_v1",
  "force_refresh": false
}
```

- `paths`: array\<string>, required, non-empty  
- `branch`: string, optional, default=레포 default_branch  
- `strategy`: string, optional, default=`code_and_docs_v1`  
- `force_refresh`: boolean, optional, default=false

#### Response

- **200 OK – 임베딩 생성 및 저장 완료**

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

- **이미 최신 상태인 경우 (캐시 히트)**

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

- **에러 예시**

```json
{
  "error": "BAD_REQUEST",
  "message": "paths must be a non-empty array."
}
```

```json
{
  "error": "EMBEDDING_IN_PROGRESS",
  "message": "An embedding job is already running for this repository and branch."
}
```

```json
{
  "error": "EMBEDDING_FAILED",
  "message": "Unexpected error during embedding generation."
}
```

