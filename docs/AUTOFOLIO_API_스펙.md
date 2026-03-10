# Autofolio API 명세서

**문서 버전:** 1.0  
**기준:** [AUTOFOLIO_API_명세_수정방향_정리.md](AUTOFOLIO_API_명세_수정방향_정리.md), [AUTOFOLIO_LangGraph_설계.md](AUTOFOLIO_LangGraph_설계.md)

---

## 1. 개요

Phase 1~3 API 엔드포인트 명세. 인증·유저·GitHub·채용공고·Job Fit·자소서·포트폴리오 API 정의. 수정 방향 반영.

---

## 2. 엔드포인트 요약


| 구분          | 메서드         | 경로                                 | 설명                                                                      |
| ----------- | ----------- | ---------------------------------- | ----------------------------------------------------------------------- |
| **인증**      | GET         | `/api/auth/github/login`           | GitHub OAuth 시작(리다이렉트)                                                  |
|             | GET         | `/api/auth/github/callback`        | OAuth 콜백, 토큰·세션 처리                                                      |
|             | GET         | `/api/auth/logout`                 | 로그아웃                                                                    |
| **유저**      | GET         | `/api/me`                          | 현재 로그인 유저 정보                                                            |
|             | GET         | `/api/user/selected-repos`         | 선택 레포 목록 조회                                                             |
|             | PUT         | `/api/user/selected-repos`         | 선택 레포 목록 저장                                                             |
|             | POST        | `/api/user/documents`              | 이력서·포트폴리오 **PDF·PPT** 업로드 → OCR·처리 → VectorDB 저장 → 성공 여부 반환             |
| **GitHub**  | GET         | `/api/github/repos`                | 레포 목록                                                                   |
|             | GET         | `/api/github/repos/{id}`           | 레포 단건 상세                                                                |
|             | GET         | `/api/github/repos/{id}/tree`      | 파일/폴더 트리 또는 파일 내용 (`?path=` 등)                                          |
|             | GET         | `/api/github/repos/{id}/commits`   | 커밋 목록                                                                   |
|             | POST        | `/api/github/repos/{id}/embedding` | 임베딩 생성/갱신 요청(비동기)                                                       |
| **채용공고**    | POST        | `/api/jobs/parse`                  | 공고 URL 입력 → **담당 업무 / 자격 요건 / 우대 사항 / 기업명 / 기업 인재상 / 포지션명** 추출 (1개 API). 자소서 문항은 유저 입력. |
| **Job Fit** | GET 또는 POST | `/api/job-fit`                     | **User DB**(프로필·임베딩) vs **공고 파싱 API 반환값** 비교 → Job Fit 점수·순위 (1개)       |
| **자소서**     | POST        | `/api/cover-letter/draft`          | 문항 입력 → Writer 그래프(유사 샘플 → 유저 DB 에셋 조회 → 초안). **전략 수립 없음** |
|             | POST        | `/api/cover-letter/inspect`        | 초안 + (선택) 유저 수정본 → Inspector → 첨삭 피드백 반환                                |
| **포트폴리오**   | POST        | `/api/portfolio/generate`          | 1번 그래프 호출 → 포트폴리오 생성                                                    |
|             | GET         | `/api/portfolio`                   | 내 포트폴리오 조회                                                              |


---

## 3. 구분별 상세

### 3.1 인증

- **GitHub 연동 해제:** 제공하지 않음. 로그아웃으로 충분.

### 3.2 유저

- **문서 업로드:** 지원 포맷 **PDF, PPT**. 전처리(필요 시 멀티모달) 후 VectorDB 저장.

### 3.3 채용공고 파싱

- **추출 항목 (6가지):** 담당 업무, 자격 요건, 우대 사항, 기업명, 기업 인재상, 포지션명. 자소서 문항(질문+글자수)은 **유저가 draft API 요청 시 입력**.
- 상세 스키마·프롬프트: [AUTOFOLIO_채용공고파싱전략.md](AUTOFOLIO_채용공고파싱전략.md).

### 3.4 Job Fit

- **동작:** 클라이언트가 공고 파싱 결과(또는 공고 ID)를 넘기면, 서버가 **User DB**(프로필·임베딩)와 비교해 유사도 기반 점수·순위 반환.
- Writer 등은 별도 API 없음. draft 시 Writer 그래프 내부에서 유사 샘플 → 유저 DB 에셋 조회 후 초안 생성. (전략 수립 없음)

### 3.5 자소서

- **draft:** **유저가 문항(질문+글자수) 직접 입력** → Writer 그래프(유사 샘플 검색 → **유저 DB 에셋 조회** → 초안 생성) → 초안 반환. (전략 수립 없음)
  - 요청 body: `{ "question_text": "...", "max_chars": 500, "job_id": "..." (선택) }` — `question_text`, `max_chars` 필수. `user_id`는 인증에서 추출.
- **합격 자소서 검색:** 대외 REST API 없음. Writer 그래프 내부 모듈로만 사용.

### 3.6 포트폴리오

- **generate:** LangGraph 포트폴리오 생성 그래프(load_profile → build_star_sentence → self_consistency → build_portfolio) 1회 호출.
- [AUTOFOLIO_LangGraph_설계.md](AUTOFOLIO_LangGraph_설계.md) §2 참고.

---

## 4. 문서 관계

- 수정 방향·판단: [AUTOFOLIO_API_명세_수정방향_정리.md](AUTOFOLIO_API_명세_수정방향_정리.md)
- 채용 공고 추출 상세: [AUTOFOLIO_채용공고파싱전략.md](AUTOFOLIO_채용공고파싱전략.md)
- 그래프·전략·Writer/Inspector: [AUTOFOLIO_LangGraph_설계.md](AUTOFOLIO_LangGraph_설계.md)
- OAuth: [AUTOFOLIO_GitHub_OAuth_가이드.md](AUTOFOLIO_GitHub_OAuth_가이드.md)

---

## 5. 문서 이력

- 1.0 (2026-03-04): 초안. 수정 방향 반영한 API 명세서 정리.

