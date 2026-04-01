#!/usr/bin/env python3
"""
data/jobkorea/, data/linkareer/ JSON을 Chroma `passed_cover_letters`에 적재한다.

  poetry run python scripts/load_passed_cover_letters.py --source all
  poetry run python scripts/load_passed_cover_letters.py --limit 5 --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

# 프로젝트 루트 (AutoPolio/)
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

from src.db.vector.chroma import get_chroma_client
from src.service.rag.passed_samples import PASSED_COVER_LETTERS_COLLECTION

load_dotenv(ROOT / ".env")

DEFAULT_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
BATCH_UPSERT = 64


@dataclass
class Stats:
    files_read: int = 0
    files_skipped: int = 0
    chunks_upserted: int = 0
    chunks_skipped: int = 0
    skip_reasons: dict[str, int] = field(default_factory=dict)

    def bump_skip(self, reason: str) -> None:
        self.chunks_skipped += 1
        self.skip_reasons[reason] = self.skip_reasons.get(reason, 0) + 1


def _read_id_set(path: Path) -> set[str]:
    if not path.is_file():
        return set()
    out: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s and not s.startswith("#"):
            out.add(s)
    return out


def _parse_linkareer_company(combined: str) -> tuple[str, str, str]:
    """'회사 / 포지션 / 연도' 형태 split."""
    parts = [p.strip() for p in combined.split("/")]
    c = parts[0] if len(parts) > 0 else ""
    p = parts[1] if len(parts) > 1 else ""
    y = parts[2] if len(parts) > 2 else ""
    return c, p, y


def _resolve_metadata(
    source_key: str,
    doc: dict,
) -> tuple[str, str, str, str]:
    """
    Returns: (company, position, year, source_label)
    source_label: JSON의 source 필드 (잡코리아 / 링커리어)
    """
    src_label = str(doc.get("source") or "").strip()
    if source_key == "linkareer":
        combined = str(doc.get("company") or "")
        pc, pp, py = _parse_linkareer_company(combined)
        pos_f = str(doc.get("position") or "").strip()
        yr_f = str(doc.get("year") or "").strip()
        company = pc or combined
        position = pos_f or pp
        year = yr_f or py
        return company, position, year, src_label or "링커리어"
    company = str(doc.get("company") or "").strip()
    position = str(doc.get("position") or "").strip()
    year = str(doc.get("year") or "").strip()
    return company, position, year, src_label or "잡코리아"


def _format_year_for_document(y: str) -> str:
    """DB에 '2015' 또는 '2015년 상반기' 등이 올 수 있음 — 불필요한 '년' 중복 방지."""
    y = y.strip()
    if not y:
        return ""
    if "년" in y:
        return y
    return f"{y}년"


def _build_document_text(
    company: str,
    position: str,
    year: str,
    question: str,
    q_idx: int,
) -> str:
    c, p, y = company.strip(), position.strip(), year.strip()
    qn = (question or "").strip()
    n = q_idx + 1
    y_fmt = _format_year_for_document(y)
    if c and p and y_fmt:
        return f"{c}의 {y_fmt} {p} 공고의 자기소개서 문항 {n} : {qn}"
    return f"자기소개서 문항 {n} : {qn}"


def _metadata_for_chroma(
    question: str,
    answer: str,
    company: str,
    position: str,
    year: str,
    source: str,
) -> dict[str, str]:
    """Chroma 메타데이터는 문자열 위주."""
    return {
        "question": question,
        "answer": answer,
        "company": company,
        "position": position,
        "year": year,
        "source": source,
    }


def _list_json_files(data_dir: Path, source_key: str) -> list[Path]:
    sub = data_dir / source_key
    if not sub.is_dir():
        return []
    return sorted(sub.glob("*.json"))


def _should_skip_linkareer_file(doc_id: str, skip_ids: set[str], skip_answer_ids: set[str]) -> bool:
    return doc_id in skip_ids or doc_id in skip_answer_ids


@dataclass
class ChunkRecord:
    chunk_id: str
    document: str
    metadata: dict[str, str]


def _parse_file(path: Path, source_key: str, stats: Stats, skip_linkareer: set[str]) -> list[ChunkRecord]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    doc_id = str(raw.get("id") or "").strip()
    if not doc_id:
        stats.files_skipped += 1
        return []

    if source_key == "linkareer" and doc_id in skip_linkareer:
        stats.files_skipped += 1
        return []

    company, position, year, src_label = _resolve_metadata(source_key, raw)
    questions = raw.get("questions")
    if not isinstance(questions, list):
        stats.files_skipped += 1
        return []

    out: list[ChunkRecord] = []
    for q_idx, item in enumerate(questions):
        if not isinstance(item, dict):
            stats.bump_skip("invalid_question_item")
            continue
        q_text = item.get("question")
        a_text = item.get("answer")
        q_str = (q_text if isinstance(q_text, str) else str(q_text or "")).strip()
        if a_text is None:
            a_str = ""
        elif isinstance(a_text, str):
            a_str = a_text.strip()
        else:
            a_str = str(a_text).strip()

        if not q_str:
            stats.bump_skip("empty_question")
            continue
        if not a_str:
            stats.bump_skip("empty_answer")
            continue

        chunk_id = f"{source_key}_{doc_id}_{q_idx}"
        doc_text = _build_document_text(company, position, year, q_str, q_idx)
        meta = _metadata_for_chroma(q_str, a_str, company, position, year, src_label)
        out.append(ChunkRecord(chunk_id=chunk_id, document=doc_text, metadata=meta))

    return out


def _embed_openai(texts: list[str]) -> list[list[float]]:
    from openai import OpenAI

    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY missing")
    client = OpenAI(api_key=key)
    resp = client.embeddings.create(model=DEFAULT_EMBEDDING_MODEL, input=texts)
    ordered = sorted(resp.data, key=lambda d: d.index)
    return [list(d.embedding) for d in ordered]


def _upsert_batch(
    collection,
    ids: list[str],
    documents: list[str],
    metadatas: list[dict[str, str]],
    embeddings: list[list[float]] | None,
) -> None:
    if embeddings is not None:
        collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )
    else:
        collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Load passed cover letters into Chroma.")
    parser.add_argument(
        "--source",
        choices=("all", "jobkorea", "linkareer"),
        default="all",
        help="데이터 소스 (default: all)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Chroma에 쓰지 않고 파싱만")
    parser.add_argument("--limit", type=int, default=None, help="처리할 JSON 파일 개수 상한 (테스트용)")
    args = parser.parse_args()

    data_dir = ROOT / "data"
    empty_linkareer = _read_id_set(data_dir / "linkareer_empty_ids.txt")
    empty_answer_linkareer = _read_id_set(data_dir / "linkareer_empty_answer_ids.txt")
    skip_linkareer = empty_linkareer | empty_answer_linkareer

    sources: list[str]
    if args.source == "all":
        sources = ["jobkorea", "linkareer"]
    else:
        sources = [args.source]

    stats = Stats()
    all_records: list[ChunkRecord] = []
    files_touched = 0

    for source_key in sources:
        paths = _list_json_files(data_dir, source_key)
        for path in paths:
            if args.limit is not None and files_touched >= args.limit:
                break
            if source_key == "linkareer" and path.stem in skip_linkareer:
                stats.files_read += 1
                stats.files_skipped += 1
                files_touched += 1
                continue
            stats.files_read += 1
            files_touched += 1
            chunks = _parse_file(path, source_key, stats, skip_linkareer)
            all_records.extend(chunks)
        if args.limit is not None and files_touched >= args.limit:
            break

    if args.dry_run:
        print("[dry-run] 파싱 결과 (저장 안 함)")
        print(f"  수집 문항 청크: {len(all_records)}")
        for i, rec in enumerate(all_records[:8]):
            print(f"  --- [{i}] id={rec.chunk_id}")
            print(f"      doc: {rec.document[:120]}{'...' if len(rec.document) > 120 else ''}")
            print(f"      meta keys: {list(rec.metadata.keys())}")
        if len(all_records) > 8:
            print(f"  ... 외 {len(all_records) - 8}건")
        print(
            f"\n처리: {stats.files_read}개 파일 (스킵 파일: {stats.files_skipped}), "
            f"적재 예정: {len(all_records)}문항, 스킵: {stats.chunks_skipped}문항"
        )
        if stats.skip_reasons:
            print(f"  스킵 사유: {stats.skip_reasons}")
        return 0

    if not all_records:
        print("적재할 문항이 없습니다.")
        print(
            f"처리: {stats.files_read}개 파일, 적재: 0문항, 스킵: {stats.chunks_skipped}문항 "
            f"(파일 스킵 {stats.files_skipped})"
        )
        return 0

    client = get_chroma_client()
    collection = client.get_or_create_collection(name=PASSED_COVER_LETTERS_COLLECTION)

    use_openai = bool(os.getenv("OPENAI_API_KEY"))
    ids = [r.chunk_id for r in all_records]
    documents = [r.document for r in all_records]
    metadatas = [r.metadata for r in all_records]

    if use_openai:
        print(f"임베딩: OpenAI {DEFAULT_EMBEDDING_MODEL} ({len(all_records)}문항)")
        for i in range(0, len(all_records), BATCH_UPSERT):
            batch_ids = ids[i : i + BATCH_UPSERT]
            batch_docs = documents[i : i + BATCH_UPSERT]
            batch_meta = metadatas[i : i + BATCH_UPSERT]
            embs = _embed_openai(batch_docs)
            _upsert_batch(collection, batch_ids, batch_docs, batch_meta, embs)
            stats.chunks_upserted += len(batch_ids)
    else:
        print("OPENAI_API_KEY 없음 — Chroma 기본 임베더로 document만 upsert")
        for i in range(0, len(all_records), BATCH_UPSERT):
            batch_ids = ids[i : i + BATCH_UPSERT]
            batch_docs = documents[i : i + BATCH_UPSERT]
            batch_meta = metadatas[i : i + BATCH_UPSERT]
            _upsert_batch(collection, batch_ids, batch_docs, batch_meta, None)
            stats.chunks_upserted += len(batch_ids)

    print(
        f"처리: {stats.files_read}개 파일, 적재: {stats.chunks_upserted}문항, "
        f"스킵: {stats.chunks_skipped}문항 (빈 답변 등)"
    )
    if stats.files_skipped:
        print(f"  (스킵한 파일: {stats.files_skipped}개 — linkareer 블랙리스트 등)")
    if stats.skip_reasons:
        print(f"  스킵 사유: {stats.skip_reasons}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
