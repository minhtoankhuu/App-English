"""Suy cách phát âm đuôi -s/-es và -ed từ CHÍNH TẢ, để kiểm tra bằng code quy tắc
"3 từ giống — 1 từ khác" của bài phát âm (PRD 7.3).

Vì sao cần: đề thật sinh bằng prompt v7 vẫn ra những nhóm sai quy tắc mà mắt thường
khó soi ngay — vd 'learned /d/, played /d/, worked /t/, talked /t/' (2-2, không có
đáp án duy nhất) hay 'saved /d/, loved /d/, wanted /ɪd/, visited /ɪd/'. Prompt không
ép được, nên chốt bằng luật xác định.

Nguyên tắc an toàn: CHỈ kết luận khi chắc chắn. Chính tả tiếng Anh nhiều ngoại lệ
(vd 'used' /d/ nhưng 'promised' /t/ — cùng đuôi 'sed'), nên những trường hợp nhập
nhằng trả None và bên gọi sẽ BỎ QUA kiểm tra thay vì cảnh báo nhầm.
"""

# ---- Đuôi -s/-es ----------------------------------------------------------
# /ɪz/ khi âm cuối từ gốc là âm xuýt /s, z, ʃ, ʒ, tʃ, dʒ/.
_S_SIBILANT = ("ses", "zes", "shes", "ches", "xes", "ges", "ces")
# /s/ khi âm cuối từ gốc là phụ âm vô thanh /p, t, k, f/ (kể cả khi có 'e' câm:
# type -> types, separate -> separates).
_S_VOICELESS = ("ps", "ts", "ks", "cs", "fs", "pes", "tes", "kes", "fes", "phs")
# Nhập nhằng: 'ths' (months /s/ vs clothes /z/), 'ghs' (laughs /s/ vs sighs /z/).
_S_UNKNOWN = ("ths", "ghs")

# ---- Đuôi -ed -------------------------------------------------------------
_ED_ID = ("ted", "ded")  # /ɪd/ sau /t/ hoặc /d/
# /t/ sau phụ âm vô thanh /p, k, f, s, ʃ, tʃ/.
_ED_VOICELESS = ("ped", "ked", "ced", "ched", "shed", "xed", "fed", "phed", "ssed")
# Nhập nhằng: 'sed' đơn (used /d/ vs promised /t/), 'ghed' (laughed /t/ vs sighed /d/),
# 'thed' (bathed /d/ vs frothed /t/).
_ED_UNKNOWN = ("ghed", "thed")

# Ký hiệu IPA để in ra cảnh báo cho giáo viên đọc.
SOUND_IPA = {"s": "/s/", "z": "/z/", "iz": "/ɪz/", "t": "/t/", "d": "/d/", "id": "/ɪd/"}


def s_ending_sound(word: str) -> str | None:
    """'s' | 'z' | 'iz' — hoặc None khi không suy chắc chắn được."""
    w = word.lower()
    if not w.isalpha() or not w.endswith("s"):
        return None
    if w.endswith(_S_UNKNOWN):
        return None
    if w.endswith(_S_SIBILANT):
        return "iz"
    if w.endswith(_S_VOICELESS):
        return "s"
    return "z"


def ed_ending_sound(word: str) -> str | None:
    """'t' | 'd' | 'id' — hoặc None khi không suy chắc chắn được."""
    w = word.lower()
    if not w.isalpha() or not w.endswith("ed"):
        return None
    if w.endswith(_ED_ID):
        return "id"
    if w.endswith(_ED_UNKNOWN):
        return None
    if w.endswith(_ED_VOICELESS):
        return "t"
    # 'sed' đơn (không phải 'ssed' đã bắt ở trên) là ca nhập nhằng nhất.
    if w.endswith("sed"):
        return None
    return "d"


def ending_sounds(words: list[str]) -> tuple[list[str], str] | None:
    """Suy âm đuôi cho CẢ nhóm lựa chọn — chỉ trả kết quả khi mọi từ cùng một kiểu
    đuôi (-ed hoặc -s/-es) và đều suy được. None = không kiểm tra được (vd dạng so
    sánh nguyên âm giữa từ, hoặc có từ nhập nhằng)."""
    if len(words) < 3:
        return None
    if all(w.lower().endswith("ed") for w in words):
        sounds = [ed_ending_sound(w) for w in words]
        label = "đuôi -ed"
    elif all(w.lower().endswith("s") for w in words):
        sounds = [s_ending_sound(w) for w in words]
        label = "đuôi -s/-es"
    else:
        return None
    if any(s is None for s in sounds):
        return None
    return [s for s in sounds if s is not None], label
