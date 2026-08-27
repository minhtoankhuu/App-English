"""Điều phối sinh câu hỏi: gọi AIProvider rồi chạy Validation Engine trên từng câu,
lưu kết quả vào DB. Tách khỏi router để router chỉ lo HTTP, còn logic nghiệp vụ
nằm ở đây và test được độc lập."""

import random
import re
from dataclasses import replace

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.academic import Grade, ProficiencyLevel, Unit
from app.models.ai_config import AIProviderConfig
from app.models.exam import Exam, ExamBlock, ExamBlockPart, Question
from app.models.exercise import ExerciseType
from app.services.ai_provider import AIGenerationError, AIProvider, BlockSpec, GenerationContext, QuestionDraft
from app.services.docx_renderer import normalize_bracket_root, split_bracket_root, word_family_label
from app.services.exam_pronunciation import build_from_exam_items, odd_one_out
from app.services.ai_provider_factory import get_active_provider
from app.services.crypto import decrypt_api_key
from app.services.openai_embedding import OpenAIEmbeddingClient
from app.services.prompts import detect_pronunciation_kind as _detect_pronunciation_kind
from app.services.pronunciation_builder import build_pronunciation_questions
from app.services.mcq_check import check_multiple_choice
from app.services.pronunciation_check import check_pronunciation_options
from app.services.rag_search import exam_examples
from app.services.unit_vocabulary import unit_vocabulary_words
from app.services.validation import validate_draft
from app.services.word_form_check import check_word_form, detect_word_form_kind, word_family_members

# Dạng phát âm/trọng âm: AI SINH, CODE KIỂM (đổi ngày 27/08/2026).
#
# Trước đó code vừa sinh vừa kiểm — vì đo được LLM gần như không sinh đúng (gpt-4o-mini
# 0/8 với -s/-es, báo cáo 02/08/2026). Nhưng bộ dựng bốc thẳng nhóm 4 từ từ đề thật ra
# dùng lại, nên mục phát âm không gọi AI lần nào và đề nào cũng lặp lại đúng mấy câu
# của đề gốc — trái hẳn mục đích của app (yêu cầu chủ dự án 27/08/2026).
#
# Giờ đề thật chỉ vào prompt làm CÂU MẪU (openai_provider._examples), câu thì AI viết
# mới. Cái giữ chất lượng là bộ kiểm bằng code (`check_pronunciation_options`) — câu
# nào máy đọc ra sai quy tắc 3 giống - 1 khác thì sinh lại, sinh lại vẫn sai thì BỎ và
# bù bằng bộ dựng code. Đề vẫn luôn đủ câu và không có câu sai đáp án, nhưng phần AI
# làm được thì là câu mới. Model càng khá thì tỉ lệ câu mới càng cao.
_PRONUNCIATION_TYPES = {"pronunciation", "stress"}
_MAX_PRONUNCIATION_REGEN = 2  # tối đa 2 lần sinh lại/câu — chặn vòng lặp + giới hạn chi phí
# Dạng tự đánh giá được bằng code -> câu lỗi được tự sinh lại trong pipeline.
_AUTO_FIX_TYPES = _PRONUNCIATION_TYPES | {"multiple_choice", "word_form"}


def _option_key(draft: QuestionDraft) -> frozenset[str]:
    return frozenset(o["text"] for o in draft.options)


def _deterministic_pronunciation_drafts(
    spec: BlockSpec,
    unit_words: list[str] | None = None,
    exam_lines: list[str] | None = None,
    used: set[frozenset[str]] | None = None,
) -> list[QuestionDraft] | None:
    """Dựng câu phát âm/trọng âm bằng code.
    None = không thuộc dạng này hoặc dựng không đủ câu -> caller rơi về LLM.

    Thứ tự ưu tiên nguyên liệu: ĐỀ THẬT của Unit (nhóm 4 từ do giáo viên soạn, bám sách và
    độ khó thật) -> vốn từ của Unit -> bộ từ chuẩn viết tay. Đề thật không ghi đáp án nên
    đáp án được suy bằng chính bộ phân tích âm dùng để kiểm tra; nhóm nào không suy chắc chắn
    thì bỏ, thiếu bao nhiêu bù bằng bộ dựng cũ (xem exam_pronunciation.py).

    `used` là các nhóm 4 từ đã dùng ở phần con TRƯỚC trong cùng khối, và được cập nhật
    thêm trước khi trả về. Rổ câu đọc được của một Unit chỉ vài câu mỗi kiểu (đo ngày
    27/08/2026: G8 Unit 1 có 3 câu đuôi -s/-es, 2 câu -ed, 2 câu nguyên âm), nên không
    chặn xuyên phần con là các phần lặp lại nguyên câu của nhau.
    """
    if spec.exercise_type_code not in _PRONUNCIATION_TYPES:
        return None

    is_pronunciation = spec.exercise_type_code == "pronunciation"
    # Kiểu phải chốt TRƯỚC khi bốc câu từ đề thật: bốc xong mới xét kiểu thì phần con
    # nào cũng lấy chung một rổ, ra đề trộn lẫn đuôi -s/-es với -ed với nguyên âm dù câu
    # lệnh của phần ghi rõ một kiểu (lỗi thấy trên đề sinh ngày 27/08/2026).
    kind = _detect_pronunciation_kind(spec.prompt_override) if is_pronunciation else None
    if used is None:
        used = set()

    drafts_from_exam = build_from_exam_items(
        exam_lines or [],
        is_pronunciation=is_pronunciation,
        count=spec.question_count,
        kind=kind,
        exclude=used,
    )
    if len(drafts_from_exam) >= spec.question_count:
        for draft in drafts_from_exam:
            draft.level_code = spec.level_code
        used.update(_option_key(d) for d in drafts_from_exam)
        return drafts_from_exam

    if spec.exercise_type_code == "stress":
        drafts = build_pronunciation_questions("stress", spec.question_count, unit_words=unit_words)
    elif kind is not None:
        drafts = build_pronunciation_questions(kind, spec.question_count, unit_words=unit_words)
    else:
        # Không rõ kiểu -> trộn -s/-es, -ed, nguyên âm cho đa dạng, đan xen.
        kinds = ["s", "ed", "vowel"]
        pools = {
            k: build_pronunciation_questions(k, spec.question_count, unit_words=unit_words) for k in kinds
        }
        drafts = []
        i = 0
        while len(drafts) < spec.question_count and any(pools.values()):
            pool = pools[kinds[i % len(kinds)]]
            if pool:
                drafts.append(pool.pop(0))
            i += 1
    # Bù cho đủ số câu bằng bộ dựng cũ, đặt đề thật lên trước.
    seen = used | {_option_key(d) for d in drafts_from_exam}
    drafts = drafts_from_exam + [d for d in drafts if _option_key(d) not in seen]
    drafts = drafts[: spec.question_count]
    if not drafts:
        return None
    for draft in drafts:
        draft.level_code = spec.level_code
    used.update(_option_key(d) for d in drafts)
    return drafts


def _pronunciation_drafts(
    provider: AIProvider,
    spec: BlockSpec,
    context: GenerationContext,
    unit_words: list[str],
    exam_lines: list[str],
    used: set[frozenset[str]],
) -> list[QuestionDraft]:
    """Câu phát âm/trọng âm: AI sinh trước, bộ dựng bằng code chỉ bù cho đủ số câu.

    Chỉ giữ câu QUA được bộ kiểm bằng code. Sai quy tắc 3 giống - 1 khác nghĩa là câu
    không có đáp án duy nhất — đó là câu hỏng, không phải câu "cần xem lại", nên không
    áp nguyên tắc "cảnh báo, không chặn cứng" ở đây: bỏ và bù bằng câu dựng được.
    """
    try:
        drafts = provider.generate(spec, context)
    except AIGenerationError:
        drafts = []
    drafts = _auto_fix_pronunciation_drafts(provider, spec, context, drafts)

    kept: list[QuestionDraft] = []
    for draft in drafts:
        if len(kept) >= spec.question_count:
            break
        key = _option_key(draft)
        if key in used or _machine_warnings(draft, spec):
            continue
        used.add(key)
        kept.append(draft)

    missing = spec.question_count - len(kept)
    if missing > 0:
        fill = _deterministic_pronunciation_drafts(
            replace(spec, question_count=missing), unit_words, exam_lines, used
        )
        kept += fill or []
    return kept


def _prompt_key(prompt_text: str | None) -> str:
    """Khoá so trùng: bỏ dấu câu, khoảng trắng thừa và tên nhân vật đầu mỗi lượt — model
    hay ra lại y hệt câu cũ chỉ đổi mỗi tên người nói."""
    lines = []
    for line in (prompt_text or "").lower().split("\n"):
        _, sep, rest = line.partition(":")
        lines.append(rest if sep else line)
    text = " ".join(" ".join(lines).split())
    return "".join(ch for ch in text if ch.isalnum() or ch.isspace() or ch == "_")


def _duplicate_key(draft: QuestionDraft, spec: BlockSpec | None = None) -> str:
    """Khoá so trùng của một câu.

    Dạng phát âm/trọng âm so theo BỘ 4 LỰA CHỌN, không phải câu dẫn: cả phần con dùng
    chung đúng một câu dẫn ("Choose the word that has a different pronunciation of the
    ending -s/-es.") nên so theo câu dẫn thì từ câu thứ 2 trở đi câu nào cũng bị báo
    trùng dù 4 từ khác hẳn nhau. Mỗi câu như vậy đốt thêm _MAX_PRONUNCIATION_REGEN lượt
    gọi API, mà bản thay thế cũng mang đúng câu dẫn đó nên không bao giờ được nhận —
    tiền mất mà câu không đổi (đo trên đề sinh 27/08/2026).
    """
    if spec is not None and spec.exercise_type_code in _PRONUNCIATION_TYPES and draft.options:
        return "|".join(sorted((o.get("text") or "").lower() for o in draft.options))
    return _prompt_key(draft.prompt_text)


def _duplicate_warning(
    draft: QuestionDraft, seen: set[str], spec: BlockSpec | None = None
) -> list[str]:
    """Đề thật 24/08/2026: câu 17, 20 và 24 giống hệt nhau ("What do people usually do to
    ______ the Mid-Autumn Festival?") chỉ khác tên nhân vật."""
    if _duplicate_key(draft, spec) in seen:
        return ["Câu này trùng nội dung với câu đã sinh trước đó trong cùng phần."]
    return []


_OPTION_LABELS = ("A", "B", "C", "D")


def _answer_key_warnings(draft: QuestionDraft, *, is_pronunciation: bool) -> list[str]:
    """Lựa chọn đánh dấu đúng phải CHÍNH LÀ lựa chọn khác 3 cái còn lại.

    `check_pronunciation_options` chỉ nhận 4 chuỗi lựa chọn nên không nhìn thấy đáp án
    đánh ở đâu — đề sinh 27/08/2026 có câu 'birds /z/, friends /z/, cats /s/, dogs /z/'
    đánh đáp án vào 'dogs' (giải thích cũng bịa theo). Câu sai đáp án là câu hỏng nặng
    nhất: học sinh làm đúng vẫn bị chấm sai, mà nhìn đề thì không thấy gì bất thường.

    Nhóm nào máy KHÔNG đọc được âm cũng bị loại. Không đọc được nghĩa là không bảo đảm
    được, mà câu phát âm sai thì không cứu bằng cảnh báo — đề sinh cùng ngày lọt
    'heavy/season/please/bear' (2-2) và 'cartoon/carrier/carry/carpet' (2-2) đúng vì
    `vowel_sounds` trả None rồi bộ kiểm im lặng cho qua.
    """
    options = draft.options or []
    if len(options) != 4:
        return []
    texts = [o.get("text") or "" for o in options]
    odd = odd_one_out(texts, is_pronunciation=is_pronunciation)
    if odd is None:
        return [
            "Không đọc được âm của cả 4 lựa chọn để đối chiếu đáp án — hãy dùng từ thông "
            "dụng, đánh vần đúng, và bọc <u> đúng một cụm nguyên âm."
        ]
    marked = [i for i, option in enumerate(options) if option.get("is_correct")]
    if marked != [odd]:
        expected = f"{_OPTION_LABELS[odd]}. {texts[odd]}"
        return [f"Đáp án đánh sai chỗ — lựa chọn khác 3 cái còn lại là {expected}."]
    return []


def _machine_warnings(draft: QuestionDraft, spec: BlockSpec) -> list[str]:
    """Cảnh báo kiểm được bằng code cho các dạng mà máy tự đánh giá được chất lượng —
    dùng làm điều kiện tự sinh lại trong pipeline."""
    code = spec.exercise_type_code
    if code == "multiple_choice":
        return check_multiple_choice(draft.prompt_text, draft.options)
    if code == "word_form":
        return check_word_form(
            draft.prompt_text,
            draft.answer_text,
            draft.target_knowledge,
            kind=detect_word_form_kind(spec.prompt_override),
            options=draft.options,
            # Họ từ đã ghim vào prompt_override của lần gọi này (Phần B ôn lại Phần A).
            allowed_family=_pinned_family(spec.prompt_override),
        )
    if code not in _PRONUNCIATION_TYPES or not draft.options:
        return []
    is_pronunciation = code == "pronunciation"
    return check_pronunciation_options(
        [opt.get("text", "") for opt in draft.options],
        is_pronunciation=is_pronunciation,
    ) + _answer_key_warnings(draft, is_pronunciation=is_pronunciation)


def _auto_fix_pronunciation_drafts(
    provider: AIProvider, spec: BlockSpec, context: GenerationContext, drafts: list[QuestionDraft]
) -> list[QuestionDraft]:
    """Với dạng phát âm/trọng âm: câu nào fail kiểm tra bằng code thì sinh lại (kèm
    cảnh báo làm feedback), tối đa _MAX_PRONUNCIATION_REGEN lần, giữ bản ít lỗi nhất.
    Câu đạt hoặc dạng khác giữ nguyên. Không finalize/chặn — vẫn để Validation Engine
    gắn cảnh báo lên câu cuối cùng nếu vẫn còn lỗi."""
    if spec.exercise_type_code not in _AUTO_FIX_TYPES:
        return drafts
    fixed: list[QuestionDraft] = []
    seen: set[str] = set()
    for draft in drafts:
        warnings = _machine_warnings(draft, spec) + _duplicate_warning(draft, seen, spec)
        attempts = 0
        while warnings and attempts < _MAX_PRONUNCIATION_REGEN:
            attempts += 1
            try:
                candidate = provider.regenerate_one(
                    spec, context, exclude_prompt=draft.prompt_text, feedback="; ".join(warnings)
                )
            except AIGenerationError:
                break
            candidate_warnings = _machine_warnings(candidate, spec) + _duplicate_warning(
                candidate, seen, spec
            )
            if len(candidate_warnings) < len(warnings):
                draft, warnings = candidate, candidate_warnings
        seen.add(_duplicate_key(draft, spec))
        fixed.append(draft)
    return fixed


def _active_embedding_client(db: Session) -> OpenAIEmbeddingClient | None:
    """`None` khi chưa cấu hình AI (vẫn dùng MockAIProvider) — Validation Engine bỏ
    qua kiểm tra trùng lặp theo embedding, chỉ còn fuzzy-match như trước Giai đoạn 1D."""
    config = db.scalar(select(AIProviderConfig).where(AIProviderConfig.is_active.is_(True)))
    if config is None:
        return None
    return OpenAIEmbeddingClient(decrypt_api_key(config.api_key_encrypted), config.embedding_model)


def _embed_drafts(client: OpenAIEmbeddingClient | None, drafts: list[QuestionDraft]) -> list[list[float] | None]:
    """Embed theo batch 1 lần cho cả danh sách — tránh N round-trip OpenAI cho N câu
    trong 1 block (xem docs/superpowers/specs/2026-07-21-llm-rag-integration-design.md mục 7)."""
    if client is None or not drafts:
        return [None] * len(drafts)
    return client.embed_batch([d.prompt_text for d in drafts])


def embed_questions_for_bank(db: Session, questions: list[Question]) -> None:
    """Embed theo batch các câu chuyển vào ngân hàng (`is_in_bank=True`) để Validation
    Engine so trùng lặp bằng cosine cho các lần sinh sau (PRD 11). Không làm gì nếu
    chưa cấu hình AI — `Question.embedding` giữ NULL, cosine check tự bỏ qua câu đó."""
    client = _active_embedding_client(db)
    if client is None or not questions:
        return
    vectors = client.embed_batch([q.prompt_text for q in questions])
    for question, vector in zip(questions, vectors):
        question.embedding = vector


def _build_context(db: Session, exam: Exam, grade: Grade) -> GenerationContext:
    unit_title = None
    unit_order_no = None
    if exam.unit_id:
        unit = db.get(Unit, exam.unit_id)
        if unit:
            unit_title = unit.title
            unit_order_no = unit.order_no
    exam_level = db.get(ProficiencyLevel, exam.level_id)
    return GenerationContext(
        grade_number=grade.number,
        school_stage_code=grade.school_stage.code if grade.school_stage else "",
        exam_level_code=exam_level.code if exam_level else "",
        unit_title=unit_title,
        unit_order_no=unit_order_no,
        unit_id=exam.unit_id,
        grammar_point_ids=[sel.grammar_point_id for sel in exam.grammar_selections],
    )


def _effective_level(db: Session, exam: Exam, block: ExamBlock) -> ProficiencyLevel:
    if block.level_override_id:
        override = db.get(ProficiencyLevel, block.level_override_id)
        if override:
            return override
    return db.get(ProficiencyLevel, exam.level_id)


# Số câu cho MỖI họ từ ở Phần A word form. Đề thật gom 5-6 câu cho một họ từ để học
# sinh luyện đủ các từ loại của từ đó; xin cả block trong 1 lần gọi thì model gần như
# luôn cho mỗi câu một họ từ khác nhau (đề thật 24/08/2026 — 5 câu ra 5 họ từ).
WORD_FORM_QUESTIONS_PER_FAMILY = 5
WORD_FORM_MIN_PER_FAMILY = 3
WORD_FORM_MAX_PER_FAMILY = 10
# Giáo viên chỉnh được số câu mỗi họ từ; con số đi kèm prompt_override của Phần con
# (nơi đã ghim sẵn "kiểu (A)") thay vì thêm cột DB — xem ExamBuilderPage.tsx.
_PER_FAMILY_RE = re.compile(r"mỗi họ từ\s+(\d+)\s*câu", re.IGNORECASE)


def word_form_questions_per_family(prompt_override: str | None) -> int:
    match = _PER_FAMILY_RE.search(prompt_override or "")
    if match is None:
        return WORD_FORM_QUESTIONS_PER_FAMILY
    value = int(match.group(1))
    return max(WORD_FORM_MIN_PER_FAMILY, min(WORD_FORM_MAX_PER_FAMILY, value))
_MIN_AGREEING_FAMILY_LABELS = 3  # >= 3/5 câu ghi cùng chuỗi -> coi là chuỗi của cả nhóm


def word_form_family_count(question_count: int, per_family: int = WORD_FORM_QUESTIONS_PER_FAMILY) -> int:
    """Số họ từ suy từ số câu của Phần con (giáo viên chọn số họ từ × số câu mỗi họ từ)."""
    return max(1, round(question_count / max(1, per_family)))


_MAX_FAMILY_ATTEMPTS = 3  # tối đa 3 hạt giống cho một họ từ — chặn vòng lặp + giới hạn chi phí
_MIN_SEED_WORD_LEN = 4  # từ quá ngắn (a/the/go) hiếm khi có họ từ đủ 5 dạng


_PINNED_FAMILY_RE = re.compile(r"dùng ĐÚNG họ từ sau:\s*(.+?)\.", re.IGNORECASE)


def _pinned_family(prompt_override: str | None) -> str | None:
    match = _PINNED_FAMILY_RE.search(prompt_override or "")
    return match.group(1).strip() if match else None


def _distinct_families(drafts: list[QuestionDraft]) -> list[str]:
    """Các chuỗi họ từ khác nhau trong danh sách, giữ nguyên thứ tự xuất hiện."""
    families: list[str] = []
    for draft in drafts:
        family = word_family_label(draft.target_knowledge)
        if family and family not in families:
            families.append(family)
    return families


def _batch_family(drafts: list[QuestionDraft]) -> str | None:
    """Chuỗi họ từ chung của cả nhóm, None nếu không câu nào ghi được chuỗi hợp lệ."""
    for draft in drafts:
        family = word_family_label(draft.target_knowledge)
        if family:
            return family
    return None


_RETRIEVAL_SAMPLE_WORDS = 5


def _sample_words(words: list[str]) -> list[str]:
    """Vài từ của Unit làm từ khoá truy vấn. Ít từ thôi: `plainto_tsquery` nối các từ
    bằng AND nên câu truy vấn càng dài càng dễ không khớp đoạn nào."""
    if len(words) <= _RETRIEVAL_SAMPLE_WORDS:
        return list(words)
    return random.sample(words, _RETRIEVAL_SAMPLE_WORDS)


def _retrieval_query(context: GenerationContext, *terms: str | None) -> str:
    """Câu truy vấn RAG: từ khoá nội dung TIẾNG ANH (từ hạt giống, các từ trong họ từ)
    cộng tên Unit — không phải đoạn chỉ thị tiếng Việt dài mà pipeline gửi cho model."""
    parts = [t.strip() for t in terms if t and t.strip()]
    if context.unit_title:
        parts.append(context.unit_title)
    return " ".join(parts) or "kiến thức bài học"


def _family_prompt_override(
    base: str | None, seed: str | None, used: list[str], per_family: int = WORD_FORM_QUESTIONS_PER_FAMILY
) -> str:
    """Ghim họ từ cho MỘT lần gọi: ưu tiên từ hạt giống (chắc chắn khác nhau vì code
    chọn), kèm danh sách họ từ đã ra để phòng khi không có vốn từ Unit."""
    parts = [base or ""]
    parts.append(
        f" Cả {per_family} câu lần này dùng CHUNG đúng MỘT họ từ duy nhất "
        "(mọi câu ghi target_knowledge y hệt nhau)."
    )
    if seed:
        parts.append(
            f" BẮT BUỘC lấy họ từ của từ '{seed}' (chuỗi họ từ phải chứa chính từ này). "
            "Nếu từ này không có họ từ đủ dùng thì chọn từ khác trong tài liệu nguồn, "
            "nhưng TUYỆT ĐỐI không lặp lại họ từ đã ra."
        )
    if used:
        parts.append(" Các họ từ ĐÃ RA (cấm dùng lại): " + "; ".join(used) + ".")
    return "".join(parts).strip()


def _unify_family_label(drafts: list[QuestionDraft]) -> None:
    """Cả nhóm đã được sinh cho CÙNG một họ từ, nhưng model hay ghi chuỗi lệch nhau chút
    (thiếu 1 thành phần, đổi thứ tự) khiến renderer tách thành nhiều dòng ❖. Nếu đa số
    câu đồng ý một chuỗi thì gán chuỗi đó cho cả nhóm; không đủ đồng thuận thì để
    nguyên để cảnh báo còn nhìn thấy được."""
    labels = [word_family_label(d.target_knowledge) for d in drafts]
    valid = [lb for lb in labels if lb]
    if not valid:
        return
    best = max(set(valid), key=valid.count)
    if valid.count(best) < min(_MIN_AGREEING_FAMILY_LABELS, len(drafts)):
        return
    for draft in drafts:
        draft.target_knowledge = best


def _strip_word_form_extras(drafts: list[QuestionDraft], *, kind: str | None) -> None:
    """Dọn hai lỗi model lặp đi lặp lại ở dạng word form, sửa bằng code thay vì tin prompt:

    - Lựa chọn A/B/C/D: word form là điền từ, không phải trắc nghiệm (đề thật 24/08/2026
      in ra "A. togetherness B. togetherly ..." vô nghĩa dưới mỗi câu).
    - Phần A bị thêm "(together)" ở cuối câu: họ từ đã in ở dòng ❖ nên từ gốc là thừa
      và lộ luôn đáp án.
    """
    for draft in drafts:
        draft.options = None
        # Đưa từ gốc về cuối câu TRƯỚC đã, rồi mới cắt — model đặt ngoặc giữa câu thì
        # split_bracket_root không thấy gì để cắt, và bộ kiểm cũng không thấy gì để kiểm.
        draft.prompt_text = normalize_bracket_root(draft.prompt_text)
        if kind == "family":
            sentence, root = split_bracket_root(draft.prompt_text)
            if root:
                draft.prompt_text = sentence


def _bracket_prompt_override(base: str | None, family: str, count: int) -> str:
    """Ghim MỘT họ từ (lấy từ Phần A) cho một lần gọi Phần B."""
    return (
        f"{base or ''}"
        f" Cả {count} câu lần này dùng ĐÚNG họ từ sau: {family}."
        " Từ đặt trong ngoặc ở cuối câu PHẢI là một thành viên của chính họ từ đó, và PHẢI"
        " KHÁC TỪ LOẠI với dạng cần điền — ví dụ 'I want to become a ______ (science).'"
        " cho từ gốc 'science' (n) để điền 'scientist' (n, người)."
        " Mỗi câu chọn một cặp (từ gốc → dạng cần điền) KHÁC nhau trong họ từ này,"
        " và câu phải có nghĩa tự nhiên, không ghép bừa từ vào chỗ trống."
    ).strip()


def _word_form_bracket_drafts(
    provider: AIProvider,
    spec: BlockSpec,
    context: GenerationContext,
    families: list[str],
) -> list[QuestionDraft]:
    """Phần B là bài TỔNG HỢP của Phần A: từ gốc trong ngoặc lấy từ đúng những họ từ đã
    ra ở Phần A, mỗi câu một từ loại khác với đáp án.

    Gọi riêng theo từng họ từ để các họ từ trải đều. Xin cả block trong một lần gọi thì
    model dồn hết vào một từ — đề thật 24/08/2026 có 7/15 câu cùng '(benefit)', kèm
    những câu ghép bừa kiểu 'To keep fit, you should ______ junk food. (benefit)'.
    """
    total = spec.question_count
    per_family = -(-total // len(families))  # chia đều, làm tròn lên
    drafts: list[QuestionDraft] = []
    for family in families:
        remaining = total - len(drafts)
        if remaining <= 0:
            break
        count = min(per_family, remaining)
        sub = replace(
            spec,
            question_count=count,
            prompt_override=_bracket_prompt_override(spec.prompt_override, family, count),
            # Truy vấn theo CÁC TỪ trong họ từ, không theo cả đoạn chỉ thị tiếng Việt.
            retrieval_query=_retrieval_query(context, " ".join(sorted(word_family_members(family)))),
        )
        batch = provider.generate(sub, context)[:count]
        _strip_word_form_extras(batch, kind="bracket")
        batch = _auto_fix_pronunciation_drafts(provider, sub, context, batch)
        _strip_word_form_extras(batch, kind="bracket")
        drafts.extend(batch)
    return drafts[:total]


def _word_form_family_drafts(
    provider: AIProvider,
    spec: BlockSpec,
    context: GenerationContext,
    unit_words: list[str],
) -> list[QuestionDraft]:
    """Phần A word form: gọi provider RIÊNG cho từng họ từ, mỗi lần xin đúng
    WORD_FORM_QUESTIONS_PER_FAMILY câu dùng chung 1 họ từ.

    Bảo đảm mỗi lần một họ từ KHÁC bằng code chứ không bằng lời dặn: mỗi lần gọi ghim
    một TỪ HẠT GIỐNG lấy từ vốn từ của Unit. Đề thật 24/08/2026 cho thấy chỉ dặn
    "không dùng lại các họ từ đã ra" thì model bỏ ngoài tai — 3 lần gọi ra y hệt
    'collect (v) → collection (n) → ...', dồn thành 15 câu chung một dòng ❖.
    Không có vốn từ (Unit chưa nạp tài liệu) thì quay về cách dặn + thử lại.
    """
    per_family = word_form_questions_per_family(spec.prompt_override)
    drafts: list[QuestionDraft] = []
    used: list[str] = []
    seeds = [w for w in unit_words if len(w) >= _MIN_SEED_WORD_LEN]
    seed_pos = 0

    for _ in range(word_form_family_count(spec.question_count, per_family)):
        batch: list[QuestionDraft] = []
        for _attempt in range(_MAX_FAMILY_ATTEMPTS):
            seed = seeds[seed_pos] if seed_pos < len(seeds) else None
            seed_pos += 1
            sub = replace(
                spec,
                question_count=per_family,
                prompt_override=_family_prompt_override(spec.prompt_override, seed, used, per_family),
                retrieval_query=_retrieval_query(context, seed),
            )
            batch = provider.generate(sub, context)[:per_family]
            _strip_word_form_extras(batch, kind="family")
            batch = _auto_fix_pronunciation_drafts(provider, sub, context, batch)
            _strip_word_form_extras(batch, kind="family")
            _unify_family_label(batch)
            family = _batch_family(batch)
            if family is not None and family not in used:
                used.append(family)
                break
            # Trùng họ từ đã ra (hoặc không nhận ra họ từ) -> thử lại với hạt giống kế tiếp.
        drafts.extend(batch)
    return drafts

def generate_block_questions(db: Session, exam: Exam, block: ExamBlock) -> list[Question]:
    """Xoá toàn bộ câu chưa khóa của block rồi sinh mới đủ question_count.

    Khi block có phần con (`ExamBlockPart`), gọi provider riêng cho từng phần với
    `question_count`/`prompt_override` của phần đó, gắn `part_id` tương ứng lên câu
    hỏi tạo ra. `order_no` vẫn là một dãy chạy liên tục xuyên suốt cả block, không
    reset theo phần con — việc nhóm hiển thị dựa hoàn toàn vào `part_id`
    (xem docs/superpowers/specs/2026-07-20-block-sub-parts-design.md)."""
    exercise_type = db.get(ExerciseType, block.exercise_type_id)
    grade = db.get(Grade, exam.grade_id)
    exam_level = db.get(ProficiencyLevel, exam.level_id)
    effective_level = _effective_level(db, exam, block)
    context = _build_context(db, exam, grade)
    provider = get_active_provider(db)
    embedding_client = _active_embedding_client(db)
    # Vốn từ của Unit để bộ dựng phát âm ưu tiên dùng từ trong bài (chỉ tra khi cần).
    unit_words = (
        unit_vocabulary_words(db, exam.unit_id)
        if exercise_type.code in _PRONUNCIATION_TYPES or exercise_type.code == "word_form"
        else []
    )
    # Nhóm 4 từ lấy nguyên từ đề thật của Unit — nguyên liệu tốt hơn bộ từ viết tay.
    exam_lines = (
        exam_examples(db, unit_id=exam.unit_id, exercise_type_code=exercise_type.code, limit=400)
        if exercise_type.code in _PRONUNCIATION_TYPES
        else []
    )

    for existing in list(block.questions):
        if not existing.is_locked:
            db.delete(existing)
    db.flush()

    parts = sorted(block.parts, key=lambda p: p.order_no)
    groups: list[ExamBlockPart | None] = list(parts) if parts else [None]

    # Họ từ Phần A, chuyển sang Phần B — các phần con sinh theo thứ tự order_no nên
    # Phần A luôn xong trước.
    word_form_families: list[str] = []
    # Chặn trùng câu phát âm/trọng âm XUYÊN các phần con của cùng khối (xem
    # _deterministic_pronunciation_drafts).
    used_pronunciation: set[frozenset[str]] = set()
    locked_orders = {q.order_no for q in block.questions if q.is_locked}
    order_no = 0
    created: list[Question] = []
    for part in groups:
        count = part.question_count if part else block.question_count
        prompt_override = (part.prompt_override if part and part.prompt_override else block.prompt_override)
        # Phần con được phép khác dạng bài với khối cha (đề thật gộp trọng âm vào mục
        # PRONUNCIATION) — mọi thứ từ đây phải theo dạng bài CỦA PHẦN CON.
        part_type = part.exercise_type if part and part.exercise_type_id else exercise_type
        spec = BlockSpec(
            exercise_type_code=part_type.code,
            question_count=count,
            level_code=effective_level.code,
            passage_word_target=block.passage_word_target,
            prompt_override=prompt_override,
            # Phát âm/trọng âm giờ do AI sinh nên phải tìm ĐÚNG đoạn từ vựng của Unit.
            # Bỏ trống thì openai_provider lấy prompt_override làm câu truy vấn, mà đó
            # là chỉ thị tiếng Việt ("Chỉ dùng kiểu (1) đuôi -s/-es...") — FTS trượt
            # sạch, vector lệch hẳn (xem BlockSpec.retrieval_query). Lấy ngẫu nhiên vài
            # từ trong bài để mỗi lần sinh bốc trúng đoạn khác nhau, đề đỡ rập khuôn.
            retrieval_query=(
                _retrieval_query(context, " ".join(_sample_words(unit_words)))
                if part_type.code in _PRONUNCIATION_TYPES
                else None
            ),
        )
        word_form_kind = (
            detect_word_form_kind(prompt_override) if part_type.code == "word_form" else None
        )
        part_exam_lines = (
            exam_examples(db, unit_id=exam.unit_id, exercise_type_code=part_type.code, limit=400)
            if part_type.code in _PRONUNCIATION_TYPES
            else exam_lines
        )
        if part_type.code in _PRONUNCIATION_TYPES:
            drafts = _pronunciation_drafts(
                provider, spec, context, unit_words, part_exam_lines, used_pronunciation
            )
        elif word_form_kind == "family":
            # Phần A word form: gọi từng họ từ một (xem _word_form_family_drafts) nên số câu
            # đã đúng theo thiết kế, không cắt theo count nữa.
            drafts = _word_form_family_drafts(provider, spec, context, unit_words)
            # Nhớ lại để Phần B ôn lại đúng những họ từ này (xem _word_form_bracket_drafts).
            word_form_families = _distinct_families(drafts)
        elif word_form_kind == "bracket" and word_form_families:
            drafts = _word_form_bracket_drafts(provider, spec, context, word_form_families)
        else:
            drafts = provider.generate(spec, context)
            drafts = _auto_fix_pronunciation_drafts(provider, spec, context, drafts)
            # Model đôi khi trả nhiều/ít hơn số câu yêu cầu dù prompt đã ghi rõ (đề thật
            # 07/08/2026: xin 8 câu, trả 9) -> cắt đúng số câu để block không lệch.
            drafts = drafts[:count]
            if part_type.code == "word_form":
                _strip_word_form_extras(drafts, kind=word_form_kind)
        draft_embeddings = _embed_drafts(embedding_client, drafts)

        for draft, draft_embedding in zip(drafts, draft_embeddings):
            order_no += 1
            while order_no in locked_orders:
                order_no += 1
            level = db.scalar(select(ProficiencyLevel).where(ProficiencyLevel.code == draft.level_code)) or exam_level
            warnings = validate_draft(
                db,
                draft,
                exercise_type=part_type,
                grade_number=grade.number,
                school_stage_id=grade.school_stage_id,
                exam_level_rank=exam_level.rank,
                draft_embedding=draft_embedding,
            )
            question = Question(
                block_id=block.id,
                part_id=part.id if part else None,
                order_no=order_no,
                prompt_text=draft.prompt_text,
                passage_text=draft.passage_text,
                options=draft.options,
                answer_text=draft.answer_text,
                explanation=draft.explanation,
                target_knowledge=draft.target_knowledge,
                level_id=level.id,
                source_ref=draft.source_ref,
                warnings=warnings,
            )
            db.add(question)
            created.append(question)
    return created


def regenerate_question(db: Session, exam: Exam, block: ExamBlock, question: Question) -> None:
    exercise_type = db.get(ExerciseType, block.exercise_type_id)
    grade = db.get(Grade, exam.grade_id)
    exam_level = db.get(ProficiencyLevel, exam.level_id)
    effective_level = _effective_level(db, exam, block)
    context = _build_context(db, exam, grade)
    prompt_override = question.part.prompt_override if question.part and question.part.prompt_override else block.prompt_override
    spec = BlockSpec(
        exercise_type_code=exercise_type.code,
        question_count=1,
        level_code=effective_level.code,
        passage_word_target=block.passage_word_target,
        prompt_override=prompt_override,
    )
    draft = get_active_provider(db).regenerate_one(spec, context, exclude_prompt=question.prompt_text)
    draft_embedding = _embed_drafts(_active_embedding_client(db), [draft])[0]
    level = db.scalar(select(ProficiencyLevel).where(ProficiencyLevel.code == draft.level_code)) or exam_level
    warnings = validate_draft(
        db,
        draft,
        exercise_type=exercise_type,
        grade_number=grade.number,
        school_stage_id=grade.school_stage_id,
        exam_level_rank=exam_level.rank,
        draft_embedding=draft_embedding,
    )

    question.prompt_text = draft.prompt_text
    question.passage_text = draft.passage_text
    question.options = draft.options
    question.answer_text = draft.answer_text
    question.explanation = draft.explanation
    question.target_knowledge = draft.target_knowledge
    question.level_id = level.id
    question.source_ref = draft.source_ref
    question.warnings = warnings
    question.is_approved = False


def _shuffle_keeping_family_groups(questions: list, rng: random.Random) -> list[str]:
    """Đảo thứ tự câu NHƯNG giữ nguyên khối các câu cùng họ từ đứng liền nhau.

    Đảo thẳng cả phần sẽ xé nhóm: đề thật 24/08/2026 in ra "❖ energy (n) → ..." 4 lần
    xen kẽ với "❖ Japanese (adj) → ..." thay vì 3 khối gọn. Bên trong một họ từ vẫn đảo,
    để đáp án không chạy theo thứ tự v → n → adj → adv đoán được.

    Câu không thuộc họ từ nào (mọi dạng bài khác) thành nhóm 1 câu — đảo tự do như cũ.
    """
    groups: list[tuple[str | None, list]] = []
    for question in questions:
        family = word_family_label(question.target_knowledge)
        if family is not None and groups and groups[-1][0] == family:
            groups[-1][1].append(question)
        else:
            groups.append((family, [question]))
    rng.shuffle(groups)
    ids: list[str] = []
    for _family, items in groups:
        rng.shuffle(items)
        ids.extend(str(q.id) for q in items)
    return ids


def shuffle_variant(exam: Exam, seed: int) -> dict:
    """Đảo thứ tự câu trong mỗi block theo shuffle_questions của block.
    Không tách nhóm câu dùng chung ngữ cảnh (đoạn đọc) — đảo trong phạm vi 1 block (PRD 13).

    Block có phần con: đảo riêng trong từng phần rồi nối theo đúng thứ tự phần con,
    không trộn câu giữa các phần — giữ nguyên nhóm sư phạm của đề thật."""
    rng = random.Random(seed)
    order: dict[str, list[str]] = {}
    for block in exam.blocks:
        parts = sorted(block.parts, key=lambda p: p.order_no)
        if parts:
            question_ids: list[str] = []
            for part in parts:
                part_questions = [q for q in sorted(block.questions, key=lambda q: q.order_no) if q.part_id == part.id]
                if block.shuffle_questions:
                    question_ids.extend(_shuffle_keeping_family_groups(part_questions, rng))
                else:
                    question_ids.extend(str(q.id) for q in part_questions)
            unassigned = [str(q.id) for q in sorted(block.questions, key=lambda q: q.order_no) if q.part_id is None]
            question_ids.extend(unassigned)
        else:
            block_questions = sorted(block.questions, key=lambda q: q.order_no)
            question_ids = (
                _shuffle_keeping_family_groups(block_questions, rng)
                if block.shuffle_questions
                else [str(q.id) for q in block_questions]
            )
        order[str(block.id)] = question_ids
    return order
