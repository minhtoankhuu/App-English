"""Điều phối sinh câu hỏi: gọi AIProvider rồi chạy Validation Engine trên từng câu,
lưu kết quả vào DB. Tách khỏi router để router chỉ lo HTTP, còn logic nghiệp vụ
nằm ở đây và test được độc lập."""

import random

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.academic import Grade, ProficiencyLevel, Unit
from app.models.ai_config import AIProviderConfig
from app.models.exam import Exam, ExamBlock, ExamBlockPart, Question
from app.models.exercise import ExerciseType
from app.services.ai_provider import AIGenerationError, AIProvider, BlockSpec, GenerationContext, QuestionDraft
from app.services.ai_provider_factory import get_active_provider
from app.services.crypto import decrypt_api_key
from app.services.openai_embedding import OpenAIEmbeddingClient
from app.services.pronunciation_builder import build_pronunciation_questions
from app.services.pronunciation_check import check_pronunciation_options
from app.services.unit_vocabulary import unit_vocabulary_words
from app.services.validation import validate_draft

# Dạng phát âm/trọng âm: kiểm chứng thực tế cho thấy LLM gần như không sinh đúng
# (gpt-4o-mini 0/8 với -s/-es), re-roll cũng vô ích (báo cáo 02/08/2026). Nên DỰNG
# BẰNG CODE (pronunciation_builder) — luôn đúng quy tắc 3 giống - 1 khác — thay vì gọi
# LLM. Chỉ khi builder không dựng được mới rơi về LLM + auto-fix như trước (phòng hờ).
_PRONUNCIATION_TYPES = {"pronunciation", "stress"}
_MAX_PRONUNCIATION_REGEN = 2  # tối đa 2 lần sinh lại/câu — chặn vòng lặp + giới hạn chi phí


def _detect_pronunciation_kind(prompt_override: str | None) -> str | None:
    """Suy 'kiểu' bài phát âm từ prompt_override của Phần con (preset ở ExamBuilder ghi
    'kiểu (1)/(2)/(3)'). None = không rõ kiểu -> caller dựng bộ trộn."""
    text = (prompt_override or "").lower()
    # Ưu tiên mã kiểu tường minh "(1)/(2)/(3)" TRƯỚC khi dò từ khoá: preset kiểu (3) mô
    # tả là "so sánh âm chung trong từ (KHÔNG PHẢI đuôi -s/-es hay -ed)" — có chứa
    # "-s/-es" trong mệnh đề loại trừ, nên dò từ khoá trước sẽ nhận nhầm thành kiểu (1),
    # khiến Phần con thứ 3 ra đề trùng hệt Phần A (báo cáo giáo viên 07/08/2026).
    for marker, kind in (("(3)", "vowel"), ("(2)", "ed"), ("(1)", "s")):
        if marker in text:
            return kind
    # Không có mã kiểu (giáo viên tự nhập) -> dò từ khoá, xét "âm trong từ" trước vì mô
    # tả kiểu này thường nhắc lại tên 2 kiểu đuôi kia để loại trừ.
    if "âm chung" in text or "âm trong từ" in text:
        return "vowel"
    if "-ed" in text or "đuôi -ed" in text:
        return "ed"
    if "-s/-es" in text or "đuôi -s" in text:
        return "s"
    return None


def _deterministic_pronunciation_drafts(
    spec: BlockSpec, unit_words: list[str] | None = None
) -> list[QuestionDraft] | None:
    """Dựng câu phát âm/trọng âm bằng code, ưu tiên vốn từ của Unit (`unit_words`).
    None = không thuộc dạng này hoặc dựng không đủ câu -> caller rơi về LLM."""
    if spec.exercise_type_code not in _PRONUNCIATION_TYPES:
        return None
    if spec.exercise_type_code == "stress":
        drafts = build_pronunciation_questions("stress", spec.question_count, unit_words=unit_words)
    else:
        kind = _detect_pronunciation_kind(spec.prompt_override)
        if kind is not None:
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
    if not drafts:
        return None
    for draft in drafts:
        draft.level_code = spec.level_code
    return drafts


def _pronunciation_warnings(draft: QuestionDraft, exercise_type_code: str) -> list[str]:
    if exercise_type_code not in _PRONUNCIATION_TYPES or not draft.options:
        return []
    return check_pronunciation_options(
        [opt.get("text", "") for opt in draft.options],
        is_pronunciation=exercise_type_code == "pronunciation",
    )


def _auto_fix_pronunciation_drafts(
    provider: AIProvider, spec: BlockSpec, context: GenerationContext, drafts: list[QuestionDraft]
) -> list[QuestionDraft]:
    """Với dạng phát âm/trọng âm: câu nào fail kiểm tra bằng code thì sinh lại (kèm
    cảnh báo làm feedback), tối đa _MAX_PRONUNCIATION_REGEN lần, giữ bản ít lỗi nhất.
    Câu đạt hoặc dạng khác giữ nguyên. Không finalize/chặn — vẫn để Validation Engine
    gắn cảnh báo lên câu cuối cùng nếu vẫn còn lỗi."""
    if spec.exercise_type_code not in _PRONUNCIATION_TYPES:
        return drafts
    fixed: list[QuestionDraft] = []
    for draft in drafts:
        warnings = _pronunciation_warnings(draft, spec.exercise_type_code)
        attempts = 0
        while warnings and attempts < _MAX_PRONUNCIATION_REGEN:
            attempts += 1
            try:
                candidate = provider.regenerate_one(
                    spec, context, exclude_prompt=draft.prompt_text, feedback="; ".join(warnings)
                )
            except AIGenerationError:
                break
            candidate_warnings = _pronunciation_warnings(candidate, spec.exercise_type_code)
            if len(candidate_warnings) < len(warnings):
                draft, warnings = candidate, candidate_warnings
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
        if exercise_type.code in _PRONUNCIATION_TYPES
        else []
    )

    for existing in list(block.questions):
        if not existing.is_locked:
            db.delete(existing)
    db.flush()

    parts = sorted(block.parts, key=lambda p: p.order_no)
    groups: list[ExamBlockPart | None] = list(parts) if parts else [None]

    locked_orders = {q.order_no for q in block.questions if q.is_locked}
    order_no = 0
    created: list[Question] = []
    for part in groups:
        count = part.question_count if part else block.question_count
        prompt_override = (part.prompt_override if part and part.prompt_override else block.prompt_override)
        spec = BlockSpec(
            exercise_type_code=exercise_type.code,
            question_count=count,
            level_code=effective_level.code,
            passage_word_target=block.passage_word_target,
            prompt_override=prompt_override,
        )
        drafts = _deterministic_pronunciation_drafts(spec, unit_words)
        if drafts is None:
            drafts = provider.generate(spec, context)
            drafts = _auto_fix_pronunciation_drafts(provider, spec, context, drafts)
            # Model đôi khi trả nhiều/ít hơn số câu yêu cầu dù prompt đã ghi rõ (đề thật
            # 07/08/2026: xin 8 câu, trả 9) -> cắt đúng số câu để block không lệch.
            drafts = drafts[:count]
        draft_embeddings = _embed_drafts(embedding_client, drafts)

        for draft, draft_embedding in zip(drafts, draft_embeddings):
            order_no += 1
            while order_no in locked_orders:
                order_no += 1
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
                part_ids = [str(q.id) for q in sorted(block.questions, key=lambda q: q.order_no) if q.part_id == part.id]
                if block.shuffle_questions:
                    rng.shuffle(part_ids)
                question_ids.extend(part_ids)
            unassigned = [str(q.id) for q in sorted(block.questions, key=lambda q: q.order_no) if q.part_id is None]
            question_ids.extend(unassigned)
        else:
            question_ids = [str(q.id) for q in sorted(block.questions, key=lambda q: q.order_no)]
            if block.shuffle_questions:
                rng.shuffle(question_ids)
        order[str(block.id)] = question_ids
    return order
