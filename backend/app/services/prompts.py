"""Hướng dẫn sinh câu hỏi theo từng dạng bài (10 dạng, PRD mục 7) dùng cho
`OpenAIProvider`. Một dict thay vì 1 file/dạng bài — nội dung mỗi dạng chỉ vài câu,
tách file riêng chỉ thêm phiền mà không ích lợi ở quy mô này. Đổi nội dung hướng
dẫn thì tăng `PROMPT_VERSION` (ghi vào `GenerationLog.prompt_version`) để phân biệt
được câu hỏi sinh ra từ phiên bản prompt nào khi debug chất lượng.
"""

PROMPT_VERSION = "v1"

EXERCISE_INSTRUCTIONS: dict[str, str] = {
    "pronunciation": (
        "Dạng chọn từ có phần gạch chân phát âm khác 3 từ còn lại. 4 lựa chọn A/B/C/D, "
        "đúng 1 đáp án đúng. Giải thích nêu rõ ký hiệu IPA khác biệt."
    ),
    "stress": (
        "Dạng chọn từ có trọng âm khác 3 từ còn lại. 4 lựa chọn A/B/C/D, đúng 1 đáp án đúng. "
        "Giải thích nêu rõ vị trí trọng âm (âm tiết thứ mấy) của từng từ."
    ),
    "multiple_choice": (
        "Trắc nghiệm 4 lựa chọn A/B/C/D, đúng 1 đáp án đúng, kiểm tra đúng target_knowledge "
        "(từ vựng/ngữ pháp) trong phạm vi nguồn được cung cấp."
    ),
    "reading_true_false": (
        "Cho 1 đoạn văn ngắn (passage_text) rồi hỏi True/False về 1 chi tiết trong đoạn. "
        "answer_text bắt đầu bằng 'True.' hoặc 'False.' kèm lý do ngắn."
    ),
    "sentence_rewrite": (
        "Cho 1 câu gốc, yêu cầu viết lại giữ nguyên nghĩa theo cấu trúc khác (ghi rõ trong "
        "prompt_text bằng '______' chỗ cần điền). answer_text là phần cần điền."
    ),
    "matching": (
        "Ghép cặp — prompt_text liệt kê 2 cột (đánh số/chữ cái), answer_text là bảng ánh xạ "
        "đúng (vd '1-C, 2-A, 3-D, 4-B')."
    ),
    "gap_fill": (
        "Điền từ vào chỗ trống trong 1 câu hoặc đoạn ngắn (đánh dấu '______'), answer_text là "
        "từ/cụm từ cần điền, đúng dạng ngữ pháp."
    ),
    "cloze_test": (
        "Đoạn văn có nhiều chỗ trống đánh số (1)/(2)/..., mỗi chỗ trống là 1 câu hỏi trắc "
        "nghiệm 4 lựa chọn A/B/C/D riêng — passage_text chứa đoạn văn đầy đủ với chỗ trống."
    ),
    "sign_reading": (
        "Đọc hiểu biển báo/thông báo ngắn — mô tả biển báo bằng văn bản trong passage_text "
        "(hệ thống hiện chưa có ảnh thật, xem PRD 23.3 #18), câu hỏi trắc nghiệm về ý nghĩa."
    ),
    "word_form": (
        "Cho 1 từ gốc (in hoa hoặc gạch chân trong câu), yêu cầu biến đổi đúng dạng từ loại "
        "(danh từ/động từ/tính từ/trạng từ) để điền vào chỗ trống. answer_text là từ đã biến đổi."
    ),
}


def build_system_prompt(exercise_type_code: str, question_count: int, level_code: str) -> str:
    instruction = EXERCISE_INSTRUCTIONS.get(
        exercise_type_code, "Sinh câu hỏi tiếng Anh phù hợp trình độ mục tiêu, bám sát tài liệu nguồn được cung cấp."
    )
    return (
        "Bạn là trợ lý tạo đề thi tiếng Anh THCS cho giáo viên Việt Nam. "
        f"Sinh đúng {question_count} câu hỏi dạng '{exercise_type_code}', trình độ mục tiêu {level_code}. "
        f"{instruction} "
        "CHỈ dùng kiến thức có trong tài liệu nguồn được cung cấp bên dưới — không tự bịa từ vựng/ngữ pháp "
        "ngoài phạm vi đó. Nếu tài liệu nguồn không đủ để sinh đúng số câu yêu cầu, vẫn sinh tối đa có thể "
        "và ghi rõ lý do vào insufficient_source_warning; nếu đủ thì để insufficient_source_warning là null. "
        "source_chunk_ids của mỗi câu phải là ID (trong ngoặc vuông trước mỗi đoạn nguồn) đã thực sự dùng."
    )


def build_user_prompt(
    unit_title: str | None,
    retrieved_chunks: list[tuple[str, str]],
    prompt_override: str | None,
    exclude_prompt: str | None,
) -> str:
    lines: list[str] = []
    if unit_title:
        lines.append(f"Chủ đề: {unit_title}")
    if not retrieved_chunks:
        lines.append("KHÔNG có tài liệu nguồn nào phù hợp phạm vi đề này.")
    else:
        lines.append("Tài liệu nguồn (mỗi đoạn có ID riêng để trích dẫn vào source_chunk_ids):")
        for chunk_id, text in retrieved_chunks:
            lines.append(f"[{chunk_id}] {text}")
    if prompt_override:
        lines.append(f"Yêu cầu thêm từ giáo viên: {prompt_override}")
    if exclude_prompt:
        lines.append(f"Tránh trùng nội dung với câu đã có: {exclude_prompt}")
    return "\n".join(lines)
