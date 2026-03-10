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

- **설명:** 채용공고 텍스트/URL을 입력받아, **담당 업무 / 자격 요건 / 우대 사항 / 기업명 / 기업 인재상 / 포지션명** 6개 항목을 추출한다. **결과만 반환하고 저장하지 않는다.**

#### 1. Request Syntax

```bash
curl -X POST "https://example.com/api/jobs/parse" \
  -H "Authorization: Bearer <app-session-token>" \
  -H "Content-Type: application/json" \
  -d '{"source_type":"text","text":"당신이 합류하게 될 팀은 데이터 기반 의사결정을 중시합니다.","url":null,"language":"ko"}'
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
| source_type | string | Y | `text` \| `url` |
| text | string | N (source_type=text일 때 Y) | 채용공고 전문 텍스트 |
| url | string | N (source_type=url일 때 Y) | 채용공고 페이지 URL |
| language | string | N | default=ko |

#### 4. Response

**200 OK**

```json
{
  "position_title": "백엔드 개발자",
  "company_name": "Autofolio Corp",
  "company_persona": "데이터 기반 의사결정을 중시하는 스타트업",
  "duties": [
    "포트폴리오 생성 API 설계 및 구현",
    "GitHub 연동 및 임베딩 파이프라인 개발"
  ],
  "requirements": [
    "Python 3년 이상",
    "FastAPI 또는 유사 프레임워크 경험"
  ],
  "preferences": [
    "LangChain, LangGraph 사용 경험",
    "RAG 시스템 구축 경험"
  ],
  "raw_text": "당신이 합류하게 될 팀은 데이터 기반 의사결정을 중시합니다.",
  "parsed_at": "2025-03-04T12:00:00Z"
}
```

| 필드 | 타입 | 설명 |
|------|------|------|
| position_title | string | 포지션명 |
| company_name | string | 기업명 |
| company_persona | string | 기업 인재상 |
| duties | array&lt;string&gt; | 담당 업무 목록 |
| requirements | array&lt;string&gt; | 자격 요건 목록 |
| preferences | array&lt;string&gt; | 우대 사항 목록 |
| raw_text | string | 파싱에 사용된 원문 |
| parsed_at | string | ISO8601 파싱 시각 |

| 상태코드 | error | 발생조건 |
|----------|-------|----------|
| 400 | BAD_REQUEST | text와 url 모두 없음 또는 source_type에 맞는 필드 누락 |
| 401 | UNAUTHORIZED | 로그인 필요 |

> 공통 에러(400/401/403/404/500/502)는 공통 규칙 참고.

---

## 2. Job Fit API

### 2.1 POST `/api/job-fit`

- **설명:** User DB(프로필·임베딩)와 채용공고 파싱 결과를 비교하여 **Job Fit 점수**를 계산한다. 사용자 식별은 인증 토큰에서 서버가 추출한다. score_label 기준은 공통 규칙 참고.

#### 1. Request Syntax

```bash
curl -X POST "https://example.com/api/job-fit" \
  -H "Authorization: Bearer <app-session-token>" \
  -H "Content-Type: application/json" \
  -d '{"parsed_job":{"position_title":"백엔드 개발자","company_name":"Autofolio Corp","company_persona":"데이터 기반 의사결정을 중시하는 스타트업","duties":["포트폴리오 생성 API 설계 및 구현"],"requirements":["Python 3년 이상"],"preferences":["RAG 시스템 구축 경험"]}}'
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
| parsed_job | object | Y | /api/jobs/parse 응답과 동일 구조의 채용공고 파싱 결과 |
| parsed_job.position_title | string | Y | 포지션명 |
| parsed_job.company_name | string | Y | 기업명 |
| parsed_job.company_persona | string | N | 기업 인재상 |
| parsed_job.duties | array&lt;string&gt; | N | 담당 업무 목록 |
| parsed_job.requirements | array&lt;string&gt; | N | 자격 요건 목록 |
| parsed_job.preferences | array&lt;string&gt; | N | 우대 사항 목록 |

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

- **설명:** 자소서 문항과 채용공고/포트폴리오 정보를 기반으로 **자소서 초안**을 생성한다. 사용자 식별은 인증에서 추출한다.  
  내부적으로 **전략 수립 그래프**와 **합격 자소서 Retrieval 모듈**을 호출하지만, 이들은 별도 공개 API가 아니다.

#### 1. Request Syntax

```bash
curl -X POST "https://example.com/api/cover-letter/draft" \
  -H "Authorization: Bearer <app-session-token>" \
  -H "Content-Type: application/json" \
  -d '{"parsed_job":{"position_title":"백엔드 개발자","company_name":"Autofolio Corp","company_persona":"데이터 기반 의사결정을 중시하는 스타트업","duties":["포트폴리오 생성 API 설계 및 구현"],"requirements":["Python 3년 이상"],"preferences":["RAG 시스템 구축 경험"]},"question_text":"지원 동기와 입사 후 포부를 작성해 주세요.","max_chars":2000,"min_chars":1000,"tone":"professional"}'
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
| parsed_job | object | N | 채용공고 파싱 결과(선택). /api/jobs/parse 응답과 동일 구조 |
| parsed_job.position_title | string | N | 포지션명 |
| parsed_job.company_name | string | N | 기업명 |
| parsed_job.company_persona | string | N | 기업 인재상 |
| parsed_job.duties | array&lt;string&gt; | N | 담당 업무 목록 |
| parsed_job.requirements | array&lt;string&gt; | N | 자격 요건 목록 |
| parsed_job.preferences | array&lt;string&gt; | N | 우대 사항 목록 |
| question_text | string | Y | 자소서 문항 지문 |
| max_chars | integer | Y | 최대 글자 수 |
| min_chars | integer | N | 최소 글자 수 |
| tone | string | N | professional \| friendly \| concise, default=professional |

#### 4. Response

**200 OK**

```json
{
  "draft_id": "draft_20250304_001",
  "question_text": "지원 동기와 입사 후 포부를 작성해 주세요.",
  "answer": "저는 개발자로서 사용자 가치를 만드는 일에 기여하고자 지원했습니다. 입사 후에는 포트폴리오 API와 RAG 파이프라인 경험을 바탕으로 제품 품질과 개발 효율을 함께 높이고 싶습니다.",
  "used_assets": {
    "github_repos": [
      { "id": 123, "full_name": "Ara5429/subway-rag-chatbot" }
    ],
    "portfolio_ids": ["portfolio_20250301_001"],
    "accepted_essays_used": true
  },
  "created_at": "2025-03-04T12:10:00Z"
}
```

| 필드 | 타입 | 설명 |
|------|------|------|
| draft_id | string | 생성된 초안 식별자 |
| question_text | string | 요청한 문항 지문 |
| answer | string | 생성된 자소서 본문 |
| used_assets | object | 초안 생성에 사용된 자원 |
| used_assets.github_repos | array&lt;object&gt; | 참조된 GitHub 레포 목록 |
| used_assets.github_repos[].id | integer | 레포 ID |
| used_assets.github_repos[].full_name | string | owner/name |
| used_assets.portfolio_ids | array&lt;string&gt; | 참조된 포트폴리오 ID 목록 |
| used_assets.accepted_essays_used | boolean | 합격 자소서 DB 사용 여부 |
| created_at | string | ISO8601 생성 시각 |

| 상태코드 | error | 발생조건 |
|----------|-------|----------|
| 400 | BAD_REQUEST | question_text 또는 max_chars 누락 등 |
| 401 | UNAUTHORIZED | 로그인 필요 |

> 공통 에러(400/401/403/404/500/502)는 공통 규칙 참고.

---

### 3.2 POST `/api/cover-letter/inspect`

- **설명:** 사용자가 작성한 자소서를 분석하고, **피드백·수정 제안**을 반환한다. (Inspector 그래프) score_label 기준은 공통 규칙 참고.

#### 1. Request Syntax

```bash
curl -X POST "https://example.com/api/cover-letter/inspect" \
  -H "Authorization: Bearer <app-session-token>" \
  -H "Content-Type: application/json" \
  -d '{"question_text":"지원 동기와 입사 후 포부를 작성해 주세요.","answer":"저는 개발자로서 사용자 가치를 만드는 일에 기여하고자 지원했습니다.","mode":"full_review"}'
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
| question_text | string | Y | 자소서 문항 지문 |
| answer | string | Y | 사용자가 작성한 자소서 본문 |
| mode | string | N | full_review \| quick_check, default=full_review |

#### 4. Response

**200 OK**

```json
{
  "inspection_id": "inspect_20250304_001",
  "score": 0.78,
  "score_label": "GOOD",
  "strengths": [
    "구체적인 STAR 구조가 잘 드러납니다.",
    "역할과 영향이 분리되어 설명되었습니다."
  ],
  "weaknesses": [
    "회사/포지션에 대한 맞춤형 언급이 부족합니다."
  ],
  "suggestions": [
    "회사 비전과 개인 경험을 연결하는 문장을 2~3줄 추가해 보세요.",
    "수치/지표를 한 군데 정도 더 넣으면 설득력이 높아집니다."
  ],
  "inspected_at": "2025-03-04T12:15:00Z"
}
```

| 필드 | 타입 | 설명 |
|------|------|------|
| inspection_id | string | 검수 결과 식별자 |
| score | number (float) | 0~1 점수 |
| score_label | string | 점수 등급 라벨 |
| strengths | array&lt;string&gt; | 강점 목록 |
| weaknesses | array&lt;string&gt; | 약점 목록 |
| suggestions | array&lt;string&gt; | 수정 제안 목록 |
| inspected_at | string | ISO8601 검수 시각 |

| 상태코드 | error | 발생조건 |
|----------|-------|----------|
| 400 | BAD_REQUEST | question_text 또는 answer 누락 |
| 401 | UNAUTHORIZED | 로그인 필요 |

> 공통 에러(400/401/403/404/500/502)는 공통 규칙 참고.

---

## 4. 포트폴리오 API

### 4.1 POST `/api/portfolio/generate`

- **설명:** GitHub 레포, 이력서·포트폴리오 문서, Job Fit 정보를 종합하여 **포트폴리오 초안**을 생성한다. 사용자 식별은 인증에서 추출한다.

#### 1. Request Syntax

```bash
curl -X POST "https://example.com/api/portfolio/generate" \
  -H "Authorization: Bearer <app-session-token>" \
  -H "Content-Type: application/json" \
  -d '{"parsed_job":{"position_title":"백엔드 개발자","company_name":"Autofolio Corp","company_persona":"데이터 기반 의사결정을 중시하는 스타트업","duties":["포트폴리오 생성 API 설계 및 구현"],"requirements":["Python 3년 이상"],"preferences":["RAG 시스템 구축 경험"]},"github_repo_ids":[123,456],"document_ids":["doc_20250301_001"],"language":"ko"}'
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
| parsed_job | object | N | 채용공고 파싱 결과(선택). /api/jobs/parse 응답과 동일 구조 |
| parsed_job.position_title | string | N | 포지션명 |
| parsed_job.company_name | string | N | 기업명 |
| parsed_job.company_persona | string | N | 기업 인재상 |
| parsed_job.duties | array&lt;string&gt; | N | 담당 업무 목록 |
| parsed_job.requirements | array&lt;string&gt; | N | 자격 요건 목록 |
| parsed_job.preferences | array&lt;string&gt; | N | 우대 사항 목록 |
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
