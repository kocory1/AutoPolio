"""Chroma 레포 단위 삭제 후 재추가 (tmp persist)."""

from __future__ import annotations

from src.service.github_embedding.chroma_store import (
    add_documents_sync,
    delete_docs_for_repo_sync,
)


def test_delete_docs_for_repo_then_add_isolated(tmp_path) -> None:
    persist = tmp_path / "chroma"
    persist.mkdir()
    uid = "user-embed-test"
    repo = "acme/demo"

    add_documents_sync(
        uid,
        ids=[f"{repo}/a.py", f"{repo}/b.py", "other/r/z.py"],
        documents=["da", "db", "dz"],
        metadatas=[
            {"user_id": uid, "repo": repo, "ref": "", "type": "code", "path": "a.py"},
            {"user_id": uid, "repo": repo, "ref": "", "type": "code", "path": "b.py"},
            {"user_id": uid, "repo": "other/r", "ref": "", "type": "code", "path": "z.py"},
        ],
        embeddings=[[0.1, 0.2]] * 3,
        persist_dir=persist,
    )

    removed = delete_docs_for_repo_sync(uid, repo, persist_dir=persist)
    assert removed == 2

    add_documents_sync(
        uid,
        ids=[f"{repo}/a.py"],
        documents=["new"],
        metadatas=[
            {"user_id": uid, "repo": repo, "ref": "", "type": "code", "path": "a.py"},
        ],
        embeddings=[[0.3, 0.4]],
        persist_dir=persist,
    )

    import chromadb

    from src.db.vector.chroma import build_user_asset_collection_name

    client = chromadb.PersistentClient(path=str(persist))
    col = client.get_or_create_collection(name=build_user_asset_collection_name(uid))
    got = col.get()
    assert set(got["ids"]) == {f"{repo}/a.py", "other/r/z.py"}
