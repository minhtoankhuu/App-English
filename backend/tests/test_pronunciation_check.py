"""Test kiểm tra chất lượng lựa chọn phát âm/trọng âm — ca lấy đúng từ đề thật lỗi
(ảnh giáo viên 21/07/2026, khối I. PRONUNCIATION và II. STRESS)."""

from app.services.pronunciation_check import check_pronunciation_options


def _pron(options):
    return check_pronunciation_options(options, is_pronunciation=True)


def _stress(options):
    return check_pronunciation_options(options, is_pronunciation=False)


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
    """Kiểu -s/-es và -ed hợp lệ khi cụm gạch chân khác nhau ('s' vs 'es', 'ed' vs
    'ied') — không được cảnh báo nhầm. Nhóm chọn đúng quy tắc 3 giống - 1 khác để
    không dính luôn cảnh báo âm."""
    # /ɪz/, /ɪz/, /ɪz/, /s/
    assert _pron(["dress<u>es</u>", "watch<u>es</u>", "box<u>es</u>", "book<u>s</u>"]) == []
    # /d/, /d/, /d/, /t/
    assert _pron(["tri<u>ed</u>", "play<u>ed</u>", "marr<u>ied</u>", "look<u>ed</u>"]) == []


def test_stress_allows_long_syllable_clusters():
    """Trọng âm bọc cả âm tiết — không áp ngưỡng độ dài/đồng nhất cụm. Dùng bộ 3-1 hợp
    lệ (3 từ trọng âm tiết 1, 'begin' trọng âm tiết 2) để không dính cảnh báo trọng âm."""
    assert _stress(["<u>hand</u>some", "<u>tra</u>vel", "be<u>gin</u>", "<u>mod</u>ern"]) == []


def test_stress_still_flags_fabricated_words():
    warnings = _stress(["<u>cel</u>ebrate", "<u>dec</u>orate", "<u>exhi</u>bitionn", "inter<u>na</u>tional"])
    assert "Không phải từ tiếng Anh có thật" in _joined(warnings)


def test_phrase_options_are_flagged_but_not_spell_checked():
    """Cụm từ bị cảnh báo "phải là 1 từ đơn" nhưng KHÔNG bị soi từ điển (soi cả cụm
    sẽ luôn báo sai) — lỗi lọt ra đề thật 24/07/2026."""
    warnings = check_pronunciation_options(["community service", "free time"], is_pronunciation=False)
    text = _joined(warnings)
    assert "phải là 1 từ đơn" in text
    assert "community service" in text
    assert "Không phải từ tiếng Anh có thật" not in text


def test_flags_multi_word_and_hyphenated_options_from_real_exam():
    warnings = _pron(
        ["native language<u>s</u>", "film<u>s</u>", "magic<u>s</u>", "voice<u>s</u>"]
    )
    text = _joined(warnings)
    assert "phải là 1 từ đơn" in text and "native languages" in text

    warnings = _pron(
        ["southeast Asia<u>s</u>", "black-and-white<u>s</u>", "destruction<u>s</u>", "ending<u>s</u>"]
    )
    text = _joined(warnings)
    assert "southeast Asias" in text and "black-and-whites" in text


def test_empty_options_return_no_warnings():
    assert check_pronunciation_options([], is_pronunciation=True) == []
