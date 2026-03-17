## Autofolio 서비스 API 명세 (Job / Cover Letter / Portfolio)

**버전:** 1.0  
**최종 정리일:** 2025-03-11

이 문서는 Autofolio의 **서비스 레벨 API**(채용공고 파싱, Job Fit, 자소서 Draft/검수, 포트폴리오)를 정의한다.  
GitHub 관련 API는 `API_GitHub_Spec.md` 를 참고한다.

---

### 공통 규칙

> 공통 요청 형식, 공통 에러 코드는 `API_Common.md` 참고.

- **인증:** 세션 쿠키 또는 `Authorization: Bearer <app-session-token>`
- **에러 응답 포맷(공통):**

```json
{
  "error": "ERROR_CODE",
  "message": "사람이 읽을 수 있는 에러 설명"
}
```

---

## 0. 사용자 문서 업로드

### 0.1 POST `/api/user/documents`

- **설명:** 이력서·포트폴리오용 PDF/PPT 파일을 업로드하여 OCR 처리 후 VectorDB에 저장한다.

#### 1. Request Syntax

```bash
curl -X POST "https://example.com/api/user/documents" \
  -H "Authorization: Bearer <app-session-token>" \
  -F "file=@/path/to/resume.pdf" \
  -F "document_type=resume" \
  -F "language=ko"
```

#### 2. Request Header

| Header | 설명 | 필수 |
|--------|------|------|
| Cookie | 세션 쿠키 (인증된 경우) | Cookie 또는 Authorization 중 하나 필수 |
| Authorization | `Bearer <app-session-token>` | Cookie 또는 Authorization 중 하나 필수 |
| Content-Type | multipart/form-data | Y (curl -F 사용 시 자동 설정) |

#### 3. Request Element

| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| file | file | Y | 업로드할 파일 (PDF 또는 PPT/PPTX) |
| document_type | string | N | resume \| portfolio, default=resume |
| language | string | N | ko \| en, default=ko |

#### 4. Response

**200 OK**

```json
{
  "document_id": "doc_20250309_001",
  "document_type": "resume",
  "filename": "resume.pdf",
  "page_count": 3,
  "status": "processing",
  "created_at": "2025-03-09T14:30:00Z"
}
```

| 필드 | 타입 | 설명 |
|------|------|------|
| document_id | string | 저장된 문서 식별자 |
| document_type | string | resume \| portfolio |
| filename | string | 원본 파일명 |
| page_count | integer | 페이지 수 |
| status | string | processing \| completed |
| created_at | string | ISO8601 |

| 상태코드 | error | 발생조건 |
|----------|-------|----------|
| 400 | BAD_REQUEST | 지원하지 않는 파일 형식 (PDF/PPT/PPTX 외) |
| 401 | UNAUTHORIZED | 로그인 필요 |
| 413 | FILE_TOO_LARGE | 파일 크기 초과 |

> 공통 에러(400/401/403/404/500/502)는 공통 규칙 참고.

---

## 1. 채용공고 파싱 API

### 1.1 POST `/api/jobs/parse`

- **설명:** 채용공고 입력을 두 가지 방식으로 받아 **담당 업무 / 자격 요건 / 우대 사항 / 기업명 / 기업 인재상 / 포지션명** 6개 항목을 확보한 뒤 **jobs 테이블에 저장**하고 `job_id`를 반환한다.  
  - **source_type=url:** `url` 필수. 서버가 해당 URL을 크롤링 후 LLM으로 파싱. url 기준으로 신규 저장하며, 항상 jobs에 한 건을 남긴다. 크롤링 실패 시 400 CRAWL_FAILED.  
  - **source_type=manual:** url 없음. 사용자가 6개 항목 직접 입력. position_title, company_name 필수, 나머지 선택. 항상 신규 저장(UUID id, 중복 체크 없음).

#### 1. Request Syntax

**source_type=url**

```bash
curl -X POST "https://example.com/api/jobs/parse" \
  -H "Authorization: Bearer <app-session-token>" \
  -H "Content-Type: application/json" \
  -d '{"source_type":"url","url":"https://example.com/jobs/123"}'
```

**source_type=manual**

```bash
curl -X POST "https://example.com/api/jobs/parse" \
  -H "Authorization: Bearer <app-session-token>" \
  -H "Content-Type: application/json" \
  -d '{"source_type":"manual","position_title":"백엔드 개발자","company_name":"Autofolio Corp","company_persona":"데이터 기반 의사결정을 중시하는 스타트업","duties":["API 설계","파이프라인 개발"],"requirements":["Python 3년 이상"],"preferences":["RAG 경험"]}'
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
| source_type | string | Y | `url` 또는 `manual` |
| url | string | N (source_type=url일 때 Y) | 채용공고 페이지 URL |
| position_title | string | N (source_type=manual일 때 Y) | 포지션명 |
| company_name | string | N (source_type=manual일 때 Y) | 기업명 |
| company_persona | string | N | 기업 인재상 |
| duties | array&lt;string&gt; | N | 담당 업무 목록 |
| requirements | array&lt;string&gt; | N | 자격 요건 목록 |
| preferences | array&lt;string&gt; | N | 우대 사항 목록 |

#### 4. Response

**200 OK**

```json
{
  "job_id": "job_abc123",
  "source_type": "url",
  "position_title": "백엔드 개발자",
  "company_name": "Autofolio Corp",
  "company_persona": "데이터 기반 의사결정을 중시하는 스타트업",
  "duties": ["API 설계", "파이프라인 개발"],
  "requirements": ["Python 3년 이상"],
  "preferences": ["RAG 경험"],
  "created_at": "2025-03-11T12:00:00Z"
}
```

| 필드 | 타입 | 설명 |
|------|------|------|
| job_id | string | jobs 테이블에 저장된 공고 ID (이후 job-fit, draft, portfolio/generate에서 사용) |
| source_type | string | `url` \| `manual` |
| position_title | string | 포지션명 |
| company_name | string | 기업명 |
| company_persona | string | 기업 인재상 |
| duties | array&lt;string&gt; | 담당 업무 목록 |
| requirements | array&lt;string&gt; | 자격 요건 목록 |
| preferences | array&lt;string&gt; | 우대 사항 목록 |
| created_at | string | ISO8601 저장 시각 |

| 상태코드 | error | 발생조건 |
|----------|-------|----------|
| 400 | BAD_REQUEST | source_type 누락, 또는 source_type=url인데 url 없음, 또는 source_type=manual인데 position_title/company_name 없음 |
| 400 | CRAWL_FAILED | source_type=url인데 해당 URL 크롤링 실패 (로그인 필요, 페이지 없음 등) |
| 401 | UNAUTHORIZED | 로그인 필요 |

> 공통 에러(400/401/403/404/500/502)는 공통 규칙 참고.

---

## 2. Job Fit API

### 2.1 POST `/api/job-fit`

- **설명:** User DB(프로필·임베딩)와 채용공고 정보를 비교하여 **Job Fit 점수(0~100)**를 계산한다. 사용자 식별은 인증 토큰에서 서버가 추출한다.  
  **비고:** job_id 없으면 공고 맥락 없이 User DB 전체 기반 범용 생성.

#### 1. Request Syntax

```bash
curl -X POST "https://example.com/api/job-fit" \
  -H "Authorization: Bearer <app-session-token>" \
  -H "Content-Type: application/json" \
  -d '{"job_id":"job_abc123"}'
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
| job_id | string | N | POST /api/jobs/parse 응답의 job_id. jobs 테이블에서 조회해 사용. 없으면 공고 맥락 없이 User DB 전체 기반 범용 생성 |

#### 4. Response

**200 OK**

```json
{
  "score": 82,
  "factors": [
    {
      "name": "skills_match",
      "weight": 0.5,
      "score": 90,
      "detail": "Python, FastAPI, RAG 경험이 요구사항과 잘 맞습니다."
    },
    {
      "name": "experience_level",
      "weight": 0.3,
      "score": 75,
      "detail": "경력 연차는 살짝 부족하지만 유사 프로젝트 경험으로 보완됩니다."
    },
    {
      "name": "company_fit",
      "weight": 0.2,
      "score": 70,
      "detail": "데이터 기반 문화와 학습 지향적인 태도가 잘 맞습니다."
    }
  ],
  "computed_at": "2025-03-04T12:05:00Z"
}
```

| 상태코드 | error | 발생조건 |
|----------|-------|----------|
| 401 | UNAUTHORIZED | 로그인 필요 |
| 404 | NOT_FOUND | 사용자(프로필/임베딩)를 찾을 수 없음 |

> 공통 에러(400/401/403/404/500/502)는 공통 규칙 참고.

---

## 3. 자소서 API (Writer / Inspector)

### 3.1 POST `/api/cover-letter/draft`

- **설명:** 자소서 문항 목록과 공고 정보를 기반으로 **다문항 자소서 초안**을 한 번에 생성한다. 문항별로 Writer 그래프를 호출하며, 생성된 초안은 `drafts` 테이블에 저장된다. 사용자 식별은 인증에서 추출한다.  
  내부적으로 **합격 자소서 Retrieval 모듈**과 User DB 에셋 조회를 수행하지만, 이들은 별도 공개 API가 아니다.  
  **비고:** job_id 없으면 공고 맥락 없이 User DB 전체 기반 범용 생성.

#### 1. Request Syntax

```bash
curl -X POST "https://example.com/api/cover-letter/draft" \
  -H "Authorization: Bearer <app-session-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "job_abc123",
    "questions": [
      {"question_text": "지원 동기를 작성해주세요.", "max_chars": 1500},
      {"question_text": "본인의 강점을 서술해주세요.", "max_chars": 1000},
      {"question_text": "입사 후 포부를 작성해주세요.", "max_chars": 1000}
    ]
  }'
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
| job_id | string | N | POST /api/jobs/parse 응답의 job_id. jobs 테이블에서 조회해 사용. 없으면 공고 맥락 없이 User DB 전체 기반 범용 생성 |
| questions | array&lt;object&gt; | Y | 문항별 입력. 비어 있으면 안 됨 |

**questions[] 각 object**

| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| question_text | string | Y | 자소서 문항 지문 |
| max_chars | integer | Y | 해당 문항 최대 글자 수 |

#### 4. Response

**200 OK**

```json
{
  "drafts": [
    {
      "draft_id": "uuid-001",
      "question_text": "지원 동기를 작성해주세요.",
      "answer": "저는 개발자로서...",
      "char_count": 1342
    },
    {
      "draft_id": "uuid-002",
      "question_text": "본인의 강점을 서술해주세요.",
      "answer": "저의 강점은...",
      "char_count": 876
    }
  ],
  "used_assets": {
    "github_repos": [
      { "id": 123, "full_name": "Ara5429/subway-rag-chatbot" }
    ],
    "accepted_essays_used": true
  },
  "created_at": "2025-03-11T12:10:00Z"
}
```

| 필드 | 타입 | 설명 |
|------|------|------|
| drafts | array&lt;object&gt; | 문항별 초안 목록 |
| drafts[].draft_id | string | 문항별 고유 식별자 (DB drafts.id) |
| drafts[].question_text | string | 해당 문항 지문 |
| drafts[].answer | string | 생성된 자소서 본문 |
| drafts[].char_count | integer | 생성된 본문 글자 수 |
| used_assets | object | 생성 시 참조된 자원 요약 |
| used_assets.github_repos | array&lt;object&gt; | 참조된 GitHub 레포 목록 |
| used_assets.github_repos[].id | integer | 레포 ID |
| used_assets.github_repos[].full_name | string | owner/name |
| used_assets.accepted_essays_used | boolean | 합격 자소서 DB 사용 여부 |
| created_at | string | ISO8601 생성 시각 |

| 상태코드 | error | 발생조건 |
|----------|-------|----------|
| 400 | BAD_REQUEST | questions 배열이 비어 있거나 누락, 또는 문항 중 question_text/max_chars 누락 |
| 401 | UNAUTHORIZED | 로그인 필요 |

> 공통 에러(400/401/403/404/500/502)는 공통 규칙 참고.

---

### 3.2 POST `/api/cover-letter/inspect`

- **설명:** 자소서 세션 전체 문항의 답변을 한번에 입력받아 문항별 개별 피드백을 반환한다. 점수는 0~100 퍼센트로 반환한다. (Inspector 그래프)

#### 1. Request Syntax

```bash
curl -X POST "https://example.com/api/cover-letter/inspect" \
  -H "Authorization: Bearer <app-session-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "answers": [
      {"draft_id": "uuid-001", "answer": "저는 개발자로서..."},
      {"draft_id": "uuid-002", "answer": "저의 강점은..."},
      {"draft_id": "uuid-003", "answer": "입사 후에는..."}
    ],
    "job_id": "job_abc123"
  }'
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
| answers | array&lt;object&gt; | Y | 문항별 답변 목록 |
| job_id | string | N | 공고 맥락 (선택). 없으면 공고 맥락 없이 User DB 기반 검사 |

**answers[] 각 object**

| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| draft_id | string | Y | draft 응답의 draft_id (DB drafts.id에 대응) |
| answer | string | Y | 해당 문항 작성본 (초안 그대로 또는 사용자 수정본) |

#### 4. Response

**200 OK**

```json
{
  "feedbacks": [
    {
      "draft_id": "uuid-001",
      "question_text": "지원 동기를 작성해주세요.",
      "score": 85,
      "strengths": ["STAR 구조가 명확합니다."],
      "weaknesses": ["회사 맞춤 언급 부족"],
      "suggestions": ["회사 비전과 연결하는 문장을 추가해 보세요."]
    },
    {
      "draft_id": "uuid-002",
      "question_text": "본인의 강점을 서술해주세요.",
      "score": 62,
      "strengths": ["구체적 사례 포함"],
      "weaknesses": ["수치 근거 부족"],
      "suggestions": ["성과를 수치로 표현해 보세요."]
    }
  ],
  "overall_score": 74,
  "inspected_at": "2025-03-11T12:15:00Z"
}
```

| 필드 | 타입 | 설명 |
|------|------|------|
| feedbacks | array&lt;object&gt; | 문항별 피드백 목록 |
| feedbacks[].draft_id | string | 문항 식별자 (DB drafts.id) |
| feedbacks[].question_text | string | 해당 문항 지문 (DB drafts에서 조회) |
| feedbacks[].score | integer | 0~100 점수 |
| feedbacks[].strengths | array&lt;string&gt; | 강점 목록 |
| feedbacks[].weaknesses | array&lt;string&gt; | 약점 목록 |
| feedbacks[].suggestions | array&lt;string&gt; | 개선 제안 목록 |
| overall_score | integer | 전체 문항 평균 점수 (0~100) |
| inspected_at | string | ISO8601 검수 시각 |

| 상태코드 | error | 발생조건 |
|----------|-------|----------|
| 400 | BAD_REQUEST | answers 배열 누락 또는 비어 있음, 또는 draft_id/answer 누락 |
| 401 | UNAUTHORIZED | 로그인 필요 |
| 404 | NOT_FOUND | draft_id에 해당하는 문항 없음 |

> 공통 에러(400/401/403/404/500/502)는 공통 규칙 참고.

---

## 4. 포트폴리오 API

### 4.1 POST `/api/portfolio/generate`

- **설명:** 인증된 사용자의 `selected_repos`(SSoT)를 기준으로 포트폴리오를 생성한다. 사용자 식별은 인증에서 추출한다.
- **SSoT 규칙:** 생성 대상 레포는 요청 바디가 아니라 `selected_repos` 테이블을 단일 진실원으로 사용한다.

#### 1. Request Syntax

```bash
curl -X POST "https://example.com/api/portfolio/generate" \
  -H "Authorization: Bearer <app-session-token>" \
  -H "Content-Type: application/json" \
  -d '{"job_id":"job_abc123"}'
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
| job_id | string | N | 공고 맞춤 포트폴리오 생성 시 사용. 없으면 범용 생성 |

**비고**

- 생성 대상 레포는 **GET/PUT `/api/user/selected-repos`** 기준으로 조회한다.
- job_id 없으면 공고 맥락 없이 User DB 전체 기반 범용 생성.

#### 4. Response

**200 OK**

```json
{
  "portfolio_id": "portfolio_20250304_001",
  "user_id": "uuid-internal",
  "portfolio": {
    "title": "mspark 포트폴리오",
    "summary": "선택한 2개 레포 기반 프로젝트 요약입니다.",
    "projects": [
      {
        "repo": "owner/repo-a",
        "intro": "owner/repo-a에서 쿼리 튜닝을 수행해 p95 35% 개선을 만든 프로젝트입니다.",
        "stars": [
          {"situation": "...", "task": "...", "action": "...", "result": "..."}
        ]
      }
    ]
  },
  "created_at": "2025-03-04T12:20:00Z"
}
```

| 필드 | 타입 | 설명 |
|------|------|------|
| portfolio.title | string | 포트폴리오 제목 |
| portfolio.summary | string | 전체 요약 |
| portfolio.projects | array&lt;object&gt; | 레포 단위 프로젝트 목록 |
| portfolio.projects[].repo | string | `owner/repo` |
| portfolio.projects[].intro | string | 레포 소개 문장 |
| portfolio.projects[].stars | array&lt;object&gt; | STAR 후보 목록 |
| portfolio.projects[].stars[].situation | string | STAR Situation |
| portfolio.projects[].stars[].task | string | STAR Task |
| portfolio.projects[].stars[].action | string | STAR Action |
| portfolio.projects[].stars[].result | string | STAR Result |

| 상태코드 | error | 발생조건 |
|----------|-------|----------|
| 400 | BAD_REQUEST | `selected_repos`가 비어 있음 (`NO_SELECTED_REPOS`) |
| 401 | UNAUTHORIZED | 로그인 필요 |
| 404 | NOT_FOUND | 사용자 없음 |
| 500 | INTERNAL_SERVER_ERROR | 그래프 실행 실패 또는 내부 예외 |

> 공통 에러 포맷은 `API_Common.md`를 따른다.
>
> ```json
> {
>   "error": "BAD_REQUEST",
>   "message": "NO_SELECTED_REPOS"
> }
> ```

---

### 4.2 GET `/api/portfolio`

- **설명:** 사용자의 기존 포트폴리오 목록/단건 조회

#### 1. Request Syntax

```bash
curl -X GET "https://example.com/api/portfolio?portfolio_id=portfolio_20250304_001" \
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
| portfolio_id | string | N | 지정 시 단건 조회 |

#### 4. Response

**200 OK (목록)**

```json
{
  "items": [
    {
      "portfolio_id": "portfolio_20250304_001",
      "created_at": "2025-03-04T12:20:00Z"
    }
  ]
}
```

**200 OK (단건)**

```json
{
  "portfolio_id": "portfolio_20250304_001",
  "user_id": "uuid-internal",
  "portfolio": {
    "title": "mspark 포트폴리오",
    "summary": "선택한 2개 레포 기반 프로젝트 요약입니다.",
    "projects": [
      {
        "repo": "owner/repo-a",
        "intro": "owner/repo-a에서 쿼리 튜닝을 수행해 p95 35% 개선을 만든 프로젝트입니다.",
        "stars": [
          {"situation": "...", "task": "...", "action": "...", "result": "..."}
        ]
      }
    ]
  },
  "created_at": "2025-03-04T12:20:00Z"
}
```

| 필드 | 타입 | 설명 |
|------|------|------|
| portfolio | object | 저장된 포트폴리오 JSON |

| 상태코드 | error | 발생조건 |
|----------|-------|----------|
| 401 | UNAUTHORIZED | 로그인 필요 |
| 404 | NOT_FOUND | portfolio_id에 해당하는 포트폴리오 없음 |

> 공통 에러(400/401/403/404/500/502)는 공통 규칙 참고.

---

## 5. 합격 자소서 검색 (내부 모듈)

- **설명:** 합격 자소서 DB(RAPTOR/VectorDB)에서 **유사한 사례를 검색**하는 모듈.
- **REST API 없음 – 내부 모듈.** Request/Response는 공개되지 않으며, `POST /api/cover-letter/draft` 내부에서만 호출되는 Retrieval 모듈이다.
- LangGraph Writer 그래프가:
  1. Job Fit / User Profile / GitHub 포트폴리오 정보를 보고,
  2. 합격 자소서 DB에서 유사 사례를 Retrieval,
  3. 이를 바탕으로 draft를 생성한다.
