# asset_hierarchy · GitHub 임베딩 연동 (설계 메모)

`asset_hierarchy` 테이블(`id`, `selected_repo_id`, `type`)과 임베딩 파이프라인이 어떻게 맞물리는지 정리한다.

## 스키마 (`type`: `code` | `folder` | `project`)

| `type` | 채우는 경로 |
|--------|-------------|
| **code** | `sync_code_rows_from_selected_assets(selected_repo_id)` — `selected_repo_assets`에 저장된 **파일(code)** 경로를 Chroma 문서 id 형식 `owner/repo/상대경로`로 INSERT |
| **folder** / **project** | 임베딩 잡 완료 후 `sync_folder_project_rows_from_embedding_result` — 파이프라인이 Chroma에 넣은 `result["ids"]`에서 code가 아닌 id만 골라 DB 반영. `rel == '/'` → **project**, 그 외 상위 폴더 경로 → **folder** |

- **code**는 “에셋 저장·동기화” 흐름에서 먼저 채워진다.
- **folder** / **project**는 임베딩이 끝난 뒤, Chroma에 생성된 id 목록과 동기화된다.

## 임베딩 파이프라인

- 입력: `code_document_ids` — 보통 `asset_hierarchy`의 `type=code` id 목록(`fetch_code_document_ids_for_repo`) 또는 요청 body.
- 파일 원문: `run_github_repo_embedding_job` → `_TokenGitHubContentAdapter` → `get_repo_content` (**GitHub Contents API**).
- 순서: 선택된 파일들 임베딩 → 경로 `/` 기준 **부모 디렉터리 수집** → **bottom-up** 폴더 요약·임베딩 → **프로젝트(루트)** 요약·임베딩.
- 저장: Chroma(유저·레포 메타데이터), 잡 종료 시 `asset_hierarchy`의 folder/project 행 갱신.

## `selected_repo_id`와의 대응

- 잡 API는 `user_id` + `repo_full_name`으로 동작한다.
- DB 기록 시 `selected_repos`에서 `user_id` + `repo_full_name`으로 `selected_repo_id`를 조회해 `asset_hierarchy`에 넣는다.
- 한 유저·레포당 `selected_repos` 행이 하나면 **레포 단위 ≈ selected_repo_id 단위**로 보면 된다.

## 운영 시 전제

1. 임베딩을 돌리려면 먼저 **`type=code` 행**이 있어야 한다 (`NO_CODE_ASSETS_IN_HIERARCHY` 방지). 보통 **selected assets 저장 후** `sync_code_rows_from_selected_assets`로 맞춘다.
2. 파일 원문은 매번 GitHub API로 가져온다. **로컬 캐시/선저장**은 추후 성능 이슈 시 검토.

## 관련 코드

- `src/service/user/asset_hierarchy_sync.py` — code 동기화, folder/project 동기화
- `src/service/github_embedding/service.py` — 임베딩 잡 + 잡 종료 시 folder/project DB 동기화
- `src/service/github_embedding/pipeline.py` — 파일 → 폴더 → 프로젝트 순 파이프라인
- `src/service/github_embedding/hierarchy.py` — `fetch_code_document_ids_for_repo`
