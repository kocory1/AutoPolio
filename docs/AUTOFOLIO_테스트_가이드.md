# Autofolio 테스트 가이드

**문서 버전:** 1.0  
**기준:** [AUTOFOLIO_디렉토리_구조.md](AUTOFOLIO_디렉토리_구조.md), [AUTOFOLIO_LangGraph_설계.md](AUTOFOLIO_LangGraph_설계.md)

---

## 1. 개요

Autofolio 백엔드 테스트는 `pytest`를 기준으로 운영한다.  
모든 테스트 실행은 Poetry 가상환경에서 `poetry run`으로 수행한다.

---

## 2. 실행 방법

### 2.1 전체 테스트

```bash
poetry run pytest -q
```

### 2.2 특정 파일 테스트

```bash
poetry run pytest tests/graphs/portfolio_graph/test_load_profile.py -q
```

### 2.3 상세 출력(디버깅)

```bash
poetry run pytest -vv
```

---

## 3. 테스트 디렉토리 규칙

### 3.1 경로

| 대상 코드 | 테스트 경로 |
|-----------|-------------|
| `src/graphs/portfolio_graph/*` | `tests/graphs/portfolio_graph/test_*.py` |
| `src/graphs/writer_graph/*` | `tests/graphs/writer_graph/test_*.py` |
| `src/graphs/inspector_graph/*` | `tests/graphs/inspector_graph/test_*.py` |
| `src/service/*` | `tests/service/*/test_*.py` |

### 3.2 파일명

- 테스트 파일명은 `test_*.py` 형식 사용
- 테스트 함수명은 `test_*` 형식 사용

---

## 4. 작성 원칙 (TDD)

### 4.1 기본 순서

1. 실패하는 테스트(RED) 작성
2. 최소 구현으로 통과(GREEN)
3. 리팩토링(REFACTOR)

### 4.2 단위 테스트 우선

- 그래프 노드 테스트는 외부 의존성(DB, VectorDB, LLM)을 mock/stub 처리
- 노드는 입력 state 대비 출력 state 계약을 검증
- 실패 케이스는 `error` 필드로 상태 기반 검증

### 4.3 실행 규칙

- 로컬 실행/CI 모두 `poetry run pytest` 기준으로 통일
- `python -m unittest`는 신규 테스트에 사용하지 않음

---

## 5. 문서 관계

- 디렉토리 구조: [AUTOFOLIO_디렉토리_구조.md](AUTOFOLIO_디렉토리_구조.md)
- 그래프 설계: [AUTOFOLIO_LangGraph_설계.md](AUTOFOLIO_LangGraph_설계.md)

---

## 6. 문서 이력

- 1.0: 초안. pytest/poetry 기준 실행 방식, 테스트 경로 규칙, TDD 원칙 정리.

