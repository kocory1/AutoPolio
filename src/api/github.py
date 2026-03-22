from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Body, Request, Response
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field

from src.db.sqlite.client import connect
from src.service.git_hub import repos as github_repos
from src.service.git_hub.repos import GitHubTreeTruncatedError
from src.service.github_embedding.hierarchy import fetch_code_document_ids_for_repo
from src.service.github_embedding.service import run_github_repo_embedding_job
from src.service.user.repos import (
    get_selected_repos,
    get_selected_repos_detailed,
    upsert_selected_repos,
)


router = APIRouter(prefix="/api", tags=["GitHub"])


class GitHubEmbeddingRequestBody(BaseModel):
    """
    GitHub code 문서 id로 user_assets 임베딩을 트리거할 때 본문.

    ``code_document_ids``가 비어 있으면 SQLite ``asset_hierarchy``에서
    해당 레포의 ``type=code`` 행 ``id``를 읽는다(명세 SSoT).

    ``include_summaries=True``이면 응답에 Chroma에 저장한 문서 본문(요약 텍스트)을
    ``summaries`` 배열로 포함한다(데모·디버그용, 응답이 커질 수 있음).
    """

    code_document_ids: list[str] = Field(default_factory=list)
    ref: str | None = None
    include_summaries: bool = False


def _error_response(status_code: int, error: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"error": error, "message": message})


async def _require_user_session(request: Request) -> tuple[str, str | None]:
    user_id = request.session.get("user_id")
    if not user_id:
        raise ValueError("UNAUTHORIZED:no_session")

    conn = await connect()
    try:
        cursor = await conn.execute(
            "SELECT access_token, github_username FROM users WHERE id = ?",
            (user_id,),
        )
        row = await cursor.fetchone()
    finally:
        await conn.close()

    if not row or not row["access_token"]:
        raise ValueError("UNAUTHORIZED:no_access_token")

    return user_id, row["github_username"]


async def _require_access_token(request: Request) -> tuple[str, str]:
    user_id = request.session.get("user_id")
    if not user_id:
        raise ValueError("UNAUTHORIZED:no_session")

    conn = await connect()
    try:
        cursor = await conn.execute(
            "SELECT access_token FROM users WHERE id = ?",
            (user_id,),
        )
        row = await cursor.fetchone()
    finally:
        await conn.close()

    if not row or not row["access_token"]:
        raise ValueError("UNAUTHORIZED:no_access_token")

    return user_id, row["access_token"]


@router.get("/github/repos")
async def github_repos_list(
    request: Request,
    page: int = 1,
    per_page: int = 30,
) -> JSONResponse:
    try:
        _, access_token = await _require_access_token(request)
    except ValueError:
        return _error_response(401, "UNAUTHORIZED", "UNAUTHORIZED")

    try:
        result = await github_repos.list_user_repos(
            access_token, page=page, per_page=per_page
        )
    except Exception:
        return _error_response(502, "GITHUB_UPSTREAM_ERROR", "GitHub repos fetch failed")

    return JSONResponse(result)


@router.get("/user/selected-repos")
async def selected_repos_get(request: Request) -> JSONResponse:
    user_id = request.session.get("user_id")
    if not user_id:
        return _error_response(401, "UNAUTHORIZED", "UNAUTHORIZED")

    try:
        items = await get_selected_repos_detailed(user_id)
    except Exception:
        return _error_response(500, "INTERNAL_SERVER_ERROR", "SELECTED_REPOS_FETCH_FAILED")

    return JSONResponse({"selected_repos": items})


@router.put("/user/selected-repos")
async def selected_repos_put(request: Request) -> JSONResponse:
    user_id = request.session.get("user_id")
    if not user_id:
        return _error_response(401, "UNAUTHORIZED", "UNAUTHORIZED")

    body = await request.json()
    repo_ids: List[int] = body.get("repo_ids") or []
    full_names: List[str] = body.get("full_names") or []
    replace: bool = bool(body.get("replace", True))

    if not repo_ids and not full_names:
        return _error_response(400, "BAD_REQUEST", "repo_ids and full_names are both missing")

    try:
        _, access_token = await _require_access_token(request)
    except ValueError:
        return _error_response(401, "UNAUTHORIZED", "UNAUTHORIZED")

    # repo_ids -> full_names resolve (선택: 이번 구현에서는 mock/테스트에서 주로 full_names를 사용)
    resolved_full_names: list[str] = list(full_names)
    if repo_ids:
        # NOTE: 모든 repo_id를 full_name으로 매핑하는 과정이 필요하다.
        for rid in repo_ids:
            gh_id, owner, repo, full_name = await github_repos.resolve_repo_owner_repo(
                access_token, str(rid)
            )
            resolved_full_names.append(full_name)

    created_at = datetime.now(timezone.utc).isoformat()
    try:
        items = await upsert_selected_repos(
            user_id=user_id,
            repo_full_names=resolved_full_names,
            replace=replace,
            created_at=created_at,
        )
    except Exception:
        return _error_response(500, "INTERNAL_SERVER_ERROR", "SELECTED_REPOS_UPSERT_FAILED")

    return JSONResponse({"selected_repos": items})


@router.get("/github/repos/{repo_id:path}/files")
async def github_repo_files(
    request: Request,
    repo_id: str,
    path: str = "/",
    # depth=-1이면 경로 깊이 필터 없음.
    depth: int = -1,
    ref: str | None = None,
) -> JSONResponse:
    try:
        _, access_token = await _require_access_token(request)
    except ValueError:
        return _error_response(401, "UNAUTHORIZED", "UNAUTHORIZED")

    try:
        _, owner, repo, full_name = await github_repos.resolve_repo_owner_repo(
            access_token, repo_id
        )
        result = await github_repos.list_repo_files_tree(
            access_token,
            owner=owner,
            repo=repo,
            path=path,
            depth=depth,
            ref=ref,
        )
        # docs response에서 repo_id를 그대로 노출한다.
        result["repo_id"] = repo_id if repo_id else full_name
        return JSONResponse(result)
    except ValueError:
        return _error_response(400, "BAD_REQUEST", "Invalid repo_id")
    except GitHubTreeTruncatedError as exc:
        return _error_response(
            502,
            "GITHUB_UPSTREAM_ERROR",
            f"GitHub tree truncated: {exc}",
        )
    except Exception as exc:
        return _error_response(
            502,
            "GITHUB_UPSTREAM_ERROR",
            f"GitHub files fetch failed: {type(exc).__name__}: {exc}",
        )


@router.get("/github/repos/{repo_id:path}/contents")
async def github_repo_contents(
    request: Request,
    repo_id: str,
    path: str | None = None,
    ref: str | None = None,
    encoding: str = "raw",
) -> Response:
    if not path:
        return _error_response(400, "BAD_REQUEST", "path 쿼리 파라미터 누락")

    try:
        _, access_token = await _require_access_token(request)
    except ValueError:
        return _error_response(401, "UNAUTHORIZED", "UNAUTHORIZED")

    try:
        _, owner, repo, _ = await github_repos.resolve_repo_owner_repo(
            access_token, repo_id
        )
        data = await github_repos.get_repo_content(
            access_token,
            owner=owner,
            repo=repo,
            path=path,
            ref=ref,
            encoding=encoding,
        )
    except ValueError:
        return _error_response(400, "BAD_REQUEST", "Invalid encoding")
    except Exception as exc:
        return _error_response(
            502,
            "GITHUB_UPSTREAM_ERROR",
            f"GitHub content fetch failed: {type(exc).__name__}: {exc}",
        )

    if encoding == "raw":
        return PlainTextResponse(content=str(data), media_type="text/plain")

    # base64
    return JSONResponse(
        {
            "repo_id": repo_id,
            "path": path,
            "ref": ref,
            "encoding": "base64",
            "content": data.get("content"),
        }
    )


@router.get("/github/repos/{repo_id:path}/commits")
async def github_repo_commits(
    request: Request,
    repo_id: str,
    author: str | None = None,
    path: str | None = None,
    since: str | None = None,
    until: str | None = None,
    per_page: int = 30,
    page: int = 1,
) -> JSONResponse:
    try:
        _, access_token = await _require_access_token(request)
    except ValueError:
        return _error_response(401, "UNAUTHORIZED", "UNAUTHORIZED")

    # author 기본값은 로그인 유저(github_username)
    if author is None:
        conn = await connect()
        try:
            cursor = await conn.execute(
                "SELECT github_username FROM users WHERE id = ?",
                (request.session.get("user_id"),),
            )
            row = await cursor.fetchone()
            author = row["github_username"] if row else None
        finally:
            await conn.close()

    try:
        _, owner, repo, _ = await github_repos.resolve_repo_owner_repo(
            access_token, repo_id
        )
        result = await github_repos.list_repo_commits(
            access_token,
            owner=owner,
            repo=repo,
            author=author,
            path=path,
            since=since,
            until=until,
            per_page=per_page,
            page=page,
        )
        result["repo_id"] = repo_id
        result["author"] = author
        return JSONResponse(result)
    except Exception as exc:
        return _error_response(
            502,
            "GITHUB_UPSTREAM_ERROR",
            f"GitHub commits fetch failed: {type(exc).__name__}: {exc}",
        )


@router.post("/github/repos/{repo_id:path}/embedding")
async def github_repo_embedding(
    request: Request,
    repo_id: str,
    body: GitHubEmbeddingRequestBody = Body(...),
) -> JSONResponse:
    """선택된 레포에 대해 code Chroma id 목록 임베딩(삭제 후 재적재)을 실행한다."""
    try:
        user_id, access_token = await _require_access_token(request)
    except ValueError:
        return _error_response(401, "UNAUTHORIZED", "UNAUTHORIZED")

    try:
        _, _owner, _repo, full_name = await github_repos.resolve_repo_owner_repo(
            access_token, repo_id
        )
    except ValueError:
        return _error_response(400, "BAD_REQUEST", "Invalid repo_id")

    selected = await get_selected_repos(user_id)
    if full_name not in selected:
        return _error_response(403, "FORBIDDEN", "REPO_NOT_SELECTED")

    code_ids = list(body.code_document_ids or [])
    if not code_ids:
        code_ids = await fetch_code_document_ids_for_repo(user_id, full_name)
    if not code_ids:
        return _error_response(400, "BAD_REQUEST", "NO_CODE_ASSETS_IN_HIERARCHY")

    try:
        result = await run_github_repo_embedding_job(
            user_id=user_id,
            access_token=access_token,
            repo_full_name=full_name,
            code_document_ids=code_ids,
            ref=body.ref,
            include_summaries=body.include_summaries,
        )
    except ValueError as exc:
        return _error_response(400, "BAD_REQUEST", str(exc))
    except Exception:
        return _error_response(500, "INTERNAL_SERVER_ERROR", "EMBEDDING_FAILED")

    return JSONResponse({"status": "ok", **result})

