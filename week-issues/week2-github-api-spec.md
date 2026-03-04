## Week2 - GitHub OAuth·포트폴리오 API 설계

**주차 목표**
- GitHub 관련 API 명세서 초안 작성.
- 레포·커밋·코드 접근·임베딩이 가능한지 로컬 실험으로 검증.

---

###  한 것

| 항목 | 내용 |
|------|------|
| 브랜치 | `feature/week2-github-api-spec` 생성 |
| API 명세서 | `docs/API_GitHub_Portfolio_Spec.md` — 인증(login, callback, logout, disconnect), 유저(/api/me, 선택 레포), GitHub(레포 목록·상세, 파일 트리·**파일 raw**, 커밋, 임베딩) 전부 명세 |
| 서비스 유틸 | `src/github_embedding/login/` OAuth·레포·커밋·트리 조회, `embedding/` 스켈레톤 |
| 로컬 실험 | Week1 복기 + `github_code_and_commits_experiment.py` — 루트 목록, 문서/코드 파일 읽기, 타인 레포에서 `author=본인` 커밋만 조회 검증 |

**로컬 실습 스크립트:** `github_oauth_local_test.py`(OAuth 플로우), `github_repo_describe_practice.py`(레포+LLM 설명), `github_code_and_commits_experiment.py`(파일 목록·코드 읽기·내 커밋만).  
실행: `GITHUB_OAUTH_ACCESS_TOKEN` 설정 후 `poetry run python scripts/...`

---

### 앞으로 할 것

- [ ] FastAPI 라우터 구현 (명세서 기준)
- [ ] 타인 레포 “내 커밋만” 실험 결과 1~2문단 정리
- [ ] 레포 코드 인식 전략(Contents API vs 클론) 정리
- [ ] github_embedding × LangGraph 연계, 인증/세션(DB·토큰) 문서화

---

**레퍼런스:** `week1-github-oauth.md`, `docs/API_GitHub_Portfolio_Spec.md`, `docs/AUTOFOLIO_GitHub_OAuth_가이드.md`, `AUTOFOLIO_LangGraph_설계.md`

---

### 레포 코드 인식 전략(Contents API vs 클론) 실험 메모

- 실험 스크립트: `scripts/repo_ingestion_strategy_experiment.py`
- 실행: `GITHUB_OAUTH_ACCESS_TOKEN` 설정 후  
  `poetry run python scripts/repo_ingestion_strategy_experiment.py`
- 실행 시 AutoPolio 가상환경 활성화 필요: `cd AutoPolio && source .venv/bin/activate` 또는 `poetry shell`

**기록 가이드 (실행 후 여기에 메모)**

- [ ] 대상 레포, 브랜치, 파일 확장자 범위
- [ ] Contents API 전략 결과: 대략적인 시간 / 파일 수 / 바이트 수 / rate-limit 체감
- [ ] git clone 전략 결과: 대략적인 시간 / 파일 수 / 바이트 수 / 로컬 후처리 편의성
- [ ] AutoFolio에서 **최종 선택한 전략**과 이유 (예: “초기 ingest 시에는 git clone, 이후 증분 동기화는 Contents API” 등)
