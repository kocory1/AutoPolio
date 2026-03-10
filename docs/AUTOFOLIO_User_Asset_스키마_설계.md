# User Asset 스키마 설계 제안

**문서 버전:** 1.3  
**기준:** [AUTOFOLIO_임베딩전략.md](AUTOFOLIO_임베딩전략.md), [AUTOFOLIO_DB_스키마_설계.md](AUTOFOLIO_DB_스키마_설계.md), [AUTOFOLIO_RAG_파이프라인_핵심.md](AUTOFOLIO_RAG_파이프라인_핵심.md), [AUTOFOLIO_Writer_그래프_파이프라인_제안.md](AUTOFOLIO_Writer_그래프_파이프라인_제안.md), [AUTOFOLIO_Inspector_그래프_파이프라인_제안.md](AUTOFOLIO_Inspector_그래프_파이프라인_제안.md), [API_GitHub_Portfolio_Spec.md](API_GitHub_Portfolio_Spec.md)

---

## 1. 개요

User Asset은 **유저의 GitHub 코드·커밋 + 이력서/포트폴리오 문서**를 RAPTOR 임베딩으로 저장하고, Writer·Inspector·Job Fit·포트폴리오 그래프에서 조회하는 데이터다.

| 저장소 | 용도 |
|--------|------|
| **ChromaDB** | RAPTOR 임베딩 (파일/폴더 청크). **컬렉션 키 = user_id** |
| **SQLite** | portfolios 메타데이터 (user_id FK). 에셋 메타는 VectorDB 메타데이터로 충분 |

---

## 2. ChromaDB — User Asset VectorDB

### 2.1 컬렉션 구조

**컬렉션 키:** `user_id` 그대로 사용

| 방식 | 설명 | 권장 |
|------|------|------|
| **A. 유저별 컬렉션** | `user_assets_{user_id}` 또는 `user_id`를 컬렉션명으로 | ✅ 단순, 유저별 격리, 삭제 용이 |
| **B. 단일 컬렉션 + 메타 필터** | `user_assets` 하나, `user_id` 메타데이터로 필터 | 대량 유저 시 관리 단순 |

**권장:** A. 유저별 컬렉션. `user_id`를 그대로 컬렉션명으로 사용 (ChromaDB 컬렉션명 제약 있으면 `user_assets_{user_id}`).

---

### 2.2 타입·출처 (통일 스키마)

모든 청크는 **동일 스키마**로 관리. `type`과 `source`로 구분.

| type | 의미 | source | 비고 |
|------|------|--------|------|
| **code** | 소스 코드 파일 (leaf) | github | 본인 커밋만 인덱싱 |
| **folder** | 폴더 요약 (mid) | github | RAPTOR bottom-up |
| **project** | 프로젝트 루트 요약 (root) | github | 레포 전체 요약만 |
| **document** | 이력서/포트폴리오 청크 | resume, portfolio | 전체 요약 없음, 청크만 |

- **code**: 본인 커밋에 포함된 파일만 임베딩. `author=본인` 필터 적용.
- **project**: GitHub 레포 루트만. 이력서/포트폴리오 전체 요약은 MVP 범위 외.

---

### 2.3 ChromaDB 문서 스키마 (실제 저장 형식)

ChromaDB는 `id`, `document`, `metadata`, `embedding` 구조를 사용한다.

| ChromaDB 필드 | 매핑 | 설명 |
|---------------|------|------|
| `id` | 청크 `id` | `{repo}/{path}` 또는 `{source}_{doc_id}_{chunk_idx}` |
| `document` | §2.4 임베딩 대상 | type별 summary 우선 또는 content. 검색·임베딩에 사용 |
| `metadata` | `type`, `source`, `repo`, `path` (MVP 4개만) | 필터·반환용 |
| `embedding` | list[float] | 벡터 |

**metadata (MVP 필수 4개):**

| 키 | 타입 | 설명 | code | folder | project | document |
|----|------|------|------|--------|---------|----------|
| `type` | str | `code` \| `folder` \| `project` \| `document` | ✓ | ✓ | ✓ | ✓ |
| `source` | str | `github` \| `resume` \| `portfolio` | ✓ | ✓ | ✓ | ✓ |
| `repo` | str | `owner/repo`. document는 `null` | ✓ | ✓ | ✓ | null |
| `path` | str | 파일/폴더 경로 또는 문서·청크 식별자 | ✓ | ✓ | ✓ | ✓ |

**id·path 예시:**

| type | id 예시 | path 예시 |
|------|---------|-----------|
| code | `owner/repo/src/auth/login.py` | `src/auth/login.py` |
| folder | `owner/repo/src/auth` | `src/auth` |
| project | `owner/repo/` | `"/"` |
| document | `resume_uuid_0` | `resume_uuid_0`, `portfolio_abc_2` |

---

### 2.4 임베딩 대상 (무엇을 embed할지)

각 type별로 **임베딩에 사용할 텍스트**를 명시. ChromaDB `document` 필드에 저장 후 `embed(document)` 수행.

| type | 임베딩 대상 | 우선순위 | 비고 |
|------|-------------|----------|------|
| **code** | `summary` 우선, 없으면 `content` | summary > content | summary: LLM 요약. content: 원본 코드 (토큰 제한 시 truncate). [임베딩전략](AUTOFOLIO_임베딩전략.md) §5 |
| **folder** | `summary` | 필수 | LLM 폴더 요약. content 없음. |
| **project** | `summary` | 필수 | 레포 루트 LLM 요약. |
| **document** | `summary` 우선, 없으면 `content` | summary > content | summary: LLM 요약. content: OCR 원문. |

**code 선택 기준:**
- **summary 우선:** 의미 공간에서 검색 품질 좋음. "인증 처리" 쿼리 → 요약된 문장과 매칭.
- **content fallback:** 요약 생성 실패·비용 절감 시 원본 코드 임베딩. 토큰 초과 시 앞부분 truncate.

---

### 2.5 검색 활용 시나리오

[AUTOFOLIO_임베딩전략.md](AUTOFOLIO_임베딩전략.md) §7 정리:

| 시나리오 | type | 호출 주체 | 예시 |
|----------|------|-----------|------|
| **JD 키워드 매칭** | folder, project | Job Fit | "인증 시스템 경험" → auth 폴더 요약 |
| **STAR 에셋 생성** | folder | 포트폴리오 그래프 | "결제 모듈에서 한 일" → payment 폴더 |
| **Writer 에셋 조회** | 전체 | Writer load_assets | 문항 + job_parsed → 관련 청크 검색 |
| **Inspector 증거 찾기** | code | Inspector load_draft | "동시성 처리 코드" → pg.py |
| **프로젝트 개요** | project | Job Fit, 포트폴리오 | 루트 요약 |

---

## 3. 조회 인터페이스 (제안)

Writer·Inspector `load_assets`에서 사용할 모듈 시그니처:

```python
def retrieve_user_assets(
    user_id: str,
    query: str | None = None,
    job_parsed: dict | None = None,
    source_filter: list[str] | None = None,  # ["github", "resume", "portfolio"]
    type_filter: list[str] | None = None,   # ["code", "folder", "project", "document"]
    top_k: int = 10,
) -> list[dict]:
    """
    user_id로 컬렉션 조회.
    query 있으면 semantic search. 없으면 job_parsed 기반 쿼리 생성 또는 전체 상위.
    반환: [{id, document, metadata, ...}, ...]
    """
```

**Job Fit용:**

```python
def get_user_profile_summary(user_id: str) -> dict | None:
    """
    루트 요약·폴더 요약 등 프로필 수준 데이터 반환.
    공고 파싱 결과와 비교해 점수 산출.
    """
```

---

## 4. 인덱싱 흐름

| 소스 | 트리거 | 처리 |
|------|--------|------|
| **GitHub** | `POST /api/github/repos/{id}/embedding` | 트리 수집 → Noise Filtering → **본인 커밋 파일만** code 임베딩 → folder/project Bottom-up 요약·임베딩 → ChromaDB upsert |
| **이력서/포트폴리오** | `POST /api/user/documents` | PDF·PPT 업로드 → OCR·전처리 → 청크 분할 → document 임베딩 → ChromaDB upsert (전체 요약 없음) |

---

## 5. SQLite와의 관계

- **portfolios** 테이블: 포트폴리오 메타데이터 (이름, 설명, content). 에셋 내용은 VectorDB에만 저장.
- **selected_repos**: 임베딩 대상 레포 목록. `repo_full_name`(owner/repo)으로 레포 구분. VectorDB 인덱싱 시 참조.

---

## 6. ER 다이어그램 (개념)

```
users (id)
  │
  ├── selected_repos → GitHub 레포 목록 (임베딩 대상)
  ├── portfolios → 포트폴리오 메타
  │
  └── ChromaDB: user_assets_{user_id}
        ├── code (GitHub 소스, 본인 커밋만)
        ├── folder (GitHub 폴더 요약)
        ├── project (GitHub 레포 루트 요약)
        └── document (이력서/포트폴리오 청크)
```

**통합 스키마:** [AUTOFOLIO_DB_스키마_설계.md](AUTOFOLIO_DB_스키마_설계.md) §4

---

## 7. 문서 관계

- DB 스키마 전체: [AUTOFOLIO_DB_스키마_설계.md](AUTOFOLIO_DB_스키마_설계.md)
- RAPTOR·임베딩 상세: [AUTOFOLIO_임베딩전략.md](AUTOFOLIO_임베딩전략.md)
- Writer/Inspector 에셋 조회: [AUTOFOLIO_Writer_그래프_파이프라인_제안.md](AUTOFOLIO_Writer_그래프_파이프라인_제안.md) §4.2, [AUTOFOLIO_Inspector_그래프_파이프라인_제안.md](AUTOFOLIO_Inspector_그래프_파이프라인_제안.md) §4.1
- API: [AUTOFOLIO_API_스펙.md](AUTOFOLIO_API_스펙.md), [API_GitHub_Portfolio_Spec.md](API_GitHub_Portfolio_Spec.md)

---

## 8. 문서 이력

- 1.0: User Asset 스키마 설계 제안 초안. ChromaDB 컬렉션 키=user_id, RAPTOR 청크(file/folder/document), 조회 인터페이스, 인덱싱 흐름 정리.
- 1.1: 통일 스키마. type=code|folder|project|document, source=github|resume|portfolio. metadata MVP 4개(type, source, repo, path). code=본인 커밋만. 이력서/포트폴리오 전체 요약 없음.
- 1.2: §2.4 임베딩 대상 상세화. code/document는 summary 우선·content fallback. 선택 기준 명시.
- 1.3: user_selected_repos→selected_repos. DB 스키마 설계와 통합, §6 ER 다이어그램 업데이트.
