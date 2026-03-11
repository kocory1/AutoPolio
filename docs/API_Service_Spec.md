## Autofolio 서비스 API 명세 (Job / Cover Letter / Portfolio)

**버전:** 1.0  
**최종 정리일:** 2025-03-04

이 문서는 Autofolio의 **서비스 레벨 API**(채용공고 파싱, Job Fit, 자소서 Draft/검수, 포트폴리오)를 정의한다.  
GitHub 관련 API는 `API_GitHub_Spec.md` 를 참고한다.

---

### 공통 규칙

> 공통 요청 형식, 공통 에러 코드, score_label 기준은 `API_Common.md` 참고.

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
  - **source_type=url:** `url` 필수. 서버가 해당 URL을 크롤링 후 LLM으로 파싱. 동일 url이 이미 jobs에 있으면 재파싱 없이 캐시 반환. 크롤링 실패 시 400 CRAWL_FAILED.  
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
  "cached": false,
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
| cached | boolean | source_type=url일 때, 동일 url 캐시 반환 시 true |
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

- **설명:** User DB(프로필·임베딩)와 채용공고 정보를 비교하여 **Job Fit 점수**를 계산한다. 사용자 식별은 인증 토큰에서 서버가 추출한다. score_label 기준은 공통 규칙 참고.  
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
  "score": 0.82,
  "score_label": "HIGH",
  "factors": [
    {
      "name": "skills_match",
      "weight": 0.5,
      "score": 0.9,
      "detail": "Python, FastAPI, RAG 경험이 요구사항과 잘 맞습니다."
    },
    {
      "name": "experience_level",
      "weight": 0.3,
      "score": 0.75,
      "detail": "경력 연차는 살짝 부족하지만 유사 프로젝트 경험으로 보완됩니다."
    },
    {
      "name": "company_fit",
      "weight": 0.2,
      "score": 0.7,
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

- **설명:** 동일 공고·동일 톤으로 **3~5개 문항을 한 번에** 일관성 있게 초안 생성한다. 요청은 `questions` 배열로 묶으며, 서버는 **draft_sessions** 단위로 세션을 만들고 **cover_letter_items** 단위로 문항별 초안을 저장한다. 사용자 식별은 인증에서 추출한다.  
  내부적으로 **전략 수립 그래프**와 **합격 자소서 Retrieval 모듈**을 호출하지만, 이들은 별도 공개 API가 아니다.  
  **비고:** job_id 없으면 공고 맥락 없이 User DB 전체 기반 범용 생성.

#### 1. Request Syntax

```bash
curl -X POST "https://example.com/api/cover-letter/draft" \
  -H "Authorization: Bearer <app-session-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "job_abc123",
    "tone": "professional",
    "questions": [
      { "question_text": "지원 동기를 작성해주세요.", "max_chars": 1500, "min_chars": 800 },
      { "question_text": "본인의 강점을 서술해주세요.", "max_chars": 1000 },
      { "question_text": "입사 후 포부를 작성해주세요.", "max_chars": 1000, "min_chars": 500 }
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
| tone | string | N | professional \| friendly \| concise, default=professional |
| questions | array&lt;object&gt; | Y | 문항별 입력. 비어 있으면 안 됨 |

**questions[] 각 object**

| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| question_text | string | Y | 자소서 문항 지문 |
| max_chars | integer | Y | 해당 문항 최대 글자 수 |
| min_chars | integer | N | 해당 문항 최소 글자 수 |

#### 4. Response

**200 OK**

```json
{
  "draft_session_id": "session_20250311_001",
  "drafts": [
    {
      "draft_id": "item_001",
      "question_text": "지원 동기를 작성해주세요.",
      "answer": "저는 개발자로서...",
      "char_count": 1342
    },
    {
      "draft_id": "item_002",
      "question_text": "본인의 강점을 서술해주세요.",
      "answer": "저의 강점은...",
      "char_count": 876
    },
    {
      "draft_id": "item_003",
      "question_text": "입사 후 포부를 작성해주세요.",
      "answer": "입사 후에는...",
      "char_count": 654
    }
  ],
  "used_assets": {
    "github_repos": [
      { "id": 123, "full_name": "Ara5429/subway-rag-chatbot" }
    ],
    "portfolio_ids": ["portfolio_20250301_001"],
    "accepted_essays_used": true
  },
  "created_at": "2025-03-11T12:10:00Z"
}
```

| 필드 | 타입 | 설명 |
|------|------|------|
| draft_session_id | string | DB draft_sessions.id에 대응하는 세션 식별자 |
| drafts | array&lt;object&gt; | 문항별 초안 목록 |
| drafts[].draft_id | string | 문항별 고유 식별자 (DB cover_letter_items.id) |
| drafts[].question_text | string | 해당 문항 지문 |
| drafts[].answer | string | 생성된 자소서 본문 |
| drafts[].char_count | integer | 생성된 본문 글자 수 |
| used_assets | object | 세션 전체 공통으로 사용된 자원 |
| used_assets.github_repos | array&lt;object&gt; | 참조된 GitHub 레포 목록 |
| used_assets.github_repos[].id | integer | 레포 ID |
| used_assets.github_repos[].full_name | string | owner/name |
| used_assets.portfolio_ids | array&lt;string&gt; | 참조된 포트폴리오 ID 목록 |
| used_assets.accepted_essays_used | boolean | 합격 자소서 DB 사용 여부 |
| created_at | string | ISO8601 생성 시각 |

| 상태코드 | error | 발생조건 |
|----------|-------|----------|
| 400 | BAD_REQUEST | questions 배열이 비어 있거나 누락, 또는 문항 중 question_text/max_chars 누락 |
| 401 | UNAUTHORIZED | 로그인 필요 |

> 공통 에러(400/401/403/404/500/502)는 공통 규칙 참고.

---

### 3.2 POST `/api/cover-letter/inspect`

- **설명:** 자소서 세션 전체 문항의 답변을 한번에 입력받아, 문항별 피드백을 반환한다. (Inspector 그래프) score_label 기준은 공통 규칙 참고.

#### 1. Request Syntax

```bash
curl -X POST "https://example.com/api/cover-letter/inspect" \
  -H "Authorization: Bearer <app-session-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "draft_session_id": "session_20250311_001",
    "answers": [
      { "draft_id": "item_001", "answer": "저는 개발자로서..." },
      { "draft_id": "item_002", "answer": "저의 강점은..." },
      { "draft_id": "item_003", "answer": "입사 후에는..." }
    ],
    "mode": "full_review"
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
| draft_session_id | string | Y | POST /api/cover-letter/draft 응답의 draft_session_id |
| answers | array&lt;object&gt; | Y | 문항별 답변. 비어 있으면 안 됨 |
| mode | string | N | full_review \| quick_check, default=full_review |

**answers[] 각 object**

| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| draft_id | string | Y | 문항별 식별자 (draft 응답의 draft_id) |
| answer | string | Y | 해당 문항 작성본 (초안 그대로 또는 사용자 수정본) |

#### 4. Response

**200 OK**

```json
{
  "inspection_session_id": "inspect_session_20250311_001",
  "feedbacks": [
    {
      "draft_id": "item_001",
      "question_text": "지원 동기를 작성해주세요.",
      "score": 0.85,
      "score_label": "HIGH",
      "strengths": ["STAR 구조가 명확하게 드러납니다."],
      "weaknesses": ["회사 맞춤 언급이 부족합니다."],
      "suggestions": ["회사 비전과 개인 경험을 연결하는 문장을 추가해 보세요."]
    },
    {
      "draft_id": "item_002",
      "question_text": "본인의 강점을 서술해주세요.",
      "score": 0.62,
      "score_label": "GOOD",
      "strengths": ["구체적인 프로젝트 사례가 포함되어 있습니다."],
      "weaknesses": ["수치 근거가 부족합니다."],
      "suggestions": ["프로젝트 성과를 수치로 표현해 보세요."]
    },
    {
      "draft_id": "item_003",
      "question_text": "입사 후 포부를 작성해주세요.",
      "score": 0.55,
      "score_label": "LOW",
      "strengths": [],
      "weaknesses": ["구체성이 없습니다.", "포지션과의 연결이 부족합니다."],
      "suggestions": ["담당 업무와 연결된 구체적 목표를 서술해 보세요."]
    }
  ],
  "overall_score": 0.67,
  "overall_score_label": "GOOD",
  "inspected_at": "2025-03-11T12:15:00Z"
}
```

| 필드 | 타입 | 설명 |
|------|------|------|
| inspection_session_id | string | 검수 세션 식별자 |
| feedbacks | array&lt;object&gt; | 문항별 피드백 목록 |
| feedbacks[].draft_id | string | 문항 식별자 (draft_id와 대응) |
| feedbacks[].question_text | string | 해당 문항 지문 |
| feedbacks[].score | number (float) | 0~1 점수 |
| feedbacks[].score_label | string | HIGH / GOOD / LOW |
| feedbacks[].strengths | array&lt;string&gt; | 강점 목록 |
| feedbacks[].weaknesses | array&lt;string&gt; | 약점 목록 |
| feedbacks[].suggestions | array&lt;string&gt; | 개선 제안 목록 |
| overall_score | number (float) | 전체 문항 평균 점수 |
| overall_score_label | string | 전체 등급 |
| inspected_at | string | ISO8601 검수 시각 |

| 상태코드 | error | 발생조건 |
|----------|-------|----------|
| 400 | BAD_REQUEST | draft_session_id 누락, answers 배열 비어 있음, 또는 draft_id/answer 누락 |
| 401 | UNAUTHORIZED | 로그인 필요 |
| 404 | NOT_FOUND | draft_session_id에 해당하는 세션 없음 |

> 공통 에러(400/401/403/404/500/502)는 공통 규칙 참고.

---

## 4. 포트폴리오 API

### 4.1 POST `/api/portfolio/generate`

- **설명:** GitHub 레포, 이력서·포트폴리오 문서, Job Fit 정보를 종합하여 **포트폴리오 초안**을 생성한다. 사용자 식별은 인증에서 추출한다.  
  **비고:** job_id 없으면 공고 맥락 없이 User DB 전체 기반 범용 생성.

#### 1. Request Syntax

```bash
curl -X POST "https://example.com/api/portfolio/generate" \
  -H "Authorization: Bearer <app-session-token>" \
  -H "Content-Type: application/json" \
  -d '{"job_id":"job_abc123","github_repo_ids":[123,456],"document_ids":["doc_20250301_001"],"language":"ko"}'
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
| github_repo_ids | array&lt;integer&gt; | N | 포함할 GitHub 레포 ID 목록 |
| document_ids | array&lt;string&gt; | N | 포함할 문서 ID 목록 |
| language | string | N | ko 등, default=ko |

#### 4. Response

**200 OK**

```json
{
  "portfolio_id": "portfolio_20250304_001",
  "user_id": "uuid-internal",
  "language": "ko",
  "sections": [
    {
      "id": "summary",
      "title": "요약",
      "content": "3년차 백엔드 개발자로서 RAG와 API 설계 경험을 보유하고 있으며, 데이터 기반 제품 개발에 기여하고자 합니다."
    },
    {
      "id": "projects",
      "title": "주요 프로젝트",
      "content": "subway-rag-chatbot: 지하철 경로 안내 RAG 챗봇 설계 및 구현. LangChain 기반 검색 파이프라인과 FastAPI 백엔드를 담당했습니다."
    }
  ],
  "created_at": "2025-03-04T12:20:00Z"
}
```

| 필드 | 타입 | 설명 |
|------|------|------|
| sections | array&lt;object&gt; | 포트폴리오 섹션 목록 |
| sections[].id | string | 섹션 식별자 |
| sections[].title | string | 섹션 제목 |
| sections[].content | string | 섹션 본문 |

| 상태코드 | error | 발생조건 |
|----------|-------|----------|
| 401 | UNAUTHORIZED | 로그인 필요 |
| 404 | NOT_FOUND | user 또는 리소스 없음 |

> 공통 에러(400/401/403/404/500/502)는 공통 규칙 참고.

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
| user_id | string | N | 기본=현재 로그인 유저 |
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
  "language": "ko",
  "sections": [
    {
      "id": "summary",
      "title": "요약",
      "content": "3년차 백엔드 개발자로서 RAG와 API 설계 경험을 보유하고 있으며, 데이터 기반 제품 개발에 기여하고자 합니다."
    },
    {
      "id": "projects",
      "title": "주요 프로젝트",
      "content": "subway-rag-chatbot: 지하철 경로 안내 RAG 챗봇 설계 및 구현. LangChain 기반 검색 파이프라인과 FastAPI 백엔드를 담당했습니다."
    }
  ],
  "created_at": "2025-03-04T12:20:00Z"
}
```

| 필드 | 타입 | 설명 |
|------|------|------|
| sections[].id | string | 섹션 식별자 |
| sections[].title | string | 섹션 제목 |
| sections[].content | string | 섹션 본문 |

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
