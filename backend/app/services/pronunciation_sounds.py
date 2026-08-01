"""Suy cách phát âm (đuôi -s/-es, -ed từ CHÍNH TẢ; nguyên âm giữa từ từ TỪ ĐIỂN IPA)
để kiểm tra bằng code quy tắc "3 từ giống — 1 từ khác" của bài phát âm (PRD 7.3).

Vì sao cần: đề thật sinh bằng prompt v7/v8 vẫn ra những nhóm sai quy tắc mà mắt thường
khó soi ngay — vd 'learned /d/, played /d/, worked /t/, talked /t/' (2-2, không có
đáp án duy nhất) hay 'help /e/, fell /e/, sell /e/, tell /e/' (cả 4 giống nhau).
Prompt không ép được, nên chốt bằng luật xác định.

Nguyên tắc an toàn: CHỈ kết luận khi chắc chắn. Chính tả tiếng Anh nhiều ngoại lệ
(vd 'used' /d/ nhưng 'promised' /t/ — cùng đuôi 'sed'), nên những trường hợp nhập
nhằng trả None và bên gọi sẽ BỎ QUA kiểm tra thay vì cảnh báo nhầm.
"""

import re
from functools import lru_cache

from app.services.text_markup import UNDERLINE_MARKUP_RE

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

# ---- Nguyên âm giữa từ (dạng "âm trong từ") ------------------------------
# Dùng từ điển phát âm CMU (cmudict, offline) để lấy chuỗi âm vị ARPABET rồi CĂN theo
# vị trí cụm chữ được gạch chân. Chỉ căn được khi số CỤM NGUYÊN ÂM (chữ) bằng số ÂM
# NGUYÊN ÂM (phiên âm) — nếu lệch (vd 'e' câm ở 'source'/'feature') thì trả None và
# bỏ qua, tránh căn sai. So sánh theo ký hiệu nguyên âm (bỏ dấu trọng âm 0/1/2).
_VOWEL_LETTERS = frozenset("aeiouy")
_ARPABET_VOWELS = frozenset(
    {"AA", "AE", "AH", "AO", "AW", "AY", "EH", "ER", "EY", "IH", "IY", "OW", "OY", "UH", "UW"}
)
_STRESS_DIGIT_RE = re.compile(r"\d")
_ARPABET_IPA = {
    "AA": "/ɑː/", "AE": "/æ/", "AH": "/ʌ/", "AO": "/ɔː/", "AW": "/aʊ/", "AY": "/aɪ/",
    "EH": "/e/", "ER": "/ɜː/", "EY": "/eɪ/", "IH": "/ɪ/", "IY": "/iː/", "OW": "/əʊ/",
    "OY": "/ɔɪ/", "UH": "/ʊ/", "UW": "/uː/",
}

# Ký hiệu IPA để in ra cảnh báo cho giáo viên đọc.
SOUND_IPA = {"s": "/s/", "z": "/z/", "iz": "/ɪz/", "t": "/t/", "d": "/d/", "id": "/ɪd/", **_ARPABET_IPA}


@lru_cache(maxsize=1)
def _cmu_dict() -> dict:
    import cmudict

    return cmudict.dict()


def _vowel_letter_runs(word: str) -> list[tuple[int, int]]:
    runs: list[tuple[int, int]] = []
    i = 0
    while i < len(word):
        if word[i] in _VOWEL_LETTERS:
            j = i
            while j < len(word) and word[j] in _VOWEL_LETTERS:
                j += 1
            runs.append((i, j))
            i = j
        else:
            i += 1
    return runs


def underlined_vowel_sound(option_text: str) -> str | None:
    """Âm nguyên âm (ARPABET, bỏ trọng âm) của cụm chữ được gạch chân, hoặc None khi
    không xác định chắc chắn (từ không có trong từ điển, cụm gạch chân không phủ đúng
    1 cụm nguyên âm, hoặc số cụm nguyên âm chữ ≠ số âm nguyên âm)."""
    match = UNDERLINE_MARKUP_RE.search(option_text)
    if match is None:
        return None
    u_lo = match.start()
    u_hi = u_lo + len(match.group(1))
    word = UNDERLINE_MARKUP_RE.sub(r"\1", option_text).strip().lower()
    if not word.isalpha():
        return None
    prons = _cmu_dict().get(word)
    if not prons:
        return None
    vowels = [_STRESS_DIGIT_RE.sub("", p) for p in prons[0] if _STRESS_DIGIT_RE.sub("", p) in _ARPABET_VOWELS]
    runs = _vowel_letter_runs(word)
    if len(runs) != len(vowels):
        return None
    covered = [i for i, (start, end) in enumerate(runs) if start < u_hi and end > u_lo]
    if len(covered) != 1:
        return None
    return vowels[covered[0]]


def vowel_sounds(option_texts: list[str]) -> tuple[list[str], str] | None:
    """Âm nguyên âm gạch chân cho CẢ nhóm — chỉ trả khi MỌI lựa chọn xác định được
    (thà bỏ sót còn hơn báo nhầm). None = không kiểm tra được nhóm này."""
    if len(option_texts) < 3:
        return None
    sounds = [underlined_vowel_sound(t) for t in option_texts]
    if any(s is None for s in sounds):
        return None
    return [s for s in sounds if s is not None], "âm trong từ"


# ---- Trọng âm (dạng "stress") --------------------------------------------
def stressed_syllable_index(word: str) -> int | None:
    """Vị trí âm tiết mang trọng âm CHÍNH (0-based) theo từ điển CMU, hoặc None khi
    không xác định được (không có trong từ điển, hoặc không có dấu trọng âm chính)."""
    prons = _cmu_dict().get(word.lower())
    if not prons:
        return None
    vowels = [p for p in prons[0] if p[-1].isdigit()]
    for i, phone in enumerate(vowels):
        if phone.endswith("1"):
            return i
    return None


def stress_positions(words: list[str]) -> tuple[list[int], str] | None:
    """Vị trí trọng âm cho CẢ nhóm — chỉ trả khi mọi từ đều tra được VÀ đều đa âm tiết
    (từ 1 âm tiết không có tương phản trọng âm). None = bỏ qua (không báo nhầm)."""
    if len(words) < 3:
        return None
    positions: list[int] = []
    for word in words:
        prons = _cmu_dict().get(word.lower())
        if not prons:
            return None
        n_syllables = sum(1 for p in prons[0] if p[-1].isdigit())
        idx = stressed_syllable_index(word)
        if idx is None or n_syllables < 2:
            return None
        positions.append(idx)
    return positions, "trọng âm"


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
