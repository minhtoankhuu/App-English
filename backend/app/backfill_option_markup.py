"""Làm sạch một lần các lựa chọn đã lưu bị model nhân đôi ký tự đuôi phát âm
(vd 'cats<u>s</u>' -> 'cat<u>s</u>') — xem app/services/text_markup.py.

Câu sinh TRƯỚC khi có bản vá chống nhân đôi vẫn lưu markup lỗi trong DB, khiến bản
xem trước trên web của đề cũ hiện sai (DOCX đã tự sửa lúc render). Script này sửa
thẳng dữ liệu để preview web cũng sạch.

Idempotent: chạy lại nhiều lần không đổi thêm gì. Mặc định DRY-RUN (chỉ in ra), thêm
cờ --apply để ghi thật:  python -m app.backfill_option_markup --apply
"""

import argparse

from sqlalchemy import select

from app.db import SessionLocal
from app.models.exam import Question
from app.services.text_markup import dedupe_pronunciation_suffix


def _fixed_options(options: list[dict] | None) -> tuple[list[dict] | None, bool]:
    if not options:
        return options, False
    changed = False
    new_options = []
    for opt in options:
        text = opt.get("text")
        if isinstance(text, str):
            fixed = dedupe_pronunciation_suffix(text)
            if fixed != text:
                changed = True
                opt = {**opt, "text": fixed}
        new_options.append(opt)
    return new_options, changed


def run_backfill(db, *, apply: bool) -> tuple[int, int]:
    """Trả (số_câu_sửa, số_lựa_chọn_sửa). apply=False chỉ đếm/in, không ghi."""
    questions = db.scalars(select(Question).where(Question.options.isnot(None))).all()
    fixed_questions = 0
    fixed_options = 0
    for question in questions:
        new_options, changed = _fixed_options(question.options)
        if not changed:
            continue
        for old, new in zip(question.options, new_options):
            if old.get("text") != new.get("text"):
                fixed_options += 1
                print(f"  q{question.id} order {question.order_no}: {old.get('text')!r} -> {new.get('text')!r}")
        fixed_questions += 1
        if apply:
            question.options = new_options
    if apply:
        db.commit()
    return fixed_questions, fixed_options


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Ghi thay đổi vào DB (mặc định chỉ DRY-RUN).")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        fixed_questions, fixed_options = run_backfill(db, apply=args.apply)
        mode = "ĐÃ GHI" if args.apply else "DRY-RUN (chưa ghi)"
        print(f"\n[{mode}] {fixed_options} lựa chọn ở {fixed_questions} câu cần sửa.")
        if not args.apply and fixed_questions:
            print("Chạy lại với --apply để ghi thật.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
