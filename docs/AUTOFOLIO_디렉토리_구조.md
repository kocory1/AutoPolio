# Autofolio 디렉토리 구조

**문서 버전:** 1.0  
**기준:** `main` 브랜치 코드베이스, LangGraph·RAG·API 설계 문서

---

## 1. 루트

- `README.md`: 프로젝트 개요, 실행 방법
- `pyproject.toml`, `poetry.lock`: Python 패키지/빌드 설정
- `docs/`: 설계·스펙·기획 문서
- `src/`: 서비스 코드 (FastAPI, LangGraph, 서비스 로직)
- `scripts/`: 실험·유틸 스크립트
- `week-issues/`: 주차별 이슈·노트
- `data/`: 샘플 데이터·실험용 데이터

---

## 2. src/ (코드)

### 2.1 app (엔트리·앱 설정)

- `src/app/main.py`
  - FastAPI 앱 엔트리포인트
  - 라우터 등록, 미들웨어 설정
- `src/app/__init__.py`
  - `from .main import app` 등 패키지 초기화

### 2.2 api (Controller 레이어)

HTTP 엔드포인트를 정의하는 레이어. 비즈니스 로직은 service/graphs에 위임.

- `src/api/auth.py`: GitHub 로그인/로그아웃
- `src/api/github.py`: 레포/트리/커밋/임베딩 API
- `src/api/jobs.py`: 채용공고 파싱, Job Fit
- `src/api/cover_letter.py`: `/api/cover-letter/draft`, `/api/cover-letter/inspect`
- `src/api/portfolio.py`: `/api/portfolio/generate`, `/api/portfolio`

### 2.3 graphs (LangGraph 오케스트레이션)

LangGraph 그래프 정의. Writer/Inspector/Portfolio 플로우를 관리하는 오케스트레이터.

- `src/graphs/portfolio_graph/`: 포트폴리오 생성 그래프
- `src/graphs/writer_graph/`: Writer 그래프 (초안 생성)
- `src/graphs/inspector_graph/`: Inspector 그래프 (첨삭, Human-in-the-loop)

각 그래프 디렉토리 공통 구성:

- `state.py`: Graph State 정의 (TypedDict 등)
- `node.py`: 노드 함수
- `edge.py`: 엣지/조건 분기
- `graph.py`: 그래프 빌더 (`build_*_graph()`)

### 2.4 service (도메인 서비스·RAG·외부 연동)

비즈니스 로직과 외부 연동을 담당하는 레이어.

예상 구조:

- `src/service/rag/`
  - `user_assets.py`: `retrieve_user_assets`, `get_user_profile_summary`
  - `passed_samples.py`: 합격 자소서 검색
- `src/service/github/`
  - `oauth.py`: GitHub OAuth 유틸
  - `api_client.py`: 레포/트리/커밋/contents 조회
- `src/service/jobs/`
  - `parse.py`: 채용공고 파싱
  - `fit.py`: Job Fit 계산
- `src/service/cover_letter/`
  - `evaluator.py`: self_consistency, Inspector 분석 로직

### 2.5 db (영속 계층)

SQLite 기반 DB 모델·세션.

- `src/db/models.py`
  - `users`, `cover_letters`, `jobs`, `selected_repos`, `asset_hierarchy`, `portfolios` 등
  - [AUTOFOLIO_DB_스키마_설계.md](AUTOFOLIO_DB_스키마_설계.md) 기준
- `src/db/session.py`: 엔진/세션 팩토리
- (선택) `src/db/repositories/`: 테이블별 쿼리 모음

### 2.6 utils (공통 유틸)

- `src/utils/visualize.py`: 그래프/구조 시각화 유틸
- 기타 공통 헬퍼·로깅 등

## 3. 향후 추가 예정

- `streamlit_app/`: Streamlit 기반 FE (포트폴리오·자소서 UI)
- `src/service/`* 세분화 및 구현 진행에 따른 디렉토리 보완

