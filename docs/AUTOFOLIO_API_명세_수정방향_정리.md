# Autofolio API 명세·수정 방향 정리

**문서 버전:** 1.0  
**기준:** [AUTOFOLIO_기획서.md](AUTOFOLIO_기획서.md), [AUTOFOLIO_LangGraph_설계.md](AUTOFOLIO_LangGraph_설계.md)

---

## 1. 개요

API 명세 수정 방향 정리. 전략 수립 제외, 채용공고 6가지 추출, 합격 자소서 내부 모듈, Job Fit 등 결정 사항 반영.

---

## 2. 반영한 수정 방향

| 항목 | 수정 방향 | 반영 문서 |
|------|-----------|-----------|
| **전략 수립** | **없음.** Writer 그래프 내부에서 유사 샘플 → 유저 DB(에셋) 조회 후 초안. | Writer 파이프라인 제안, API 스펙 |
| **채용 공고 파싱** | 추출 항목: **담당 업무 / 자격 요건 / 우대 사항 / 기업명 / 기업 인재상 / 포지션명** (6가지). 자소서 문항은 **유저 입력** | 채용공고파싱전략, 기획서, 파이프라인, 16주 계획표 |
| **이력서/포트폴리오** | 지원 포맷 **PDF, PPT** 명시 (표·문구) | 기획서 |
| **합격 자소서 검색** | 대외 API 아님. Writer 그래프가 **내부 모듈**로 호출. 별도 REST API 노출 없음. | LangGraph 설계, 16주 계획표, RAG 파이프라인 |
| **Job Fit** | **User DB**(프로필·임베딩) vs **공고 파싱 API 반환값** 비교 → Job Fit 점수 API 호출 | LangGraph 설계, 파이프라인, RAG 파이프라인, 기획서, 16주 계획표 |
| **GitHub 연동 해제** | 제공하지 않음. 로그아웃으로 충분. | 기획서 제약·범위 |

---

## 3. API 명세 요약 (수정 반영 후)

- **인증:** GET /api/auth/github/login, callback, GET /api/auth/logout.
- **유저:** GET /api/me, GET·PUT /api/user/selected-repos, POST /api/user/documents (PDF·PPT 업로드 → OCR·처리 → VectorDB 저장).
- **GitHub:** GET /api/github/repos, /repos/{id}, /repos/{id}/tree, /repos/{id}/commits, POST /repos/{id}/embedding.
- **채용공고:** POST /api/jobs/parse → 담당업무/자격요건/우대사항/기업명/기업인재상/포지션명 추출. 자소서 문항은 유저 입력.
- **Job Fit:** GET 또는 POST /api/job-fit (User DB + 공고 API 반환값 비교 → 점수).
- **자소서:** POST /api/cover-letter/draft (문항 → Writer: 유사 샘플 → 유저 DB 에셋 → 초안. 전략 수립 없음), POST /api/cover-letter/inspect.
- **포트폴리오:** POST /api/portfolio/generate, GET /api/portfolio.
- **합격 자소서 검색:** REST API 없음. Writer 내부에서 검색 모듈 호출.

---

## 4. 문서 관계

- API 스펙: [AUTOFOLIO_API_스펙.md](AUTOFOLIO_API_스펙.md)
- LangGraph 설계: [AUTOFOLIO_LangGraph_설계.md](AUTOFOLIO_LangGraph_설계.md)

---

## 5. 문서 이력

- 1.0 (2026-03-04): 수정 방향 반영, API 명세 요약 정리.
