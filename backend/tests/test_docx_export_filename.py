"""Test tên file DOCX tải về — theo lớp + Unit đã chọn thay vì "de-ma-a-..."
(yêu cầu chủ dự án 24/08/2026). Không cần DB."""

from types import SimpleNamespace

import pytest

from app.models.exam import ExportMode
from app.services.docx_renderer import _slugify, export_filename

VARIANT_A = SimpleNamespace(code="A")


def _exam(*, grade=7, unit=1, mode=ExportMode.PLAIN, title="Unit 1 Revision"):
    return SimpleNamespace(
        title=title,
        export_mode=mode,
        grade=SimpleNamespace(number=grade) if grade else None,
        unit=SimpleNamespace(order_no=unit) if unit else None,
    )


def test_uses_grade_and_unit():
    assert export_filename(_exam(), VARIANT_A) == "lop-7-unit-1-hoc-sinh.docx"


def test_answer_key_suffix():
    assert export_filename(_exam(mode=ExportMode.ANSWER_KEY), VARIANT_A) == "lop-7-unit-1-dap-an-do.docx"


def test_two_digit_unit():
    assert export_filename(_exam(grade=9, unit=12), VARIANT_A) == "lop-9-unit-12-hoc-sinh.docx"


def test_no_variant_code_for_default_variant():
    """Mã đề A (mặc định, và là mã duy nhất giao diện tạo) không để lại dấu vết."""
    assert "ma-a" not in export_filename(_exam(), VARIANT_A)


def test_extra_variants_stay_distinct():
    """API vẫn tạo được nhiều mã — hai file phải khác tên, không ghi đè nhau."""
    names = {export_filename(_exam(), SimpleNamespace(code=c)) for c in "ABCD"}
    assert len(names) == 4
    assert export_filename(_exam(), SimpleNamespace(code="B")) == "lop-7-unit-1-hoc-sinh-ma-b.docx"


def test_falls_back_to_title_without_grade_or_unit():
    """Đề "Kiến thức chung"/Cambridge không gắn Unit."""
    exam = _exam(grade=None, unit=None, title="Ôn tập thì hiện tại đơn")
    assert export_filename(exam, VARIANT_A) == "on-tap-thi-hien-tai-don-hoc-sinh.docx"


def test_grade_without_unit():
    assert export_filename(_exam(unit=None), VARIANT_A) == "lop-7-hoc-sinh.docx"


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("Đề ôn tập", "de-on-tap"),
        ("UNIT 1 – GLOBAL SUCCESS 7", "unit-1-global-success-7"),
        ("Tiếng Việt có dấu", "tieng-viet-co-dau"),
        (r"a//b\c:d", "a-b-c-d"),  # ký tự cấm trong tên file Windows
        ("   ", ""),
    ],
)
def test_slugify(raw, expected):
    assert _slugify(raw) == expected


def test_filename_has_no_unsafe_characters():
    name = export_filename(_exam(title=r'Đề "khó" \ / : * ?'), VARIANT_A)
    assert all(ch.isalnum() or ch in "-." for ch in name)
