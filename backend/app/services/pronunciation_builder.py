"""Dựng câu hỏi phát âm/trọng âm BẰNG CODE (không dùng LLM).

Vì sao: kiểm chứng thực tế cho thấy gpt-4o-mini gần như không sinh đúng dạng này
(0/8 với -s/-es), re-roll cũng vô ích (báo cáo 02/08/2026). Trong khi CODE tính âm
đuôi -s/-es, -ed, nguyên âm và trọng âm CHÍNH XÁC (pronunciation_sounds), nên tự ghép
bộ 4 đúng quy tắc "3 giống - 1 khác" là cách đảm bảo đề luôn đúng.

Nguồn từ: bộ từ chuẩn viết tay (curated) — đảm bảo luôn đủ nguyên liệu ghép nhóm và
đúng chính tả, chạy được cả với Unit chưa nạp corpus. Âm của từng từ KHÔNG hard-code
mà tính lại qua pronunciation_sounds (đã có test), rồi mỗi câu dựng ra được VERIFY lại
bằng chính check_pronunciation_options — sai thì bỏ, không bao giờ xuất câu lỗi.
"""

import random
from collections import Counter

from app.services.ai_provider import QuestionDraft
from app.services.pronunciation_check import check_pronunciation_options, is_real_word
from app.services.pronunciation_sounds import (
    SOUND_IPA,
    _cmu_dict,
    _vowel_letter_runs,
    ed_ending_sound,
    s_ending_sound,
    stressed_syllable_index,
    vowel_sounds,
)

PRONUNCIATION_KINDS = ("s", "ed", "vowel")

_PROMPTS = {
    "s": "Choose the word that has a different pronunciation of the ending -s/-es.",
    "ed": "Choose the word that has a different pronunciation of the ending -ed.",
    "vowel": "Choose the word that has a different pronunciation of the underlined part.",
    "stress": "Choose the word that has a different stress pattern.",
}

# -s/-es: (gốc, đuôi) tách rõ để đặt markup không nhập nhằng (book+s, watch+es, class+es).
_S_WORDS: list[tuple[str, str]] = [
    ("book", "s"), ("cat", "s"), ("map", "s"), ("lake", "s"), ("rock", "s"), ("student", "s"),
    ("plant", "s"), ("shirt", "s"), ("cup", "s"), ("shop", "s"),
    ("dog", "s"), ("pen", "s"), ("ring", "s"), ("song", "s"), ("girl", "s"), ("hand", "s"),
    ("friend", "s"), ("day", "s"), ("boy", "s"), ("teacher", "s"),
    ("box", "es"), ("watch", "es"), ("class", "es"), ("dish", "es"), ("church", "es"),
    ("glass", "es"), ("bus", "es"), ("brush", "es"), ("bench", "es"), ("wish", "es"),
]

# -ed: từ quá khứ đã đúng chính tả; luôn gạch chân 2 chữ cuối "ed".
_ED_WORDS: list[str] = [
    "worked", "stopped", "watched", "cooked", "helped", "washed", "jumped", "laughed", "missed", "danced",
    "played", "saved", "cleaned", "called", "moved", "opened", "loved", "tried", "studied", "enjoyed",
    "wanted", "needed", "visited", "decided", "started", "ended", "waited", "added", "painted", "planted",
]

# Trọng âm: từ 2 âm tiết thường gặp; vị trí trọng âm tính lại bằng cmudict.
_STRESS_WORDS: list[str] = [
    "happy", "modern", "travel", "teacher", "mountain", "city", "open", "doctor", "pencil", "sunny",
    "careful", "handsome", "morning", "evening", "orange", "clever", "husband", "cabbage",
    "begin", "invite", "enjoy", "relax", "forget", "prepare", "allow", "receive", "arrive", "decide",
    "police", "hotel", "guitar", "polite", "return", "explain",
]

# Nguyên âm: bộ 3-1 dựng sẵn (dạng này khó ghép động, ghép sẵn cho chắc & đúng).
_VOWEL_GROUPS: list[list[str]] = [
    ["cl<u>ea</u>n", "br<u>ea</u>d", "t<u>ea</u>ch", "t<u>ea</u>m"],
    ["b<u>oo</u>k", "f<u>oo</u>d", "l<u>oo</u>k", "g<u>oo</u>d"],
    ["c<u>a</u>t", "f<u>a</u>ther", "b<u>a</u>ck", "bl<u>a</u>ck"],
    ["r<u>i</u>ce", "s<u>i</u>t", "b<u>i</u>g", "f<u>i</u>sh"],
    ["p<u>e</u>n", "h<u>e</u>", "t<u>e</u>n", "b<u>e</u>d"],
    ["c<u>u</u>t", "b<u>u</u>s", "s<u>u</u>n", "p<u>u</u>t"],
]


def _draft(prompt: str, options: list[dict], odd_label: str, odd_word: str, explanation: str) -> QuestionDraft:
    return QuestionDraft(
        prompt_text=prompt,
        answer_text=f"{odd_label}. {odd_word}",
        explanation=explanation,
        target_knowledge="Phát âm" if prompt != _PROMPTS["stress"] else "Trọng âm",
        level_code="A2",
        source_ref="Bộ dựng tự động (không dùng LLM)",
        options=options,
    )


def _finish(items: list[tuple[str, str]], odd_index: int, prompt: str, explain: str) -> QuestionDraft | None:
    """items: list (text_có_markup, từ_hiển_thị); odd_index: vị trí đáp án đúng trong items.
    Trả None nếu câu dựng ra không qua được checker (an toàn tuyệt đối)."""
    labels = ["A", "B", "C", "D"]
    options = [
        {"label": labels[i], "text": text, "is_correct": i == odd_index}
        for i, (text, _word) in enumerate(items)
    ]
    is_pron = prompt != _PROMPTS["stress"]
    if check_pronunciation_options([o["text"] for o in options], is_pronunciation=is_pron):
        return None
    odd_label, (_odd_text, odd_word) = labels[odd_index], items[odd_index]
    return _draft(prompt, options, odd_label, odd_word, explain)


_S_SIBILANT_ENDINGS = ("s", "x", "z", "ch", "sh")
_VOWELS = "aeiou"


def inflect_s(word: str) -> tuple[str, str] | None:
    """(gốc, đuôi) dạng số nhiều/ngôi 3 của `word`, hoặc None nếu không chắc chắn.
    Kết quả PHẢI là từ có thật trong từ điển — chặn dạng bịa (city -> citys)."""
    w = (word or "").lower()
    if not w.isalpha() or len(w) < 2 or w.endswith("s"):
        return None
    if w.endswith("y") and w[-2] not in _VOWELS:
        base, suffix = w[:-1] + "i", "es"  # city -> cit + ies
    elif w.endswith(_S_SIBILANT_ENDINGS):
        base, suffix = w, "es"
    else:
        base, suffix = w, "s"
    return (base, suffix) if is_real_word(base + suffix) else None


def inflect_ed(word: str) -> str | None:
    """Dạng quá khứ có quy tắc của `word`, hoặc None nếu không chắc chắn. Kết quả PHẢI
    là từ có thật — chặn động từ bất quy tắc (go -> goed) và dạng bịa."""
    w = (word or "").lower()
    if not w.isalpha() or len(w) < 3 or w.endswith("ed"):
        return None
    if w.endswith("e"):
        candidate = w + "d"
    elif w.endswith("y") and w[-2] not in _VOWELS:
        candidate = w[:-1] + "ied"
    elif len(w) >= 3 and w[-1] not in _VOWELS and w[-2] in _VOWELS and w[-3] not in _VOWELS and w[-1] not in "wxy":
        candidate = w + w[-1] + "ed"  # stop -> stopped
    else:
        candidate = w + "ed"
    return candidate if is_real_word(candidate) else None


def _s_items(words: list[str]) -> list[tuple[str, str, str | None]]:
    """(text_markup, từ, âm đuôi) cho danh sách từ GỐC."""
    items = []
    for word in words:
        inflected = inflect_s(word)
        if inflected is None:
            continue
        base, suffix = inflected
        items.append((f"{base}<u>{suffix}</u>", base + suffix, s_ending_sound(base + suffix)))
    return items


def _ed_items(words: list[str]) -> list[tuple[str, str, str | None]]:
    items = []
    for word in words:
        past = inflect_ed(word) if not word.endswith("ed") else word
        if past is None:
            continue
        items.append((f"{past[:-2]}<u>ed</u>", past, ed_ending_sound(past)))
    return items


def _build_ending(kind: str, rng: random.Random, unit_words: list[str] | None = None) -> QuestionDraft | None:
    make_items = _s_items if kind == "s" else _ed_items
    if kind == "s":
        curated = [(f"{base}<u>{suf}</u>", base + suf, s_ending_sound(base + suf)) for base, suf in _S_WORDS]
    else:
        curated = [(f"{w[:-2]}<u>ed</u>", w, ed_ending_sound(w)) for w in _ED_WORDS]
    # Ưu tiên vốn từ trong Unit: thử dựng chỉ bằng từ của bài trước, thiếu mới bù curated.
    pools = []
    if unit_words:
        pools.append(make_items(unit_words))
    pools.append(curated)

    for pool in pools:
        draft = _build_ending_from_pool(kind, pool, rng)
        if draft is not None:
            return draft
    return None


def _build_ending_from_pool(kind: str, pool, rng: random.Random) -> QuestionDraft | None:
    buckets: dict[str, list[tuple[str, str]]] = {}
    for text, word, sound in pool:
        if sound is not None:
            buckets.setdefault(sound, []).append((text, word))
    chosen = _pick_three_one(buckets, rng)
    if chosen is None:
        return None
    (major_sound, three), (minor_sound, one) = chosen
    items = three + [one]
    rng.shuffle(items)
    odd_index = items.index(one)
    explain = (
        f"'{one[1]}' phát âm đuôi {SOUND_IPA[minor_sound]}, ba từ còn lại {SOUND_IPA[major_sound]}."
    )
    return _finish(items, odd_index, _PROMPTS[kind], explain)


def _build_vowel(rng: random.Random) -> QuestionDraft | None:
    group = list(rng.choice(_VOWEL_GROUPS))
    # Bộ dựng sẵn đã đúng 3-1, nhưng vẫn xác nhận bằng vowel_sounds rồi tự tìm phần tử
    # "lẻ" theo âm (không phụ thuộc thứ tự cố định trong dữ liệu curated).
    resolved = vowel_sounds(group)
    if resolved is None:
        return None
    sounds, _ = resolved
    counts = Counter(sounds)
    odd_sound = min(counts, key=lambda s: counts[s])
    major_sound = max(counts, key=lambda s: counts[s])
    items = [(text, _plain(text)) for text in group]
    rng.shuffle(items)
    sounds_after = vowel_sounds([t for t, _ in items])[0]
    odd_index = sounds_after.index(odd_sound)
    explain = (
        f"'{items[odd_index][1]}' có nguyên âm {SOUND_IPA.get(odd_sound, odd_sound)}, "
        f"ba từ còn lại {SOUND_IPA.get(major_sound, major_sound)}."
    )
    return _finish(items, odd_index, _PROMPTS["vowel"], explain)


def _build_stress(rng: random.Random, unit_words: list[str] | None = None) -> QuestionDraft | None:
    # Ưu tiên từ trong Unit (đa âm tiết, tra được trọng âm), thiếu mới bù bộ chuẩn.
    for words in ([w for w in (unit_words or []) if is_real_word(w)], _STRESS_WORDS):
        draft = _build_stress_from_words(words, rng)
        if draft is not None:
            return draft
    return None


def _syllable_count(word: str) -> int:
    """Số âm tiết theo từ điển CMU (0 nếu không tra được)."""
    prons = _cmu_dict().get(word.lower())
    if not prons:
        return 0
    return sum(1 for phone in prons[0] if phone[-1].isdigit())


def _build_stress_from_words(words: list[str], rng: random.Random) -> QuestionDraft | None:
    buckets: dict[int, list[tuple[str, str]]] = {}
    for word in words:
        # Từ 1 âm tiết không có tương phản trọng âm -> loại khỏi bài trọng âm.
        if _syllable_count(word) < 2:
            continue
        idx = stressed_syllable_index(word)
        marked = _stress_markup(word, idx)
        if idx is None or marked is None:
            continue
        buckets.setdefault(idx, []).append((marked, word))
    chosen = _pick_three_one(buckets, rng)
    if chosen is None:
        return None
    (major_pos, three), (minor_pos, one) = chosen
    items = three + [one]
    rng.shuffle(items)
    odd_index = items.index(one)
    explain = f"'{one[1]}' trọng âm âm tiết {minor_pos + 1}, ba từ còn lại âm tiết {major_pos + 1}."
    return _finish(items, odd_index, _PROMPTS["stress"], explain)


def _plain(text: str) -> str:
    return text.replace("<u>", "").replace("</u>", "")


def _stress_markup(word: str, idx: int | None) -> str | None:
    """Gạch chân đúng âm tiết mang trọng âm. None khi không căn chắc chắn được: số cụm
    nguyên âm (chữ) phải bằng số âm tiết, nếu không sẽ bọc nhầm (vd 'layer' có 1 cụm
    'aye' nhưng 2 âm tiết -> bọc cả từ, sai)."""
    if idx is None:
        return None
    runs = _vowel_letter_runs(word.lower())
    if len(runs) != _syllable_count(word) or idx >= len(runs):
        return None
    start, end = runs[idx]
    return f"{word[:start]}<u>{word[start:end]}</u>{word[end:]}"


def _pick_three_one(buckets: dict, rng: random.Random):
    """Chọn 1 âm/vị trí đa số (>=3 từ) + 1 phần tử khác âm. Trả ((major, [3 items]),
    (minor, one_item)) hoặc None nếu không đủ nguyên liệu."""
    majors = [k for k, v in buckets.items() if len(v) >= 3]
    rng.shuffle(majors)
    for major in majors:
        minors = [(k, it) for k, v in buckets.items() if k != major for it in v]
        if minors:
            three = rng.sample(buckets[major], 3)
            minor_key, one = rng.choice(minors)
            return (major, three), (minor_key, one)
    return None


def build_pronunciation_questions(
    kind: str, count: int, seed: int | None = None, unit_words: list[str] | None = None
) -> list[QuestionDraft]:
    """Dựng tối đa `count` câu dạng `kind` ('s' | 'ed' | 'vowel' | 'stress'), không trùng
    bộ lựa chọn. Mỗi câu đều đã qua checker nên luôn đúng quy tắc 3 giống - 1 khác.

    `unit_words` (vốn từ của Unit) được ƯU TIÊN: thử dựng bằng từ trong bài trước, chỉ
    khi không đủ nguyên liệu mới bù bằng bộ từ chuẩn — nhờ vậy đề bám sách hơn mà vẫn
    đảm bảo đúng. Dạng 'vowel' dùng nhóm dựng sẵn nên chưa áp dụng."""
    rng = random.Random(seed)
    builder = {
        "s": lambda: _build_ending("s", rng, unit_words),
        "ed": lambda: _build_ending("ed", rng, unit_words),
        "vowel": lambda: _build_vowel(rng),
        "stress": lambda: _build_stress(rng, unit_words),
    }.get(kind)
    if builder is None:
        return []
    out: list[QuestionDraft] = []
    seen: set[frozenset[str]] = set()
    for _ in range(count * 20):  # thử dư để lọc trùng, dừng khi đủ
        if len(out) >= count:
            break
        draft = builder()
        if draft is None:
            continue
        key = frozenset(o["text"] for o in draft.options)
        if key in seen:
            continue
        seen.add(key)
        out.append(draft)
    return out
