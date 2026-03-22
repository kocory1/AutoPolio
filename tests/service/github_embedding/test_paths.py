"""순수 경로 분해·bottom-up 순서."""

from __future__ import annotations

import pytest

from src.service.github_embedding.paths import (
    bottom_up_folder_order,
    collect_parent_directories,
    direct_children_for_folder,
    split_chroma_document_id,
)


def test_split_chroma_document_id_code_file() -> None:
    assert split_chroma_document_id("octocat/Hello-World/src/app.py") == (
        "octocat/Hello-World",
        "src/app.py",
    )


def test_split_chroma_document_id_folder() -> None:
    assert split_chroma_document_id("org/proj/src/auth") == ("org/proj", "src/auth")


def test_split_chroma_document_id_project_trailing_slash() -> None:
    assert split_chroma_document_id("owner/repo/") == ("owner/repo", "/")


def test_split_chroma_document_id_project_no_trailing() -> None:
    assert split_chroma_document_id("owner/repo") == ("owner/repo", "/")


def test_split_chroma_document_id_invalid() -> None:
    with pytest.raises(ValueError):
        split_chroma_document_id("nope")
    with pytest.raises(ValueError):
        split_chroma_document_id("")


def test_bottom_up_folder_order_two_files() -> None:
    files = ["src/a.py", "src/b/c.py"]
    assert bottom_up_folder_order(files) == ["src/b", "src"]


def test_collect_parent_directories() -> None:
    assert collect_parent_directories(["x.py"]) == set()
    assert collect_parent_directories(["src/a.py", "src/b/c.py"]) == {"src", "src/b"}


def test_direct_children_root() -> None:
    files = {"main.py", "src/a.py"}
    folders = {"src"}
    assert direct_children_for_folder("", files, folders) == ["main.py", "src"]


def test_direct_children_nested() -> None:
    files = {"src/a.py", "src/pkg/x.py"}
    folders = {"src", "src/pkg"}
    assert direct_children_for_folder("src", files, folders) == ["src/a.py", "src/pkg"]
