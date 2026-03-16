# Autofolio API 전체 명세 (Full Spec)

**버전:** 1.0  
**최종 정리일:** 2025-03-11

이 문서는 Autofolio API를 **한 곳에서 조망**하기 위한 통합 명세이다.  
다음 네 문서의 내용을 묶어 두었다.

| 문서 | 역할 |
|------|------|
| `API_Common.md` | 공통 요청 형식, 에러 규칙, API 사용 시퀀스 |
| `API_Auth_Spec.md` | GitHub OAuth 로그인/콜백/로그아웃, `/api/me` |
| `API_GitHub_Spec.md` | GitHub 레포 목록·선택, 파일/콘텐츠, 커밋, 임베딩 |
| `API_Service_Spec.md` | 문서 업로드, 채용공고 파싱, Job Fit, 자소서 Draft/Inspect, 포트폴리오 |

**상세한 Request/Response 스키마, curl 예제, 에러 표**는 각 문서를 참고한다.

---

## Part I. 공통 규칙 (API_Common)

### 1. 공통 요청 형식

- **Content-Type:** 기본 `application/json`. 파일 업로드는 `multipart/form-data`(해당 엔드포인트에서 명시).
- **인증:** 세션 쿠키 또는 `Authorization: Bearer <app-session-token>`.

**HTTP 상태코드**

| 상태코드 범위 | 의미 |
|-------------|------|
| 200번대 | 성공 |
| 302 | 리다이렉트 |
| 400번대 | 클라이언트 오류 |
| 500번대 | 서버 오류 |

### 2. 공통 에러 응답 형식

```json
{
  "error": "ERROR_CODE",
  "message": "사람이 읽을 수 있는 에러 설명"
}
```

### 3. 공통 에러 코드표

| HTTP 상태코드 | error | 발생조건 |
|--------------|-------|----------|
| 400 | BAD_REQUEST | 요청 파라미터 누락 또는 형식 오류 |
| 401 | UNAUTHORIZED | 세션 없음 또는 만료 |
| 403 | FORBIDDEN | 접근 권한 없음 |
| 404 | NOT_FOUND | 요청한 리소스 없음 |
| 500 | INTERNAL_SERVER_ERROR | 서버 내부 오류 |
| 502 | GITHUB_UPSTREAM_ERROR | GitHub API 호출 실패 (GitHub 연동 API에만 해당) |

---

## Part II. 인증 API (API_Auth_Spec)

**역할:** GitHub OAuth를 통한 로그인·세션 발급, 로그아웃, 현재 유저 조회.  
비밀번호는 앱이 받지 않으며, GitHub 로그인 페이지에서만 입력된다.

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/auth/github/login` | GitHub OAuth authorize URL로 302 리다이렉트 |
| GET | `/api/auth/github/callback` | code·state 수신 → access_token 교환·세션 발급 → 302 → /dashboard |
| GET | `/api/auth/logout` | 세션 무효화 후 302 → / |
| GET | `/api/me` | 현재 로그인 유저 정보 반환 (user_id, github_login, github_id, email, avatar_url) |

상세: `docs/API_Auth_Spec.md`

---

## Part III. GitHub API (API_GitHub_Spec)

**역할:** 로그인한 유저의 GitHub 레포 목록 조회, 선택 레포 저장/조회, 레포 내 파일 트리·파일 내용·커밋 조회, 임베딩 생성.  
Base URL: `/api/github` (선택 레포는 `/api/user`).

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/github/repos` | 레포 목록 (page, per_page만 노출) |
| GET | `/api/user/selected-repos` | 선택 레포 목록 조회 |
| PUT | `/api/user/selected-repos` | 선택 레포 저장(갱신) |
| GET | `/api/github/repos/{repo_id}/files` | 파일/디렉터리 트리 |
| GET | `/api/github/repos/{repo_id}/contents` | 단일 파일 raw/base64 내용 |
| GET | `/api/github/repos/{repo_id}/commits` | 커밋 목록·집계 (author 등 필터) |
| POST | `/api/github/repos/{repo_id}/embedding` | 임베딩 생성·저장. selected_repos 등록 레포만 가능(미등록 시 403). paths[]로 레포/폴더/파일 단위 지정. 응답에 hierarchy_nodes_created(asset_hierarchy 노드 수) 포함 |

상세: `docs/API_GitHub_Spec.md`

---

## Part IV. 서비스 API (API_Service_Spec)

**역할:** 이력서/포트폴리오 문서 업로드, 채용공고 입력·저장, Job Fit 점수, 자소서 초안·검수, 포트폴리오 생성·조회.  
채용공고는 **POST /api/jobs/parse** 호출 시 항상 **jobs 테이블에 저장**되며 응답에 **job_id**를 반환한다.  
이후 job-fit, cover-letter/draft, portfolio/generate는 **job_id만** 받으며, job_id 없으면 공고 맥락 없이 User DB 기준 범용 생성한다.

| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | `/api/user/documents` | 이력서/포트폴리오 PDF·PPT 업로드 → OCR → VectorDB 저장 |
| POST | `/api/jobs/parse` | 채용공고 입력: source_type=url(크롤링+파싱) 또는 manual(직접입력). 둘 다 jobs 저장 후 job_id 반환 |
| POST | `/api/job-fit` | job_id(선택) 기준 Job Fit 점수·요인. 없으면 범용 생성 |
| POST | `/api/cover-letter/draft` | 자소서 초안 생성. questions[] 다문항 한 번에 생성 → drafts[] 반환 (job_id 선택) |
| POST | `/api/cover-letter/inspect` | 자소서 검수. answers[] 입력 → feedbacks[] + overall_score(0~100) 반환 |
| POST | `/api/portfolio/generate` | 포트폴리오 초안 생성 (job_id 선택) |
| GET | `/api/portfolio` | 포트폴리오 목록/단건 조회 |

- 생성:
  - 입력: 인증 사용자 기준 (요청 바디 비어도 됨).
  - 레포 소스는 요청 바디가 아니라 `selected_repos`(SSoT)에서 조회한다.
  - `parsed_job`, `language`는 공고 맞춤형 단계에서 도입 예정이며 현재 미사용.
  - 출력: `portfolio_id`, `portfolio{title, summary, projects[]}`.
- 조회:
  - 목록: `items[]` (portfolio_id, job_id, created_at)
  - 단건: `portfolio_id`, `portfolio` 전체 내용.

---

## Part V. API 사용 시퀀스

1. GET /api/auth/github/login — GitHub 로그인 시작 (Auth)
2. GET /api/auth/github/callback — 세션 발급 완료 (Auth)
3. GET /api/me — 유저 정보 확인 (Auth)
4. GET /api/github/repos — 레포 목록 조회 (GitHub)
5. PUT /api/user/selected-repos — 레포 선택 저장 (GitHub)
6. POST /api/user/documents — 이력서/포트폴리오 업로드 (Service, 선택)
7. POST /api/github/repos/{id}/embedding — 임베딩 생성 (GitHub)
8. POST /api/jobs/parse — 채용공고 입력·저장 (Service). 응답 job_id는 9·10·12번에서 선택 사용
9. POST /api/job-fit — 적합도 점수 확인 (Service)
10. POST /api/cover-letter/draft — 자소서 초안 생성 (Service)
11. POST /api/cover-letter/inspect — 자소서 검수 (Service)
12. POST /api/portfolio/generate — 포트폴리오 생성 (Service)

6번(문서 업로드)은 선택 단계이며, 이력서/포트폴리오 문서가 없어도 자소서·포트폴리오 생성은 GitHub 임베딩만으로 진행 가능하다.
