## Week2 - GitHub OAuth·포트폴리오 API 설계

**주차 목표**
- GitHub 관련 API 명세서 초안 작성.
- 레포·커밋·코드 접근·임베딩이 가능한지 로컬 실험으로 검증.

---

###  한 것

| 항목 | 내용 |
|------|------|
| 브랜치 | `feature/week2-github-api-spec` 생성 |
| API 명세서 | `docs/API_GitHub_Portfolio_Spec.md` — Week2 기준 GitHub OAuth·레포/커밋/파일·임베딩 API 초안 정리 |
| GitHub 전용 명세 | `docs/API_GitHub_Spec.md` — GitHub 레포 목록/선택, 파일·콘텐츠, 커밋(author 필터·집계), 임베딩 생성/저장까지 **요청 파라미터 + 응답 스키마 + 예시 JSON** 완성 |
| 서비스 API 명세 | `docs/API_Service_Spec.md` — 채용공고 파싱, Job Fit, 자소서 Draft/Inspect, 포트폴리오 generate/get, 합격 자소서 검색(내부 모듈) 명세 정리 |
| 전체 요약 명세 | `docs/API_Full_Spec.md` — GitHub + 서비스 API를 한 테이블과 요약 섹션으로 묶은 통합 명세서 |
| 서비스 유틸 | `src/github_embedding/login/` OAuth·레포·커밋·트리 조회, `embedding/` 스켈레톤 |
| 로컬 실험 | Week1 복기 + `github_code_and_commits_experiment.py` — 루트 목록, 문서/코드 파일 읽기, 타인 레포에서 `author=본인` 커밋만 조회 검증 |

**로컬 실습 스크립트:** `github_oauth_local_test.py`(OAuth 플로우), `github_repo_describe_practice.py`(레포+LLM 설명), `github_code_and_commits_experiment.py`(파일 목록·코드 읽기·내 커밋만).  
실행: `GITHUB_OAUTH_ACCESS_TOKEN` 설정 후 `poetry run python scripts/...`

---

### 앞으로 할 것

- [ ] FastAPI 라우터 구현 (명세서 기준)
- [ ] github_embedding × LangGraph 연계, 인증/세션(DB·토큰) 문서화

---

**레퍼런스:** `week1-github-oauth.md`, `docs/API_GitHub_Portfolio_Spec.md`, `docs/AUTOFOLIO_GitHub_OAuth_가이드.md`, `AUTOFOLIO_LangGraph_설계.md`

---

### 레포 코드 인식 전략(Contents API vs 클론) 실험 메모

- 실험 스크립트: `scripts/repo_ingestion_strategy_experiment.py`
- 실행: `GITHUB_OAUTH_ACCESS_TOKEN` 설정 후  
  `poetry run python scripts/repo_ingestion_strategy_experiment.py`
- 실행 시 AutoPolio 가상환경 활성화 필요: `cd AutoPolio && source .venv/bin/activate` 또는 `poetry shell`

**실험 설정**

- 대상 레포: `kocory1/AutoPolio` (기본 브랜치)
- 타깃 파일 확장자: `('.py', '.js', '.ts', '.tsx', '.java', '.go', '.rs', '.md')`

**Contents API 전략 결과**

- 소요 시간: **약 25.94초**
- 읽은 파일 수: **52개**
- 총 바이트 수: **184,319 bytes**
- HTTP 요청 수(대략): **69회**
- 특징: 레포를 클론하지 않고도 바로 파일 내용을 읽을 수 있지만, 디렉터리 재귀 + 파일 raw 요청으로 인해 요청 수/레이턴시가 커지고, 레포가 커질수록 rate-limit에 더 민감해진다.

**git clone 전략 결과**

- 소요 시간: **약 2.01초**
- 읽은 파일 수: **52개** (Contents API와 동일)
- 총 바이트 수: **184,319 bytes** (Contents API와 동일)
- HTTP 요청 수(대략): **1회** (초기 `git clone --depth 1` 기준)
- 특징: 초기 클론 비용만 지불하면, 이후에는 로컬 파일시스템에서 빠르게 여러 번 읽고 가공할 수 있어 임베딩/색인 파이프라인에 유리하다.

**AutoFolio에서의 선택**

- AutoFolio의 “레포 코드 인식 + 임베딩/색인” 요구사항 기준으로,
  - **기본 전략**은 `git clone (--depth 1)` 후 로컬 파일을 순회하며 인덱싱하는 방식으로 선택한다.
  - Contents API는 (1) 클론 권한이 없거나 (2) 특정 파일만 on-demand로 읽고 싶을 때 보조적으로 사용한다.
- 초기 ingest, 재인덱싱, 여러 번의 실험/임베딩을 고려했을 때, git clone 기반 전략이 시간/요청 수/개발자 경험 측면에서 더 안정적인 베이스라인이라고 판단했다.
