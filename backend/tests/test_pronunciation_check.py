"""Test kiểm tra chất lượng lựa chọn phát âm/trọng âm — ca lấy đúng từ đề thật lỗi
(ảnh giáo viên 21/07/2026, khối I. PRONUNCIATION và II. STRESS)."""

from app.services.pronunciation_check import check_pronunciation_options


def _pron(options):
    return check_pronunciation_options(options, check_cluster_shape=True)


def _stress(options):
    return check_pronunciation_options(options, check_cluster_shape=False)


def _joined(warnings):
    return " | ".join(warnings)


def test_flags_fabricated_words():
    """'boring' bị chế thành foring/woring/soring — không phải từ tiếng Anh."""
    warnings = _pron(["b<u>or</u>ing", "f<u>or</u>ing", "w<u>or</u>ing", "s<u>or</u>ing"])
    text = _joined(warnings)
    assert "Không phải từ tiếng Anh có thật" in text
    assert "foring" in text and "woring" in text and "soring" in text
    assert "boring" not in text


def test_flags_underline_spanning_whole_word():
    warnings = _pron(["g<u>ather</u>", "l<u>ather</u>", "f<u>ather</u>", "m<u>other</u>"])
    text = _joined(warnings)
    assert "Phần gạch chân quá dài" in text


def test_flags_inconsistent_clusters_between_options():
    warnings = _pron(["tr<u>a</u>ditional", "p<u>ar</u>t", "m<u>ar</u>t", "h<u>ar</u>t"])
    text = _joined(warnings)
    assert "gạch chân cụm chữ khác nhau" in text


def test_flags_missing_underline_markup():
    warnings = _pron(["cl<u>ea</u>n", "bread", "t<u>ea</u>ch", "t<u>ea</u>m"])
    text = _joined(warnings)
    assert "Thiếu gạch chân" in text
    assert "bread" in text


def test_clean_type3_question_has_no_warnings():
    assert _pron(["cl<u>ea</u>n", "br<u>ea</u>d", "t<u>ea</u>ch", "t<u>ea</u>m"]) == []


def test_suffix_types_allow_different_clusters():
    """Kiểu -s/-es và -ed hợp lệ khi cụm khác nhau — không được cảnh báo nhầm."""
    assert _pron(["look<u>s</u>", "game<u>s</u>", "dress<u>es</u>", "watch<u>es</u>"]) == []
    assert _pron(["want<u>ed</u>", "play<u>ed</u>", "marr<u>ied</u>", "look<u>ed</u>"]) == []


def test_stress_allows_long_syllable_clusters():
    """Trọng âm bọc cả âm tiết ('thanks', 'feast') — không áp ngưỡng độ dài/đồng nhất."""
    assert _stress(["<u>thanks</u>giving", "en<u>ter</u>tain", "com<u>pe</u>tition", "<u>fes</u>tival"]) == []


def test_stress_still_flags_fabricated_words():
    warnings = _stress(["<u>cel</u>ebrate", "<u>dec</u>orate", "<u>exhi</u>bitionn", "inter<u>na</u>tional"])
    assert "Không phải từ tiếng Anh có thật" in _joined(warnings)


def test_phrase_options_are_not_spell_checked():
    """Lựa chọn là cụm từ (dạng khác) không bị soi từ điển — tránh cảnh báo nhầm."""
    assert check_pronunciation_options(["community service", "free time"], check_cluster_shape=False) == [
        "Thiếu gạch chân <u> ở lựa chọn: community service, free time."
    ]


def test_empty_options_return_no_warnings():
    assert check_pronunciation_options([], check_cluster_shape=True) == []
