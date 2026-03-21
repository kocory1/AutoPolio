## Week 4 이슈 정리: GitHub Tree 선택 + 저장된 assets 기반 Contents

> **PR 이력:** 기존 PR을 닫은 뒤, 아래 “최종 반영(추가 변경)”까지 포함해 **새 PR**로 다시 올릴 예정.

### 실험 가이드라인 (먼저 이대로 해보세요)
1. `poetry run uvicorn src.app.main:app --reload --host 127.0.0.1 --port 8000` 등으로 서버 실행 후 `http://127.0.0.1:8000/dashboard` 접속.
2. `GitHub 로그인` → `/api/me`가 `200 OK`인지 확인.
3. `저장된 레포(assets 대상)`에서 레포 버튼 클릭 → `selected_repo_assets` 복원, 트리 체크 상태·`저장된 파일(선택)` 리스트 동기화.
4. **Files Tree**에서 `GET .../files` 버튼으로 트리 로드.
   - 프론트는 `depth`/`ref` 입력 없이 `path`만 전달 가능(기본 `depth=-1`).
   - 백엔드는 **Git Trees API(`recursive=1`)** 로 트리를 가져와 **개수 상한 없이** 필터 결과 전체를 반환(`traverse_cap`/`capped` 없음).
5. 폴더/파일 체크 → 폴더 체크 시 하위 자동 포함, `▸/▾`로 펼치기.
6. `선택 assets 저장` → DB에 **완전 replace**.
7. `저장된 파일(선택)`에서 파일 클릭 → `contents` 표시(`ref` 수동 입력 없음, 기본 브랜치 기준).

### 변경 요약 (누적)

#### 1) 파일 트리 API: Contents 재귀(A) → Git Trees 단일 호출(B)
- **파일:** `src/service/git_hub/repos.py` — `list_repo_files_tree()`
- **흐름(요약):**
  - `ref` 없으면 `GET /repos/{owner}/{repo}` 로 `default_branch` 조회
  - 브랜치면 `GET .../git/ref/heads/{branch}` 로 커밋 SHA (브랜치명은 URL 인코딩)
  - 커밋 SHA면 `GET .../git/commits/{sha}` 로 tree SHA
  - `GET .../git/trees/{tree_sha}?recursive=1` **한 번**으로 flat 트리 수신
  - `blob` → `type: file`, `tree` → `type: dir`(디렉터리 경로는 `/` 접미사 유지)
  - `path` / `depth` 로 서버 측 필터만 적용
- **GitHub `truncated=true`:** 트리가 너무 커 잘리면 `GitHubTreeTruncatedError` → API **502** (`GITHUB_UPSTREAM_ERROR`).

#### 2) 개수 상한(traverse_cap) 제거
- 예전: 정렬 후 앞 N개만 반환 + `capped` / `traverse_cap` 필드.
- **현재:** 해당 로직·쿼리 파라미터·응답 필드 **제거**. 반환 `tree`는 필터 통과분 전부.
- 응답에는 **`visited_nodes`**(실제 반환 노드 수 = `len(tree)`)만 유지.

#### 3) API 라우터
- **파일:** `src/api/github.py` — `GET /api/github/repos/{repo_id:path}/files`
  - `depth` 기본 `-1`, `ref` 선택
  - `truncated` 시 전용 예외로 502 처리

#### 4) 대시보드 HTML 위치
- **파일:** `src/web/dashboard.py` — `dashboard_html` (raw string)
- **파일:** `src/app/main.py` — 라우트만, `dashboard_html` 중복 문자열 제거

#### 5) 프론트(대시보드)
- Files Tree: `depth`/`ref` 입력 제거, `/files?path=...` 위주
- cap 관련 상태 문구 제거
- Contents: `저장된 파일(선택)` 리스트로 재선택, 수동 `ref` 제거

#### 6) User assets (선택 폴더/파일 저장)
- **API:** `GET/PUT /api/user/selected-repo-assets`
- **DB:** `selected_repo_assets` 테이블, PUT 시 replace

#### 7) 문서·OpenAPI
- **파일:** `docs/API_GitHub_Spec.md` — `/files` Git Trees·`truncated`·파라미터 설명 반영
- **스크립트:** `scripts/export_openapi.py` → `docs/openapi.json`

### 주의: 404/502가 나올 수 있는 경우
- **GitHub `truncated=true`:** 레포가 매우 클 때 → **502** (우리 쪽에서 잘라서 줄이지는 않음).
- **권한/존재하지 않는 ref/경로 등:** 기존과 같이 GitHub upstream 오류는 **502** + 메시지로 전달되는 경우가 많음.
- **`ref=main` 고정 제거:** default branch 기준으로 맞춰 `main` 아닌 브랜치에서의 404는 완화되는 편.

### 테스트
- `poetry run pytest -q` → **75 passed** (작업 시점 기준)

---

## 새 PR에 넣을 내용 (복사용)

### PR 제목 (예시)
```
Week 4: GitHub OAuth + Git Trees 파일 트리 + selected assets + 대시보드
```

### PR 본문 (예시)
```markdown
## Summary
- GitHub OAuth·세션 기반 `/api/me` 및 GitHub 연동 API.
- **파일 트리**는 Contents 재귀 호출 대신 **Git Trees API (`recursive=1`)** 로 조회.
- **traverse_cap / capped 제거** — 필터(`path`, `depth`) 결과를 개수 제한 없이 반환. (GitHub이 `truncated=true`일 때만 502)
- 대시보드: 폴더 트리 선택·저장된 assets 기반 contents 재선택 UX. HTML은 `src/web/dashboard.py`로 분리.
- `selected_repo_assets` API + SQLite 스키마.

## Key files
- `src/service/git_hub/repos.py` — `list_repo_files_tree` (Git Trees)
- `src/api/github.py` — `/files`, `GitHubTreeTruncatedError` → 502
- `src/api/user_assets.py`, `src/service/user/selected_assets.py`
- `src/web/dashboard.py`, `src/app/main.py`
- `docs/API_GitHub_Spec.md`, `docs/openapi.json`

## How to test
1. `poetry run uvicorn src.app.main:app --reload --host 127.0.0.1 --port 8000`
2. `/dashboard` → 로그인 → 저장된 레포 선택 → Files Tree 로드 → assets 저장 → 저장된 파일 리스트에서 contents 확인.
3. `poetry run pytest -q`

## Notes
- 이전 PR은 닫았고, **Git Trees 전환 + traverse_cap 제거 등** 이후 수정분까지 이 PR에 포함.
```
