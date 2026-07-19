import shutil
from pathlib import Path

from docx import Document
from sqlalchemy import func, select

from app.import_knowledge import import_global_success
from app.models.academic import Grade, Unit
from app.models.knowledge import KnowledgeChunk, KnowledgeDocument

KB_ROOT = Path(__file__).resolve().parents[2] / "Knowledge_Base" / "Global Success"


def _copy_unit3_grade7(tmp_path: Path) -> Path:
    dest_dir = tmp_path / "G7"
    dest_dir.mkdir(parents=True)
    shutil.copyfile(KB_ROOT / "G7" / "GS7 - UNIT 3 - LESSON.docx", dest_dir / "GS7 - UNIT 3 - LESSON.docx")
    return tmp_path


def _unit3_grade7(db) -> Unit:
    return db.scalar(select(Unit).join(Grade).where(Grade.number == 7, Unit.order_no == 3))


def _chunk_count(db, document_id) -> int:
    return db.scalar(select(func.count()).select_from(KnowledgeChunk).where(KnowledgeChunk.document_id == document_id))


def test_import_creates_document_and_chunks(seeded_db, tmp_path):
    base_path = _copy_unit3_grade7(tmp_path)

    stats = import_global_success(seeded_db, base_path)
    seeded_db.commit()

    assert stats.files_seen == 1
    assert stats.documents_created == 1
    assert stats.chunks_written > 0

    unit3 = _unit3_grade7(seeded_db)
    document = seeded_db.scalar(select(KnowledgeDocument).where(KnowledgeDocument.unit_id == unit3.id))
    assert document is not None
    assert document.file_name == "GS7 - UNIT 3 - LESSON.docx"
    assert _chunk_count(seeded_db, document.id) == stats.chunks_written


def test_import_is_idempotent_on_rerun(seeded_db, tmp_path):
    base_path = _copy_unit3_grade7(tmp_path)

    import_global_success(seeded_db, base_path)
    seeded_db.commit()
    unit3 = _unit3_grade7(seeded_db)
    document = seeded_db.scalar(select(KnowledgeDocument).where(KnowledgeDocument.unit_id == unit3.id))
    rows_after_first_import = _chunk_count(seeded_db, document.id)

    stats = import_global_success(seeded_db, base_path)
    seeded_db.commit()

    assert stats.documents_created == 0
    assert stats.documents_updated == 0
    assert stats.documents_unchanged == 1
    assert _chunk_count(seeded_db, document.id) == rows_after_first_import


def test_import_replaces_chunks_when_file_content_changes(seeded_db, tmp_path):
    base_path = _copy_unit3_grade7(tmp_path)
    dest_file = base_path / "G7" / "GS7 - UNIT 3 - LESSON.docx"

    import_global_success(seeded_db, base_path)
    seeded_db.commit()
    unit3 = _unit3_grade7(seeded_db)
    document = seeded_db.scalar(select(KnowledgeDocument).where(KnowledgeDocument.unit_id == unit3.id))
    original_checksum = document.checksum

    document_xml = Document(str(dest_file))  # giả lập file được cập nhật: sửa 1 đoạn rồi lưu lại
    document_xml.paragraphs[0].add_run(" (updated)")
    document_xml.save(str(dest_file))

    stats = import_global_success(seeded_db, base_path)
    seeded_db.commit()
    seeded_db.refresh(document)

    assert stats.documents_updated == 1
    assert document.checksum != original_checksum
    assert _chunk_count(seeded_db, document.id) > 0
