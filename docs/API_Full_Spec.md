## Autofolio 전체 API 명세 (GitHub + Service)

**문서 버전:** 1.0  
**최종 정리일:** 2026-03-05

이 문서는 Autofolio의 **전체 API**를 한눈에 볼 수 있도록 정리한 통합 명세서이다.

- GitHub 연동 전용 상세 문서: `API_GitHub_Spec.md`
- 서비스 레벨 상세 문서 (채용공고/Job Fit/자소서/포트폴리오): `API_Service_Spec.md`

여기서는 두 문서의 핵심 내용을 한 파일로 모아서 정리한다.

---

## 0. 공통 규칙

- **인증:** 세션 쿠키 또는 `Authorization: Bearer <app-session-token>`
- **에러 응답 포맷(공통):**

```json
{
  "error": "ERROR_CODE",
  "message": "사람이 읽을 수 있는 에러 설명"
}
```

---

## 1. API 목차

| 구분 | 메서드 | 경로 | 설명 |
|------|--------|------|------|
| 인증 | GET | `/api/auth/github/login` | GitHub OAuth 시작(리다이렉트) |
| 인증 | GET | `/api/auth/github/callback` | OAuth 콜백, 토큰 교환·세션 생성 |
| 인증 | GET | `/api/auth/logout` | 로그아웃 |
| 인증 | POST | `/api/auth/github/disconnect` | GitHub 연동 해제 (**MVP 이후 TODO**) |
| 유저 | GET | `/api/me` | 현재 로그인 유저 정보 |
| 유저 | GET/PUT | `/api/user/selected-repos` | 선택 레포 목록 조회/저장 |
| 유저 | POST | `/api/user/documents` | 이력서·포트폴리오 PDF·PPT 업로드 → OCR·임베딩 저장 |
| GitHub | GET | `/api/github/repos` | 로그인 유저 레포 목록 |
| GitHub | POST | `/api/github/repos/select` | 선택 레포 저장 |
| GitHub | GET | `/api/github/repos/{repo_id}` | 레포 단건 상세 |
| GitHub | GET | `/api/github/repos/{repo_id}/files` | 파일/디렉터리 트리 조회 |
| GitHub | GET | `/api/github/repos/{repo_id}/contents` | 파일 raw 내용 조회 |
| GitHub | GET | `/api/github/repos/{repo_id}/commits` | 커밋 목록 + 집계(summary) |
| GitHub | POST | `/api/github/repos/{repo_id}/embedding` | 임베딩 생성 + DB 저장 |
| 채용공고 | POST | `/api/jobs/parse` | 담당업무/자격요건/우대사항/기업명/인재상/포지션명 추출 |
| Job Fit | POST | `/api/job-fit` | User DB + 공고 결과 비교 → Job Fit 점수 |
| 자소서 | POST | `/api/cover-letter/draft` | 자소서 초안 생성 (전략 수립 + Writer + 합격 자소서 모듈) |
| 자소서 | POST | `/api/cover-letter/inspect` | 자소서 검수/피드백 (Inspector) |
| 포트폴리오 | POST | `/api/portfolio/generate` | 포트폴리오 생성 |
| 포트폴리오 | GET | `/api/portfolio` | 포트폴리오 조회 |

> **합격 자소서 검색**은 REST API가 아니며,  
> `/api/cover-letter/draft` 내부에서만 호출되는 Retrieval 모듈이다.

---

## 2. GitHub API 요약

자세한 내용은 `API_GitHub_Spec.md` 참조.

### 2.1 레포 목록/선택

- **GET `/api/github/repos`**
  - 로그인 유저의 레포 목록, `per_page`, `page`, `sort`, `direction`, `type` 쿼리 지원.
  - 응답: `repos[]` + 페이징 정보, 각 레포의 id/full_name/description/private/language/stars/forks/default_branch/pushed_at.

- **POST `/api/github/repos/select`**
  - 바디: `repo_ids`, `full_names`, `replace` (덮어쓰기 여부).
  - 응답: 최종 `selected_repos[]` 목록.

### 2.2 파일/콘텐츠/커밋

- **GET `/api/github/repos/{repo_id}/files`**
  - 쿼리: `path`, `depth`, `ref`  
  - 응답: `tree[]` (path, type=file/dir) + root/ref 정보.

- **GET `/api/github/repos/{repo_id}/contents`**
  - 쿼리: `path`(필수), `ref`, `encoding`(raw/base64).  
  - 응답: raw 텍스트 또는 `{content: base64, ...}` JSON.

- **GET `/api/github/repos/{repo_id}/commits`**
  - 쿼리: `author`, `path`, `since`, `until`, `per_page`, `page`.  
  - 응답: `summary`(total_commits, author_commits, files_changed_total, date_range) + `commits[]`.

### 2.3 임베딩

- **POST `/api/github/repos/{repo_id}/embedding`**
  - 바디: `paths[]`, `branch`, `strategy`, `force_refresh`.  
  - 응답: `status=completed`, `embedding`(chunks_indexed, dimensions, tokens, storage 정보)와 함께 VectorDB 저장 상태 반환.  
  - 에러: `BAD_REQUEST`(paths 비어 있음), `EMBEDDING_IN_PROGRESS`, `EMBEDDING_FAILED` 등.

---

## 3. 서비스 API 요약

자세한 내용은 `API_Service_Spec.md` 참조.

### 3.1 채용공고 파싱 – POST `/api/jobs/parse`

- 채용공고 텍스트 또는 URL을 입력받아:
  - `position_title`, `company_name`, `company_persona`,
  - `duties[]`, `requirements[]`, `preferences[]`
  를 추출하고 `job_id`로 저장.

### 3.2 Job Fit – POST `/api/job-fit`

- 입력: `user_id`, `job_id`  
- 출력: `score`(0~1), `score_label`(HIGH/MEDIUM/LOW), `factors[]` (skills_match, experience_level, company_fit 등 세부 항목별 점수 및 설명).

### 3.3 자소서 – Draft / Inspect

- **POST `/api/cover-letter/draft`**
  - 입력: `user_id`, `job_id`, `question_id`, `question_text`, `constraints(min/max_chars, tone, ...)`.
  - 내부에서:
    - 전략 수립 그래프 호출,
    - GitHub/포트폴리오/Job Fit/합격 자소서 Retrieval 결과를 조합,
    - 초안(`answer`)과 사용한 에셋 목록(`used_assets`)을 생성.

- **POST `/api/cover-letter/inspect`**
  - 입력: 사용자가 작성한 `answer`.
  - 출력: `score`, `strengths[]`, `weaknesses[]`, `suggestions[]` 등 Inspector 결과.

### 3.4 포트폴리오 – POST `/api/portfolio/generate`, GET `/api/portfolio`

- 생성:
  - 입력: `user_id`, `job_id`, `github_repo_ids[]`, `document_ids[]`, `language`.
  - 출력: `portfolio_id`, `sections[]`(요약, 프로젝트, 경험 등).
- 조회:
  - 목록: `items[]` (portfolio_id, job_id, created_at)
  - 단건: `portfolio_id`, `sections[]` 전체 내용.

---

## 4. 미구현/향후 TODO

- **disconnect API:**  
  - `POST /api/auth/github/disconnect` 는 **MVP에서 제외**.  
  - 현재는 로그아웃만 제공하며, 추후 “GitHub 연동 해제”가 필요해지면 별도 이슈로 설계.

- **채용공고 크롤링 API:**  
  - 현재는 외부 사이트에서 텍스트/URL로 입력받는 수준.  
  - 직접 크롤링/동기화 API는 16주 계획표 상 후순위.

- **합격 자소서 검색 별도 API:**  
  - Writer 그래프 내부 Retrieval 모듈로만 존재.  
  - 외부 REST API로 열 계획은 현재 없음.

