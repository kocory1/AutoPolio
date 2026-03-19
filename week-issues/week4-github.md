## Week 4 이슈 정리: GitHub Tree 선택 + 저장된 assets 기반 Contents

### 실험 가이드라인 (먼저 이대로 해보세요)
1. `poetry run uvicorn ...` 서버를 켠 뒤 브라우저에서 `http://localhost:8000/dashboard`로 접속합니다.
2. `GitHub 로그인` 버튼으로 OAuth 로그인 후 `/api/me`가 `200 OK`로 떠야 합니다.
3. `저장된 레포(assets 대상)`에서 버튼(저장된 레포)을 클릭합니다.
   - 이 단계에서 해당 `selected_repo_id`의 `selected_repo_assets`가 복원되고,
   - 화면의 `Files Tree`(폴더/파일 트리) 체크 상태와 `저장된 파일(선택)` 리스트가 자동으로 동기화됩니다.
4. `Files Tree` 섹션에서 `GET /api/github/repos/{repo_id}/files` 버튼을 클릭해 트리를 로드합니다.
   - 이제 프론트에서 `depth/ref`를 입력하지 않고, 서버가 기본적으로 “끝까지” 순회하되 `traverse_cap=500`까지만 허용합니다.
5. 트리에서 폴더/파일 체크를 합니다.
   - 폴더 체크 시 하위(자식)까지 자동으로 포함되도록 동작합니다.
   - 폴더 펼치기(`▸/▾`)로 깊이 확인이 가능합니다.
6. `선택 assets 저장`을 누르면 현재 체크된 assets가 “완전 replace”로 저장됩니다.
7. `저장된 파일(선택)` 리스트에서 파일을 다시 클릭하면, 해당 경로의 `contents`가 로드되어 `contents` 영역에 표시됩니다.
   - 이제 `ref=main` 같은 입력이 없고, GitHub API는 repo의 `default_branch`를 기준으로 동작합니다.

### 변경 요약 (이번 주에 실제로 한 것)
1. 백엔드: GitHub 파일 트리 “끝까지” 순회(단, 안전 cap 적용)
- `src/service/git_hub/repos.py`
  - `list_repo_files_tree`에서 `depth=-1`을 “끝까지”로 해석
  - `traverse_cap=500`을 기본 안전장치로 두고, cap을 넘으면 더 내려가지 않고 중단
  - 응답에 `capped`, `visited_nodes`, `traverse_cap` 등을 포함해 상태 확인 가능

2. 백엔드: `/api/github/repos/{repo_id}/files` 요청 스펙 정리
- `src/api/github.py`
  - `GET /api/github/repos/{repo_id:path}/files`
    - 기본 `depth=-1`, 기본 `traverse_cap=500`
    - 프론트가 `ref`/`depth`를 직접 넣지 않아도 동작하도록 정리

3. 프론트: “나열” 대신 폴더/파일 트리 펼쳐서 선택
- `src/app/main.py` (dashboard_html)
  - `Files Tree` UI에서 기존 `depth`, `ref` 인풋을 제거
  - `GET /files`는 `path`만 보내도록 변경
  - 트리 로딩 실패 시 전체가 실패하는 strict 동작은 유지(502로 표시)

4. 프론트: contents 선택 UI를 “저장된 assets 기반 리스트”로 전환
- `src/app/main.py` (dashboard_html)
  - `저장된 파일(선택)` 리스트를 추가
  - 리스트는 현재 `selectedAssetKeys` 중 `code:*`(파일)만 뽑아서 렌더링
  - 리스트에서 파일을 클릭하면 `/api/github/repos/{repo_id}/contents`를 호출해 내용 표시
  - 기존 `contentsRef`/`btnContents`/`contentsPath` 입력 UI는 제거

### 주요 동작 포인트 / 왜 404/502가 섞여 보일 수 있나
- `files` 트리는 `contents` API를 재귀로 도는 방식이라, 특정 repo/경로 조합에서 GitHub가 `404 Not Found`를 주면 현재 구현에서는 해당 트리 로딩이 통째로 502가 됩니다.
- 특히 예전에는 `ref=main`을 강제로 쓰는 요청이 있어서, repo의 default branch가 main이 아닌 경우 404가 쉽게 발생했습니다.
- 이번 변경에서는 files/contents 모두 `ref` 입력을 없애고 repo의 `default_branch` 기반으로 호출되도록 정리했기 때문에, “어떤 단계에서만 되거나 안 되는” 현상이 줄어드는 방향입니다.

### 테스트
- `tests/api/test_github_api.py`
  - `/files` 호출이 `depth/ref` 대신 `depth=-1`와 `traverse_cap=500` 전달을 기대하도록 갱신
- `poetry run pytest -q`
  - 전체 통과 확인: **75 passed**

