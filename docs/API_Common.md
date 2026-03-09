## 1. 문서 개요

Autofolio API 전체에서 공통으로 사용하는 **요청 형식, 에러 응답 규칙, score_label 기준, 대표 사용 시퀀스**를 정리한 문서이다.  
각 API 명세서에서 공통 에러/규칙이 언급될 때는 이 문서를 참고한다.

---

## 2. 공통 요청 형식

- **Content-Type:** 기본은 `application/json`  
  - 파일 업로드 엔드포인트의 경우 `multipart/form-data` 를 사용하며, 해당 엔드포인트에서 별도로 명시한다.
- **인증 방식:** 세션 쿠키 또는 `Authorization: Bearer <app-session-token>`

### 2.1 HTTP 상태코드 의미

| 상태코드 범위 | 의미 |
|-------------|------|
| 200번대 | 성공 |
| 302 | 리다이렉트 |
| 400번대 | 클라이언트 오류 |
| 500번대 | 서버 오류 |

---

## 3. 공통 에러 응답 형식

- **에러 JSON 포맷:**

```json
{
  "error": "ERROR_CODE",
  "message": "사람이 읽을 수 있는 에러 설명"
}
```

---

## 4. 공통 에러 코드표

| HTTP 상태코드 | error | 발생조건 |
|--------------|-------|----------|
| 400 | BAD_REQUEST | 요청 파라미터 누락 또는 형식 오류 |
| 401 | UNAUTHORIZED | 세션 없음 또는 만료 |
| 403 | FORBIDDEN | 접근 권한 없음 |
| 404 | NOT_FOUND | 요청한 리소스 없음 |
| 500 | INTERNAL_SERVER_ERROR | 서버 내부 오류 |
| 502 | GITHUB_UPSTREAM_ERROR | GitHub API 호출 실패 (GitHub 연동 API에만 해당) |

---

## 5. score_label 기준표

Autofolio에서 Job Fit 점수 및 자소서/포트폴리오 관련 점수의 등급을 표기할 때 사용하는 공통 기준이다.

| score 범위 | score_label | 의미 |
|-----------|-------------|------|
| 0.8 이상 | HIGH | 높은 적합도 |
| 0.6 이상 0.8 미만 | GOOD | 보통 적합도 |
| 0.6 미만 | LOW | 낮은 적합도 |

---

## 6. API 사용 시퀀스

Autofolio에서 일반적으로 사용하는 **엔드투엔드 API 호출 흐름**은 다음과 같다.

1. GET /api/auth/github/login — GitHub 로그인 시작 (Auth)
2. GET /api/auth/github/callback — 세션 발급 완료 (Auth)
3. GET /api/me — 유저 정보 확인 (Auth)
4. GET /api/github/repos — 레포 목록 조회 (GitHub)
5. PUT /api/user/selected-repos — 레포 선택 저장 (GitHub)
6. POST /api/user/documents — 이력서/포트폴리오 업로드 (Service, 선택)
7. POST /api/github/repos/{id}/embedding — 임베딩 생성 (GitHub)
8. GET /api/github/repos/{id}/embedding/status — 임베딩 완료 확인 (GitHub)
9. POST /api/jobs/parse — 채용공고 파싱 (Service)
10. POST /api/job-fit — 적합도 점수 확인 (Service)
11. POST /api/cover-letter/draft — 자소서 초안 생성 (Service)
12. POST /api/cover-letter/inspect — 자소서 검수 (Service)
13. POST /api/portfolio/generate — 포트폴리오 생성 (Service)

6번(문서 업로드)은 선택 단계이며, 이력서/포트폴리오 문서가 없어도 자소서·포트폴리오 생성은 GitHub 임베딩만으로 진행 가능하다.

