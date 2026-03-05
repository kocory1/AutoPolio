## Autofolio 서비스 API 명세 (Job / Cover Letter / Portfolio)

**버전:** 1.0  
**최종 정리일:** 2025-03-04

이 문서는 Autofolio의 **서비스 레벨 API**(채용공고 파싱, Job Fit, 자소서 Draft/검수, 포트폴리오)를 정의한다.  
GitHub 관련 API는 `API_GitHub_Spec.md` 를 참고한다.

---

### 공통 규칙

- **인증:** 세션 쿠키 또는 `Authorization: Bearer <app-session-token>`
- **에러 응답 포맷(공통):**

```json
{
  "error": "ERROR_CODE",
  "message": "사람이 읽을 수 있는 에러 설명"
}
```

---

## 1. 채용공고 파싱 API

### 1.1 POST `/api/jobs/parse`

- **설명:** 채용공고 텍스트/URL을 입력받아, **담당 업무 / 자격 요건 / 우대 사항 / 기업명 / 기업 인재상 / 포지션명** 6개 항목을 추출한다.

#### Request

- **Body (JSON)**

```json
{
  "source_type": "text",
  "text": "당신이 합류하게 될 팀은...",
  "url": null,
  "language": "ko"
}
```

- `source_type`: string, required  
  - 허용값: `text` \| `url`  
- `text`: string, optional (source_type=`text`일 때 필수)  
  - 채용공고 전문 텍스트
- `url`: string, optional (source_type=`url`일 때 필수)  
  - 채용공고 페이지 URL
- `language`: string, optional, default=`ko`

#### Response

- **200 OK**

```json
{
  "job_id": "job_20250304_001",
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
  "raw_text": "당신이 합류하게 될 팀은...",
  "parsed_at": "2025-03-04T12:00:00Z"
}
```

- **400 BAD_REQUEST**

```json
{
  "error": "BAD_REQUEST",
  "message": "Either text or url must be provided."
}
```

---

## 2. Job Fit API

### 2.1 POST `/api/job-fit`

- **설명:** User DB(프로필·임베딩)와 채용공고 파싱 결과를 비교하여 **Job Fit 점수**를 계산한다.

#### Request

- **Body (JSON)**

```json
{
  "user_id": "uuid-internal",
  "job_id": "job_20250304_001"
}
```

- `user_id`: string, required  
  - 내부 User DB의 식별자
- `job_id`: string, required  
  - `/api/jobs/parse` 결과에서 반환된 `job_id`

#### Response

- **200 OK**

```json
{
  "user_id": "uuid-internal",
  "job_id": "job_20250304_001",
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

- **404 NOT_FOUND**

```json
{
  "error": "NOT_FOUND",
  "message": "User or job not found."
}
```

---

## 3. 자소서 API (Writer / Inspector)

### 3.1 POST `/api/cover-letter/draft`

- **설명:** 자소서 문항과 채용공고/포트폴리오 정보를 기반으로 **자소서 초안**을 생성한다.  
  - 내부적으로 **전략 수립 그래프**와 **합격 자소서 Retrieval 모듈**을 호출하지만, 이들은 별도 공개 API가 아니다.

#### Request

- **Body (JSON)**

```json
{
  "user_id": "uuid-internal",
  "job_id": "job_20250304_001",
  "question_id": "q1",
  "question_text": "지원 동기와 입사 후 포부를 작성해 주세요.",
  "constraints": {
    "min_chars": 1000,
    "max_chars": 2000,
    "tone": "professional"
  }
}
```

#### Response

- **200 OK**

```json
{
  "draft_id": "draft_20250304_001",
  "user_id": "uuid-internal",
  "job_id": "job_20250304_001",
  "question_id": "q1",
  "answer": "저는 개발자로서 ...",
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

- **비고**
  - **합격 자소서 검색**은 REST API가 아니며, 이 엔드포인트 내부에서만 호출되는 Retrieval 모듈이다.

---

### 3.2 POST `/api/cover-letter/inspect`

- **설명:** 사용자가 작성한 자소서를 분석하고, **피드백·수정 제안**을 반환한다. (Inspector 그래프)

#### Request

- **Body (JSON)**

```json
{
  "user_id": "uuid-internal",
  "job_id": "job_20250304_001",
  "question_id": "q1",
  "answer": "저는 개발자로서 ...",
  "mode": "full_review"
}
```

- `mode`: string, optional, default=`full_review`  
  - `full_review` \| `quick_check`

#### Response

- **200 OK**

```json
{
  "inspection_id": "inspect_20250304_001",
  "user_id": "uuid-internal",
  "job_id": "job_20250304_001",
  "question_id": "q1",
  "score": 0.78,
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

---

## 4. 포트폴리오 API

### 4.1 POST `/api/portfolio/generate`

- **설명:** GitHub 레포, 이력서·포트폴리오 문서, Job Fit 정보를 종합하여 **포트폴리오 초안**을 생성한다.

#### Request

- **Body (JSON)**

```json
{
  "user_id": "uuid-internal",
  "job_id": "job_20250304_001",
  "github_repo_ids": [123, 456],
  "document_ids": ["doc_20250301_001"],
  "language": "ko"
}
```

#### Response

- **200 OK**

```json
{
  "portfolio_id": "portfolio_20250304_001",
  "user_id": "uuid-internal",
  "job_id": "job_20250304_001",
  "language": "ko",
  "sections": [
    {
      "id": "summary",
      "title": "요약",
      "content": "3년차 백엔드 개발자로서..."
    },
    {
      "id": "projects",
      "title": "주요 프로젝트",
      "content": "- subway-rag-chatbot: ..."
    }
  ],
  "created_at": "2025-03-04T12:20:00Z"
}
```

---

### 4.2 GET `/api/portfolio`

- **설명:** 사용자의 기존 포트폴리오 목록/단건 조회

#### Request

- **Query Parameters**
  - `user_id`: string, optional (기본=현재 로그인 유저)
  - `portfolio_id`: string, optional (제공 시 단건 조회)

#### Response

- **200 OK (목록)**

```json
{
  "items": [
    {
      "portfolio_id": "portfolio_20250304_001",
      "job_id": "job_20250304_001",
      "created_at": "2025-03-04T12:20:00Z"
    }
  ]
}
```

- **200 OK (단건)**

```json
{
  "portfolio_id": "portfolio_20250304_001",
  "user_id": "uuid-internal",
  "job_id": "job_20250304_001",
  "language": "ko",
  "sections": [
    { "id": "summary", "title": "요약", "content": "..." },
    { "id": "projects", "title": "주요 프로젝트", "content": "..." }
  ],
  "created_at": "2025-03-04T12:20:00Z"
}
```

---

## 5. 합격 자소서 검색 (내부 모듈)

- **설명:** 합격 자소서 DB(RAPTOR/VectorDB)에서 **유사한 사례를 검색**하는 모듈.
- **중요:** 이 기능은 **REST API로 공개되지 않으며**,  
  - `POST /api/cover-letter/draft` 내부에서만 호출되는 **내부 Retrieval 모듈**이다.
- LangGraph Writer 그래프가:
  1. Job Fit / User Profile / GitHub 포트폴리오 정보를 보고,
  2. 합격 자소서 DB에서 유사 사례를 Retrieval,
  3. 이를 바탕으로 draft를 생성한다.

