"""Import tài liệu Global Success (G6-G8) vào knowledge_documents/knowledge_chunks.

Idempotent theo checksum SHA-256: file không đổi thì bỏ qua, file đổi nội dung
thì xoá toàn bộ chunk cũ và parse lại. Không đụng Cambridge/Tense/G9 (khác cấu
trúc — xem docs/superpowers/specs/2026-07-19-knowledge-base-global-success-design.md).

Chạy độc lập: `python -m app.import_knowledge` — không gộp vào seed.py vì đây là
nhập tài liệu lớn, không phải danh mục tĩnh (tránh làm chậm mọi lần khởi động).
"""

import argparse
import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import SessionLocal
from app.models.academic import Grade, Unit
from app.models.knowledge import KnowledgeChunk, KnowledgeDocument
from app.services.knowledge_parser import parse_lesson_docx

GRADES = (6, 7, 8)
_UNIT_NUMBER_RE = re.compile(r"UNIT\s*(\d+)", re.IGNORECASE)


@dataclass
class ImportStats:
    files_seen: int = 0
    documents_created: int = 0
    documents_updated: int = 0
    documents_unchanged: int = 0
    chunks_written: int = 0


def _checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _unit_number(file_name: str) -> int | None:
    match = _UNIT_NUMBER_RE.search(file_name)
    return int(match.group(1)) if match else None


def import_global_success(db: Session, base_path: Path, force: bool = False) -> ImportStats:
    """`base_path` là gốc Knowledge_Base/ — file thật nằm dưới `Global Success/G{6,7,8}/`.

    `force=True` bỏ qua so khớp checksum, parse lại toàn bộ file đã import — dùng khi
    sửa logic parser (`docx_utils`/`knowledge_parser`) mà nội dung file .docx không đổi,
    nên checksum vẫn khớp và bản ghi cũ (chunk cũ) sẽ không tự refresh nếu không có cờ này."""
    stats = ImportStats()
    grades = {g.number: g for g in db.scalars(select(Grade).where(Grade.number.in_(GRADES)))}
    global_success_dir = base_path / "Global Success"

    for grade_number in GRADES:
        grade = grades.get(grade_number)
        folder = global_success_dir / f"G{grade_number}"
        if grade is None or not folder.is_dir():
            continue

        units_by_order = {u.order_no: u for u in db.scalars(select(Unit).where(Unit.grade_id == grade.id))}

        for file_path in sorted(folder.glob("*.docx")):
            stats.files_seen += 1
            order_no = _unit_number(file_path.name)
            unit = units_by_order.get(order_no) if order_no else None
            if unit is None:
                continue

            checksum = _checksum(file_path)
            existing = db.scalar(
                select(KnowledgeDocument).where(
                    KnowledgeDocument.unit_id == unit.id,
                    KnowledgeDocument.file_name == file_path.name,
                )
            )

            if existing is not None and existing.checksum == checksum and not force:
                stats.documents_unchanged += 1
                continue

            parsed_chunks = parse_lesson_docx(file_path)

            if existing is not None:
                existing.checksum = checksum
                existing.chunks.clear()
                document = existing
                stats.documents_updated += 1
            else:
                document = KnowledgeDocument(unit_id=unit.id, file_name=file_path.name, checksum=checksum)
                db.add(document)
                stats.documents_created += 1

            for chunk in parsed_chunks:
                document.chunks.append(
                    KnowledgeChunk(
                        order_no=chunk.order_no,
                        chunk_type=chunk.chunk_type,
                        section_title=chunk.section_title,
                        raw_text=chunk.raw_text,
                        structured=chunk.structured,
                    )
                )
            stats.chunks_written += len(parsed_chunks)
            db.flush()

    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force",
        action="store_true",
        help="Parse lại toàn bộ file kể cả khi checksum không đổi (dùng khi logic parser vừa sửa).",
    )
    args = parser.parse_args()

    settings = get_settings()
    db = SessionLocal()
    try:
        stats = import_global_success(db, Path(settings.knowledge_base_dir), force=args.force)
        db.commit()
        print(
            f"Import OK: {stats.files_seen} file, {stats.documents_created} mới, "
            f"{stats.documents_updated} cập nhật, {stats.documents_unchanged} không đổi, "
            f"{stats.chunks_written} chunk ghi."
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
