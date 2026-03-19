# GitHub 임베딩 구현 계획

**문서 버전:** 2.2  
**기준:** [AUTOFOLIO_임베딩전략.md](AUTOFOLIO_임베딩전략.md), [AUTOFOLIO_User_Asset_스키마_설계.md](AUTOFOLIO_User_Asset_스키마_설계.md), [AUTOFOLIO_DB_스키마_설계.md](AUTOFOLIO_DB_스키마_설계.md), [API_GitHub_Spec.md](API_GitHub_Spec.md), [week3-oauth-repo-list.md](../week-issues/week3-oauth-repo-list.md) § asset_hierarchy path 설계 근거

---

## 1. 목표

- **트리거:** `POST /api/github/repos/{repo_id}/embedding` 호출 시, 해당 레포의 코드·폴더·프로젝트 청크를 RAPTOR 방식으로 생성해 ChromaDB `user_assets_{user_id}`에 저장.
- **제약:** 레포는 해당 유저의 `selected_repos`에 등록된 경우에만 임베딩 허용. 미등록 시 403.
- **결과:** 포트폴리오 그래프의 `retrieve_user_assets(source_filter=["github"])`로 GitHub 청크 조회 가능.

---

## 2. 기준 문서 요약

### 2.1 asset_hierarchy (SQLite)

- **컬럼:** `id`(PK), `selected_repo_id`(FK), `type` 만 존재. path 전용 컬럼 없음.
- **id:** 경로 자체를 id로 사용. 예: `owner/repo/src/auth/login.py`. ChromaDB document id와 동일.  
  GitHub Contents API에 쓸 path는 id에서 `owner/repo/`(또는 `owner/repo`) 제거해 유도.
- **채우는 시점:** 임베딩 시 해당 `selected_repo_id` 행 전부 삭제 후 재생성.

### 2.2 ChromaDB User Asset

- **컬렉션:** `user_assets_{user_id}`.
- **문서 필드:** `id`, `document`, `metadata`, `embedding`.
- **metadata (MVP 4개):** `type`, `source`, `repo`, `path`.  
  path = 레포 내 경로 (예: `src/auth/login.py`, `src/auth`, `"/"`).
- **id:** `owner/repo/` + path 형태. code: `owner/repo/src/auth/login.py`, folder: `owner/repo/src/auth`, project: `owner/repo/`.

### 2.3 임베딩 전략 (RAPTOR)

- 트리 수집 → 노이즈 필터 → code(본인 커밋만 문서상 정의, MVP에서 생략 가능) → folder bottom-up 요약 → project 루트 요약.
- code: document = summary 우선, 없으면 content(truncate).  
  folder/project: document = LLM 요약.

### 2.4 API (POST embedding)

- **Request:** paths(필수), branch, strategy, force_refresh.  
  paths 규칙: `"/"` = 레포 전체, `"src/"` = 해당 폴더 하위 재귀, `"src/main.py"` = 해당 파일만.
- **Response:** status, embedding(chunks_indexed, dimensions, total_tokens, storage), hierarchy_nodes_created.
- **전제:** selected_repos에 해당 repo 없으면 403.
- **저장소 표현:** 실제 저장은 ChromaDB 컬렉션 `user_assets_{user_id}` 하나뿐이며, `metadata.repo`로 레포 구분. API 응답의 `embedding.storage.index_name`(예: `autofolio_github_repo_123_main`)은 레포·브랜치 식별용 **논리 이름**이며, ChromaDB 컬렉션명과는 다름.

---

## 3. 구현 단계 (Phase)

### Phase 1: 인증·권한·인프라

| 순서 | 작업 | 설명 |
|------|------|------|
| 1.1 | 유저·레포 검증 | 인증된 user_id로 `get_selected_repos(user_id)` 호출. repo_id(또는 owner/name)가 반환 목록에 없으면 403. |
| 1.2 | 임베딩 클라이언트 | 텍스트 리스트 → 벡터 리스트. 문서/기존 코드와 동일 차원(예: 1536) 사용. |
| 1.3 | ChromaDB upsert | `user_assets_{user_id}` 컬렉션에 id/document/metadata/embedding 추가. 동일 id는 덮어쓰기(upsert). |

**산출물:** selected_repos 검증 로직, embed 함수/클래스, ChromaDB add(upsert) 호출 래퍼.

---

### Phase 2: 트리 수집·노이즈 필터

| 순서 | 작업 | 설명 |
|------|------|------|
| 2.1 | 트리 수집 | GitHub `GET /repos/{owner}/{repo}/git/trees/{tree_sha}?recursive=1`. ref = branch 또는 default_branch. |
| 2.2 | paths 확장 | API paths 규칙 적용: `"/"` → 전체 blob 경로, `"src/"` → 해당 prefix blob 경로, 단일 파일 → 해당 path만. |
| 2.3 | 노이즈 필터 | 제외: node_modules/, .git/, __pycache__, *.lock 등. 포함: 소스 확장자, README 등. (임베딩전략 §4) |

**산출물:** 트리 조회 함수, paths → 대상 blob path 목록 변환, 필터 적용 후 최종 path 목록.

---

### Phase 3: 파일 내용 조회

| 순서 | 작업 | 설명 |
|------|------|------|
| 3.1 | 파일 내용 조회 | 각 path에 대해 `GET /repos/{owner}/{repo}/contents/{path}?ref=...` (raw). 또는 clone 기반이면 로컬에서 읽기. |
| 3.2 | 길이 제한 | 단일 파일이 너무 크면 앞부분 truncate. (User_Asset §2.4 content fallback 시 truncate) |

**산출물:** path → content 매핑. (본인 커밋만 필터는 문서에 있으나 MVP에서 생략 가능.)

---

### Phase 4: code 청크 생성·임베딩

| 순서 | 작업 | 설명 |
|------|------|------|
| 4.1 | 청크 구조 | id = `{repo_full_name}/{path}` (path가 루트 파일이면 `owner/repo/README.md` 등). document = content(truncate) 또는 추후 summary. metadata = type=code, source=github, repo=repo_full_name, path=레포 내 path. |
| 4.2 | 임베딩 벡터 생성 | document 리스트 embed → 청크별 id, document, metadata, embedding 벡터를 메모리상 리스트로 확보. **ChromaDB 반영은 하지 않음.** 실제 DB 반영은 Phase 6.1(삭제) 이후 6.2(일괄 add)에서만 수행. |

**산출물:** code 청크 리스트(id, document, metadata, embedding 포함). ChromaDB 쓰기는 Phase 6에서만.

---

### Phase 5: folder / project (RAPTOR Bottom-up)

| 순서 | 작업 | 설명 |
|------|------|------|
| 5.1 | 폴더 경로 유도 | code path 목록에서 디렉터리 경로 추출. 예: `src/auth/login.py` → `src/`, `src/auth/`. |
| 5.2 | folder 청크 | 각 폴더별 하위 code document(또는 요약)를 모아 LLM으로 폴더 요약 생성. id = `owner/repo/src/auth`, document = 요약, metadata path = `src/auth`. |
| 5.3 | project 청크 | 루트 하위 folder 요약을 모아 LLM으로 프로젝트 요약. id = `owner/repo/`, path = `"/"`. |
| 5.4 | 임베딩 벡터 생성 | folder/project document → embed → 청크별 id, document, metadata, embedding을 메모리상 리스트로 확보. **ChromaDB 반영은 하지 않음.** 실제 DB 반영은 Phase 6.2(일괄 add)에서만 수행. |

**산출물:** folder/project 청크 리스트(id, document, metadata, embedding 포함). ChromaDB 쓰기는 Phase 6에서만. (MVP에서 code만 먼저 하고 5는 후순위 가능.)

---

### Phase 6: ChromaDB·asset_hierarchy 정리

**실행 순서:** 4·5에서는 청크 리스트와 임베딩 벡터만 생성하고 DB에는 쓰지 않는다. ChromaDB 반영은 여기서만 수행: **6.1(삭제) → 6.2(일괄 add)**.

| 순서 | 작업 | 설명 |
|------|------|------|
| 6.1 | 해당 repo 기존 청크 삭제 | ChromaDB `user_assets_{user_id}`에서 해당 repo 청크만 삭제. id prefix가 `{repo_full_name}/` 인 항목 삭제 또는 metadata.repo 필터 후 삭제. |
| 6.2 | 새 청크 일괄 add | Phase 4·5에서 만든 청크 리스트(id, document, metadata, embedding)를 ChromaDB에 일괄 add. |
| 6.3 | asset_hierarchy 재생성 | 해당 `selected_repo_id`에 대한 기존 행 전부 삭제. 각 청크마다 (id, selected_repo_id, type) insert. parent_id·path 컬럼 없음. |

**산출물:** repo 단위 ChromaDB 삭제+add, asset_hierarchy 삭제 후 (id, selected_repo_id, type) insert.

---

### Phase 7: API

| 순서 | 작업 | 설명 |
|------|------|------|
| 7.1 | POST /api/github/repos/{repo_id}/embedding | 인증 → Phase 1.1 검증 → 2~6 순서 실행 → 200 + status, embedding(chunks_indexed, dimensions, total_tokens, storage), hierarchy_nodes_created. |
| 7.2 | 에러 매핑 | 400(paths 비어 있음 등), 401, 403(레포 미선택), 404, 409(진행 중), 502. API_GitHub_Spec §5 준수. |

**산출물:** 라우터, main에 등록. (GET embedding/status는 API 명세에서 삭제됨·구현하지 않음.)

---

## 4. id·path 규칙 정리

- **ChromaDB id:** `owner/repo` + `/` + 레포 내 path.  
  - code: `owner/repo/src/auth/login.py`  
  - folder: `owner/repo/src/auth`  
  - project: `owner/repo/` (path는 metadata에 `"/"`)
- **ChromaDB metadata.path:** 레포 내 경로만. `src/auth/login.py`, `src/auth`, `"/"`.
- **asset_hierarchy.id:** ChromaDB id와 동일. path 컬럼 없으므로 Contents API용 path는 id에서 `owner/repo/` 제거해 유도.

---

## 5. 디렉터리·파일 배치 제안

```
src/
├── api/
│   └── github.py                 # POST embedding
├── service/
│   ├── github/
│   │   ├── tree.py               # 트리 수집 (Trees API)
│   │   ├── filter.py             # paths 확장 + 노이즈 필터
│   │   ├── contents.py           # 파일 내용 조회
│   │   └── embedding.py          # orchestration: 2~6 호출
│   └── rag/
│       └── user_assets.py        # 기존 retrieve_user_assets
├── db/
│   └── vector/
│       ├── chroma.py             # 기존
│       └── (embedding 호출)      # embed 함수 위치
```

---

## 6. MVP 범위

| 포함 | 제외(후순위) |
|------|----------------|
| selected_repos 검증, Trees API 트리 수집, paths 확장, 노이즈 필터 | 본인 커밋만 필터 |
| code 청크만: content(truncate) → embed → ChromaDB | folder/project LLM 요약 |
| ChromaDB repo 단위 삭제 후 code add | |
| asset_hierarchy 해당 selected_repo_id 삭제 후 (id, selected_repo_id, type) insert | |
| POST embedding 동기, 200 + chunks_indexed, hierarchy_nodes_created | (GET embedding/status 없음 — 명세 삭제) |

**1차 목표:** POST 한 번으로 해당 레포 코드 파일이 `user_assets_{user_id}`에 code로 들어가고, `retrieve_user_assets(source_filter=["github"])`로 조회되는 것까지 검증.

---

## 7. 문서 관계

- RAPTOR·청크 정의: [AUTOFOLIO_임베딩전략.md](AUTOFOLIO_임베딩전략.md)  
- ChromaDB 스키마: [AUTOFOLIO_User_Asset_스키마_설계.md](AUTOFOLIO_User_Asset_스키마_설계.md) §2  
- SQLite asset_hierarchy: [AUTOFOLIO_DB_스키마_설계.md](AUTOFOLIO_DB_스키마_설계.md) §2.5  
- API: [API_GitHub_Spec.md](API_GitHub_Spec.md) §5  
- id=path 설계 근거: [week3-oauth-repo-list.md](../week-issues/week3-oauth-repo-list.md) § asset_hierarchy path 설계 근거

---

## 8. 문서 이력

- 2.0: GitHub 임베딩 구현 단계·MVP 범위 정리. Phase 1~7, id/path 규칙 정리.
- 2.1: Phase 6 실행 순서 명확화 — 4·5는 청크·임베딩만 생성, ChromaDB 반영은 6.1(삭제) 후 6.2(일괄 add)에서만 수행. API 응답 index_name vs 실제 컬렉션명(user_assets_{user_id}) 안내 추가. 문서 이력 섹션 추가.
- 2.2: GET embedding/status 삭제 — API 명세(week3)에서 제거됨에 따라 Phase 7·디렉터리·MVP 범위에서 제거. 문서 기준(API_GitHub_Spec §5)으로 진행.
