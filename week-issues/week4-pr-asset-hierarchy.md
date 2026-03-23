# PR 초안: asset_hierarchy ↔ 임베딩 동기화

## Compare & PR 생성 URL

**Base: `main` ← Head: `week4/asset-hierarchy-embedding-sync`**

https://github.com/kocory1/AutoPolio/compare/main...week4/asset-hierarchy-embedding-sync?expand=1

---

## 제목

```
feat: asset_hierarchy에 folder/project 동기화 (code path 기반)
```

---

## 본문 (복사용)

```markdown
## Summary
- 임베딩 잡(`run_github_repo_embedding_job`) 완료 후 **`code_document_ids`(코드 경로)**로부터 결정적으로 **folder·project** id를 재생성해 `asset_hierarchy`를 갱신한다 (기존 `folder`/`project` 행 DELETE 후 INSERT).
- **`code`** 행은 기존과 같이 `sync_code_rows_from_selected_assets`로만 채운다.
- **`folder/project`**는 Chroma `result["ids"]`가 아니라 **code 경로(부모 디렉터리 + project root)**로 파생한다.
- 설계·운영 전제는 `week-issues/week4-asset-hierarchy-embedding.md` 참고.

## Changes
- `src/service/user/asset_hierarchy_sync.py`: `sync_folder_project_rows_from_code_document_ids`
- `src/service/github_embedding/service.py`: 파이프라인 직후 위 동기화 호출
- `tests/service/test_asset_hierarchy_sync_folder_project.py`: 동기화 단위 테스트

## How to test
```bash
poetry run pytest -q
```

## Related doc
- `week-issues/week4-asset-hierarchy-embedding.md`
```
