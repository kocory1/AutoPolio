"""
Chroma 문서 id(`owner/repo/...`) 분해 및 bottom-up 폴더 처리 순서 (순수 함수).
"""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import Iterable


def split_chroma_document_id(doc_id: str) -> tuple[str, str]:
    """
    Chroma 문서 id를 `repo_full_name`과 레포 내 상대 경로로 분리한다.

    - code: ``owner/repo/src/app.py`` → (``owner/repo``, ``src/app.py``)
    - folder: ``owner/repo/src/auth`` → (``owner/repo``, ``src/auth``)
    - project: ``owner/repo/`` 또는 ``owner/repo`` → (``owner/repo``, ``/``)

    GitHub `full_name`은 항상 ``login/name`` 형태(첫 두 세그먼트)로 가정한다.
    """
    s = doc_id.strip()
    if not s:
        raise ValueError("doc_id must be non-empty")

    had_trailing_slash = s.endswith("/")
    trimmed = s.rstrip("/")
    parts = trimmed.split("/")

    if len(parts) < 2:
        raise ValueError(f"doc_id must include owner/repo: {doc_id!r}")

    repo_full_name = f"{parts[0]}/{parts[1]}"

    if len(parts) == 2:
        return repo_full_name, "/"

    rel = "/".join(parts[2:])
    if had_trailing_slash and not rel:
        return repo_full_name, "/"
    return repo_full_name, rel


def _posix_parent(path: str) -> str:
    p = PurePosixPath(path)
    if p.parent == PurePosixPath("."):
        return ""
    return p.parent.as_posix()


def direct_children_for_folder(
    folder_path: str,
    file_paths: Iterable[str],
    folder_paths: Iterable[str],
) -> list[str]:
    """
    ``folder_path``의 직계 자식 파일 경로 및 직계 자식 폴더 경로를 정렬해 반환.

    ``folder_path``가 ``""``이면 레포 루트를 뜻한다.
    """
    files = set(file_paths)
    folders = set(folder_paths)
    children: set[str] = set()

    for fp in files:
        if _posix_parent(fp) == folder_path:
            children.add(fp)

    for fd in folders:
        if not fd:
            continue
        if _posix_parent(fd) == folder_path:
            children.add(fd)

    return sorted(children)


def _folder_chain_shallow_to_deepest(repo_rel_path: str) -> list[str]:
    """
    파일의 레포 상대 경로에 대해, 직계~최심 부모 디렉터리 경로를 얕은 순으로 반환.

    예: ``src/auth/login.py`` → ``["src", "src/auth"]``
    """
    p = repo_rel_path.strip().strip("/")
    if not p or "/" not in p:
        return []

    segments = p.split("/")
    if len(segments) < 2:
        return []

    out: list[str] = []
    for i in range(1, len(segments)):
        out.append("/".join(segments[:i]))
    return out


def collect_parent_directories(repo_rel_paths: Iterable[str]) -> set[str]:
    """여러 파일 경로에서 등장하는 모든 부모 디렉터리 경로 집합."""
    folders: set[str] = set()
    for rp in repo_rel_paths:
        if rp == "/" or not rp.strip():
            continue
        for d in _folder_chain_shallow_to_deepest(rp):
            folders.add(d)
    return folders


def bottom_up_folder_order(repo_rel_paths: Iterable[str]) -> list[str]:
    """
    파일 경로들이 암시하는 디렉터리들을 **깊이 내림차순**(bottom-up)으로 정렬해 반환.

    동일 깊이에서는 경로 문자열로 안정 정렬한다.
    """
    folders = collect_parent_directories(repo_rel_paths)

    def depth(path: str) -> int:
        return 0 if not path else path.count("/")

    return sorted(folders, key=lambda p: (-depth(p), p))
