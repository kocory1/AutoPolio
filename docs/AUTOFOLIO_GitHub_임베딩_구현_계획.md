# GitHub 임베딩 구현 계획

**문서 버전:** 2.4  
**기준:** [AUTOFOLIO_임베딩전략.md](AUTOFOLIO_임베딩전략.md), [AUTOFOLIO_User_Asset_스키마_설계.md](AUTOFOLIO_User_Asset_스키마_설계.md), [AUTOFOLIO_DB_스키마_설계.md](AUTOFOLIO_DB_스키마_설계.md), [API_GitHub_Spec.md](API_GitHub_Spec.md), [week3-oauth-repo-list.md](../week-issues/week3-oauth-repo-list.md) § asset_hierarchy path 설계 근거

---

## 1. 목표

- **트리거:** `POST /api/github/repos/{repo_id}/embedding` 호출 시, **이미 SQLite `asset_hierarchy`에 올라와 있는 유저 선택(경로)**을 기준으로 ChromaDB `user_assets_{user_id}`에 벡터를 저장한다. (RAPTOR 시 folder·project 청크는 파이프라인이 만들고, 해당 노드도 `asset_hierarchy`에 반영한다.)
- **제약:** 레포는 해당 유저의 `selected_repos`에 등록된 경우에만 임베딩 허용. 미등록 시 403.
- **결과:** 포트폴리오 그래프의 `retrieve_user_assets(source_filter=["github"])`로 GitHub 청크 조회 가능.

---

## 2. 기준 문서 요약

### 2.1 asset_hierarchy (SQLite)

- **컬럼:** `id`(PK), `selected_repo_id`(FK), `type` 만 존재. path 전용 컬럼 없음.
- **id:** 경로 자체를 id로 사용. 예: `owner/repo/src/auth/login.py`. ChromaDB document id와 동일.  
  GitHub Contents API에 쓸 path는 id에서 `owner/repo/`(또는 `owner/repo`) 제거해 유도.
- **채우는 시점(유저 선택):** **GitHub·User 관련 API**에서 유저가 임베딩할 파일·폴더(또는 펼쳐진 파일 목록)를 확정할 때 `type=code` 등으로 **먼저** 반영한다. 유저가 고른 것만 대상이므로 **임베딩 단계에서 별도 노이즈 필터·전체 트리 스캔으로 걸러내지 않는다.**
- **임베딩 이후:** RAPTOR로 생성한 `folder`·`project` 노드는 같은 테이블에 **추가**(또는 재임베딩 시 해당 레포의 folder/project 행만 갱신). code 행은 유저 선택 API가 SSoT이면 임베딩이 임의로 지우지 않는다(재선택 시 선택 API에서 정리).

### 2.2 ChromaDB User Asset

- **컬렉션:** `user_assets_{user_id}`.
- **문서 필드:** `id`, `document`, `metadata`, `embedding`.
- **metadata (MVP 4개):** `type`, `source`, `repo`, `path`.  
  path = 레포 내 경로 (예: `src/auth/login.py`, `src/auth`, `"/"`).
- **id:** `owner/repo/` + path 형태. code: `owner/repo/src/auth/login.py`, folder: `owner/repo/src/auth`, project: `owner/repo/`.

### 2.3 임베딩 전략 (RAPTOR)

- **임베딩 API(모델·제공자):** 구현에서 선택한다. 벡터 차원은 선택한 모델에 맞춘다. **본 문서는 모델명·차원을 규정하지 않는다.**
- **대상 목록:** `asset_hierarchy`에서 해당 `selected_repo_id`·`type=code`인 행의 `id`를 순회한다. **노이즈 필터는 두지 않는다**(선택은 유저·선택 API가 담당).
- **POST body `paths[]`:** API 명세상 필드가 있을 수 있으나, 구현 우선순위는 **DB에 반영된 선택**이다. `paths[]`만으로 트리를 다시 훑는 방식과 병행하지 않는 것을 권장(중복·불일치 방지). 명세 정리는 별도 이슈로 API_GitHub_Spec과 맞출 수 있다.
- **계층 임베딩 순서:**  
  1. **파일(code) 단위:** 대상 blob마다 내용을 읽어 각각 임베딩(또는 document 생성 후 임베딩).  
  2. **경로 `/` 기준 bottom-up:** 레포 내 `path`를 `/`로 분해해 **가장 깊은 디렉터리부터** 상위로 올라가며, **같은 직계 부모 디렉터리**에 속한 청크(직접 하위 파일의 code, 또는 이미 만든 하위 folder 요약)를 묶어 LLM 요약 → `type=folder` 임베딩. **더 이상 상위 경로(부모)가 없을 때** 마지막 단계로 `type=project`(루트) 요약·임베딩.
- code: document = summary 우선, 없으면 content(truncate).  
  folder/project: document = LLM 요약.
- 본인 커밋만 필터는 [AUTOFOLIO_임베딩전략.md](AUTOFOLIO_임베딩전략.md)에 정의되어 있으나 MVP에서 생략 가능.

### 2.4 API (POST embedding)

- **Request:** branch, strategy, force_refresh 등. **`paths[]`는 asset_hierarchy를 쓰는 구현에서는 생략 가능**(또는 무시) — 실제 대상은 DB의 `id` 목록.
- (레거시·명세) `paths[]`가 있는 경우: 선택 API와의 이중 입력이 되지 않도록 팀에서 한 가지 SSoT로 통일할 것.
- **Response:** status, embedding(chunks_indexed, dimensions, total_tokens, storage), hierarchy_nodes_created.
- **전제:** selected_repos에 해당 repo 없으면 403.
- **저장소 표현:** 실제 저장은 ChromaDB 컬렉션 `user_assets_{user_id}` 하나뿐이며, `metadata.repo`로 레포 구분. API 응답의 `embedding.storage.index_name`(예: `autofolio_github_repo_123_main`)은 레포·브랜치 식별용 **논리 이름**이며, ChromaDB 컬렉션명과는 다름.

---

## 3. 구현 단계 (Phase)

### Phase 1: 인증·권한·인프라

| 순서 | 작업 | 설명 |
|------|------|------|
| 1.1 | 유저·레포 검증 | 인증된 user_id로 `get_selected_repos(user_id)` 호출. repo_id(또는 owner/name)가 반환 목록에 없으면 403. |
| 1.2 | 임베딩 클라이언트 | 텍스트 리스트 → 벡터 리스트. 사용 모델의 차원에 맞춤(모델 선택은 구현 담당, 본 문서 비규정). |
| 1.3 | ChromaDB upsert | `user_assets_{user_id}` 컬렉션에 id/document/metadata/embedding 추가. 동일 id는 덮어쓰기(upsert). |

**산출물:** selected_repos 검증 로직, embed 함수/클래스, ChromaDB add(upsert) 호출 래퍼.

---

### Phase 2: 임베딩 대상 로드 (SQLite)

| 순서 | 작업 | 설명 |
|------|------|------|
| 2.1 | `asset_hierarchy` 조회 | 해당 레포의 `selected_repo_id`에 대해 `type=code`인 행만 조회. 각 행의 `id`가 Chroma document id이자 Contents API용 레포 내 path를 유도하는 SSoT. |
| 2.2 | 빈 선택 처리 | code 행이 없으면 400 등으로 명확히 실패(또는 no-op 정책은 팀 합의). |
| 2.3 | (선택) 유효성 | 읽기 불가·과대용량 파일은 **스킵 또는 truncate**만 적용(노이즈 **룰베이스 경로 필터는 사용하지 않음**). |

**산출물:** 임베딩할 `(id, selected_repo_id)` 목록. **Trees API로 전체 트리를 받아 필터링하는 단계는 사용하지 않는다.**

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

### Phase 5: folder / project (RAPTOR Bottom-up, `/` 기준)

| 순서 | 작업 | 설명 |
|------|------|------|
| 5.1 | 깊이 순 정렬 | code(및 필요 시 중간 folder)의 레포 내 `path`로부터 **부모 디렉터리**를 `/` 단위로 파악. **가장 깊은 디렉터리부터** 상위로 처리할 순서를 만든다. |
| 5.2 | folder 청크(단계 반복) | 각 디렉터리마다 **직계 하위**에 해당하는 청크만 묶는다: 직접 포함된 code 파일의 document(또는 요약), 그리고 이미 생성한 **직계 하위 folder**의 요약. 이 묶음으로 LLM 폴더 요약 → `type=folder` document → 임베딩. id = `owner/repo/{dir}`, metadata path = 레포 내 디렉터리 경로(예: `src/auth`). |
| 5.3 | project 청크 | 루트(`"/"`) 직계에 해당하는 folder(및 루트에만 있는 code 등)를 묶어 LLM 프로젝트 요약. id = `owner/repo/`, metadata path = `"/"`. |
| 5.4 | 임베딩 벡터 생성 | folder/project document → embed → 청크별 id, document, metadata, embedding을 메모리상 리스트로 확보. **ChromaDB 반영은 하지 않음.** 실제 DB 반영은 Phase 6.2(일괄 add)에서만 수행. |

**산출물:** folder/project 청크 리스트(id, document, metadata, embedding 포함). ChromaDB 쓰기는 Phase 6에서만. (MVP에서 code만 먼저 하고 5는 후순위 가능.)

---

### Phase 6: ChromaDB·asset_hierarchy 정리

**실행 순서:** 4·5에서는 청크 리스트와 임베딩 벡터만 생성하고 Chroma에는 아직 쓰지 않는다. ChromaDB 반영은 **6.1(삭제) → 6.2(일괄 add)**.

| 순서 | 작업 | 설명 |
|------|------|------|
| 6.1 | 해당 repo 기존 Chroma 청크 삭제 | `user_assets_{user_id}`에서 해당 `repo_full_name` 청크만 삭제(id prefix 또는 metadata.repo). |
| 6.2 | 새 청크 일괄 add | Phase 4·5에서 만든 code·folder·project 청크를 Chroma에 일괄 add. |
| 6.3 | asset_hierarchy(folder·project) 동기화 | **code 행은 유저 선택 API가 이미 넣었으므로 임베딩이 일괄 삭제하지 않는다.** RAPTOR로 생긴 `folder`·`project` 행만 insert 또는 기존 folder/project 행 삭제 후 재삽입(재임베딩 시 하위 요약이 바뀌므로). |

**산출물:** repo 단위 Chroma 삭제+add, SQLite는 **folder/project 노드 정리 + code 행 유지(선택 API SSoT)**.

---

### Phase 7: API

| 순서 | 작업 | 설명 |
|------|------|------|
| 7.1 | POST /api/github/repos/{repo_id}/embedding | 인증 → Phase 1.1 검증 → 2~6 순서 실행 → 200 + status, embedding(chunks_indexed, dimensions, total_tokens, storage), hierarchy_nodes_created. |
| 7.2 | 에러 매핑 | 400(asset_hierarchy에 code 행 없음, 또는 명세상 paths 누락 등), 401, 403(레포 미선택), 404, 409(진행 중), 502. **API_GitHub_Spec §5**의 `paths[]` 필수 여부는 asset_hierarchy SSoT로 바꿀 경우 명세 개정과 맞출 것. |

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
│   └── github.py                 # POST embedding (+ 선택 API는 asset_hierarchy 반영)
├── service/
│   ├── github/
│   │   ├── hierarchy.py          # asset_hierarchy 조회·folder/project 반영
│   │   ├── contents.py           # id → GitHub Contents 조회
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
| selected_repos 검증, asset_hierarchy에서 code id 로드, Contents로 내용 조회 | 본인 커밋만 필터 |
| code 청크만: content(truncate) → embed → ChromaDB | folder/project LLM 요약 |
| ChromaDB repo 단위 삭제 후 add | |
| 선택 API로 asset_hierarchy(code) 선반영 / 임베딩 후 folder·project 행 반영 | |
| POST embedding 동기, 200 + chunks_indexed, hierarchy_nodes_created | (GET embedding/status 없음 — 명세 삭제) |

**1차 목표:** 선택 API로 `asset_hierarchy`에 code id가 쌓인 뒤, POST 한 번으로 해당 id들이 `user_assets_{user_id}`에 code로 들어가고, `retrieve_user_assets(source_filter=["github"])`로 조회되는 것까지 검증.

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
- 2.3: 임베딩 모델 비규정. 노이즈 필터 — 넓은 스코프는 룰베이스 컷, paths 명시 시 해당 범위는 전부 인덱싱 원칙. RAPTOR: 파일 단위 code 후 `/` 기준 bottom-up folder → project 명시.
- 2.4: **asset_hierarchy는 GitHub·User 선택 API에서 code 행 선반영.** 임베딩은 DB `id`만 따라가며 노이즈 필터·전체 트리 스캔 없음. Phase 2를 SQLite 로드로 전환. Phase 6.3는 code 행 유지·folder/project만 동기화. `paths[]`와의 관계 명시.
