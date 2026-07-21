"""Hướng dẫn sinh câu hỏi theo từng dạng bài (10 dạng, PRD mục 7) dùng cho
`OpenAIProvider`. Một dict thay vì 1 file/dạng bài — nội dung mỗi dạng chỉ vài câu,
tách file riêng chỉ thêm phiền mà không ích lợi ở quy mô này. Đổi nội dung hướng
dẫn thì tăng `PROMPT_VERSION` (ghi vào `GenerationLog.prompt_version`) để phân biệt
được câu hỏi sinh ra từ phiên bản prompt nào khi debug chất lượng.
"""

PROMPT_VERSION = "v4"

EXERCISE_INSTRUCTIONS: dict[str, str] = {
    "pronunciation": (
        "Dạng chọn từ có phần phát âm khác 3 từ còn lại. QUAN TRỌNG VỀ SỐ LƯỢNG: mỗi câu "
        "ĐỘC LẬP tự chọn 1 trong 3 kiểu liệt kê bên dưới — KHÔNG phải 'mỗi kiểu đúng 1 câu'. "
        "Được lặp lại cùng 1 kiểu ở nhiều câu liên tiếp, không bắt buộc dùng đủ cả 3 kiểu. "
        "Số câu trả về PHẢI đúng bằng số câu yêu cầu (trừ khi nguồn thật sự không đủ).\n"
        "3 KIỂU thường gặp — chọn kiểu phù hợp nhất với từ vựng có sẵn trong nguồn cho từng câu:\n"
        "(1) Đuôi -s/-es: 4 từ đều tận cùng -s/-es nhưng đọc khác nhau /s/, /z/ hoặc /ɪz/ tùy "
        "âm đứng trước — vd 'look<u>s</u>' /s/, 'game<u>s</u>' /z/, 'dress<u>es</u>' /ɪz/. "
        "CHỈ bọc đúng chữ cái 's' hoặc 'es' ở cuối cùng — KHÔNG bọc thêm chữ nào trước đó "
        "(SAI: 'dre<u>sses</u>'; ĐÚNG: 'dress<u>es</u>').\n"
        "(2) Đuôi -ed: 4 từ đều tận cùng -ed nhưng đọc khác nhau /t/, /d/ hoặc /ɪd/ tùy âm "
        "đứng trước — vd 'watch<u>ed</u>' /t/, 'lov<u>ed</u>' /d/, 'want<u>ed</u>' /ɪd/. CHỈ "
        "bọc đúng 2 chữ 'ed' ở cuối cùng, không bọc thêm chữ nào trước đó.\n"
        "(3) So sánh âm chung không phải đuôi -s/-es hay -ed: 4 từ đơn cùng chứa 1 cụm chữ "
        "cái giống nhau ở vị trí tương ứng, 3 từ đọc cụm đó giống nhau, đúng 1 từ khác — vd "
        "'cl<u>ea</u>n', 'br<u>ea</u>d', 't<u>ea</u>ch', 't<u>ea</u>m' (đáp án 'bread' vì "
        "phát âm /e/, ba từ còn lại /iː/).\n"
        "BẮT BUỘC dù chọn kiểu nào: 4 lựa chọn phải là 4 TỪ ĐƠN (không phải cụm từ/câu), có "
        "điểm chung về chính tả để so sánh được — KHÔNG được chọn 4 từ/cụm từ không liên "
        "quan nhau (vd không được so sánh 'gardening' với 'free time' — không có điểm chung "
        "để so sánh phát âm). Giải thích nêu rõ ký hiệu IPA khác biệt."
    ),
    "stress": (
        "Dạng chọn từ có trọng âm khác 3 từ còn lại. BẮT BUỘC: 4 lựa chọn phải là 4 TỪ ĐƠN "
        "(không phải cụm từ/câu) có CÙNG số âm tiết — 3 từ trọng âm rơi vào cùng vị trí âm "
        "tiết, đúng 1 từ trọng âm rơi vào vị trí khác (đó là đáp án đúng). Trong mỗi "
        "option.text, bọc chính xác âm tiết mang trọng âm bằng <u>...</u>. Ví dụ 4 lựa chọn "
        "hợp lệ (2 âm tiết): '<u>han</u>dsome', '<u>tra</u>vel', 'be<u>gin</u>', '<u>mod</u>ern' "
        "— đáp án 'begin' vì trọng âm rơi vào âm tiết 2, ba từ còn lại rơi vào âm tiết 1. "
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
        f"Mảng questions PHẢI có đúng {question_count} phần tử — nếu hướng dẫn dạng bài bên dưới liệt kê "
        "nhiều kiểu/cách làm khác nhau, đó là các lựa chọn cho TỪNG câu chọn 1 trong số đó, KHÔNG phải yêu "
        "cầu mỗi kiểu đúng 1 câu (được lặp lại kiểu, không cần dùng đủ mọi kiểu). "
        f"{instruction} "
        "CHỈ dùng kiến thức có trong tài liệu nguồn được cung cấp bên dưới — không tự bịa từ vựng/ngữ pháp "
        "ngoài phạm vi đó. Nếu tài liệu nguồn không đủ để sinh đúng số câu yêu cầu, vẫn sinh tối đa có thể "
        "và ghi rõ lý do vào insufficient_source_warning; nếu đủ thì để insufficient_source_warning là null. "
        "source_chunk_ids của mỗi câu phải là ID (trong ngoặc vuông trước mỗi đoạn nguồn) đã thực sự dùng. "
        "Khi cần đánh dấu phần gạch chân trong 1 lựa chọn (bắt buộc với dạng phát âm/trọng âm, xem hướng dẫn "
        "dạng bài ở trên), bọc đúng phần đó bằng <u>...</u> ngay trong option.text — hệ thống sẽ tự render "
        "thành gạch chân thật khi xuất file, không cần và không được dùng ký hiệu nào khác (không markdown **, "
        "không dấu ngoặc kép quanh phần gạch chân)."
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
