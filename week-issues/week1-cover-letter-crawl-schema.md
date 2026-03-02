## Week1 - 자소서 크롤링 및 합격 자소서 스키마 정의

**주차 목표**
- 합격 자소서 데이터 수집: 잡코리아·링커리어 크롤링으로 질문/답변 쌍 확보.
- 합격 자소서 공통 스키마 정의: 출처·회사·직무·연도·questions 배열(question/answer) 등으로 통일.

**이번 주 작업 범위**
1. 잡코리아 합격 자소서 목록 수집 및 상세 페이지 크롤링 (질문·답변 추출).
2. 링커리어 합격 자소서 목록 수집 및 상세 페이지 크롤링 (질문·답변 추출).
3. 두 출처를 하나의 JSON 스키마로 통일 (id, source, url, company, position, year, questions[], expert_feedback 등).

---

### 1. 레퍼런스 문서 요약
- 합격 자소서는 RAG에서 **Writer/Inspector 그래프**의 참고 샘플로 사용. 검색 API(P1)로 조회 후 문항·전략에 맞게 활용.
- 스키마 통일로 잡코리아/링커리어 데이터를 동일 포맷으로 저장·검색 가능하게 함.

---

### 2. 이번 주 TODO
- [x] 잡코리아 합격 자소서 URL 목록 수집 스크립트
- [x] 잡코리아 상세 페이지 크롤링 (질문/답변 파싱) 및 JSON 저장
- [x] 링커리어 합격 자소서 URL 목록 수집
- [x] 링커리어 상세 페이지 크롤링 (질문/답변 파싱) 및 JSON 저장
- [x] 합격 자소서 공통 스키마 정의 및 두 출처 데이터 동일 형식으로 저장
  - 필드: `id`, `source`, `url`, `crawled_at`, `company`, `position`, `year`, `questions` (배열: `question`, `answer`), `expert_feedback`
- [x] (선택) 링커리어 본문 LLM 추출: content 필터 없이 context에 넣고 OpenAI로 Q&A 분리 후 잡코리아 JSON 형식으로 저장

---

### 3. 진행 로그
- 1주차
  - [x] 잡코리아·링커리어 크롤링 스크립트 작성 및 실행
  - [x] 합격 자소서 JSON 스키마 확정 (잡코리아/링커리어 동일 구조)
  - [x] data/jobkorea, data/linkareer 디렉터리에 스키마에 맞춰 데이터 저장
