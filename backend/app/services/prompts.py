"""Hướng dẫn sinh câu hỏi theo từng dạng bài (10 dạng, PRD mục 7) dùng cho
`OpenAIProvider`. Một dict thay vì 1 file/dạng bài — nội dung mỗi dạng chỉ vài câu,
tách file riêng chỉ thêm phiền mà không ích lợi ở quy mô này. Đổi nội dung hướng
dẫn thì tăng `PROMPT_VERSION` (ghi vào `GenerationLog.prompt_version`) để phân biệt
được câu hỏi sinh ra từ phiên bản prompt nào khi debug chất lượng.
"""

PROMPT_VERSION = "v6"

EXERCISE_INSTRUCTIONS: dict[str, str] = {
    "pronunciation": (
        "Dạng chọn từ có phần phát âm khác 3 từ còn lại. Có 3 KIỂU — CHỌN ĐÚNG 1 KIỂU DUY "
        "NHẤT (kiểu phù hợp nhất với từ vựng có sẵn trong nguồn) rồi ÁP DỤNG ĐÚNG KIỂU ĐÓ CHO "
        "TOÀN BỘ số câu được yêu cầu trong lần sinh này — KHÔNG trộn nhiều kiểu khác nhau "
        "trong cùng 1 lần sinh (giáo viên muốn nhiều kiểu sẽ tự tạo nhiều lượt/phần riêng, "
        "không phải việc của bạn tự đổi kiểu giữa chừng):\n"
        "(1) Đuôi -s/-es: mọi từ đều tận cùng -s/-es nhưng đọc khác nhau /s/, /z/ hoặc /ɪz/ "
        "tùy âm đứng trước — vd 'look<u>s</u>' /s/, 'game<u>s</u>' /z/, 'dress<u>es</u>' /ɪz/. "
        "CHỈ bọc đúng chữ cái 's' hoặc 'es' VỐN ĐÃ CÓ SẴN ở cuối từ thật — KHÔNG bọc thêm chữ "
        "nào trước đó (SAI: 'dre<u>sses</u>'; ĐÚNG: 'dress<u>es</u>') và TUYỆT ĐỐI KHÔNG được "
        "thêm/nhân đôi ký tự 's' để tự tạo ra đuôi giả cho từ vốn đã đúng chính tả — nếu từ đã "
        "tận cùng bằng đúng 1 chữ 's' (vd 'stars', 'cars', 'bus', 'class', 'glass') thì dùng "
        "NGUYÊN từ đó, chỉ bọc <u> quanh chữ 's' có sẵn (SAI: 'star' → 'star<u>s</u>s' hay "
        "'starss'; ĐÚNG: 'star<u>s</u>'. SAI: 'bus' → 'bu<u>s</u>s'; ĐÚNG: 'bu<u>s</u>' — từ "
        "sau khi bỏ markup phải là 1 từ tiếng Anh có thật, đánh vần đúng).\n"
        "(2) Đuôi -ed: mọi từ đều tận cùng -ed nhưng đọc khác nhau /t/, /d/ hoặc /ɪd/ tùy âm "
        "đứng trước — vd 'watch<u>ed</u>' /t/, 'lov<u>ed</u>' /d/, 'want<u>ed</u>' /ɪd/. CHỈ "
        "bọc đúng 2 chữ 'ed' VỐN ĐÃ CÓ SẴN ở cuối từ thật, không bọc thêm chữ nào trước đó và "
        "cũng không được thêm/nhân đôi ký tự để tạo đuôi giả — áp dụng đúng quy tắc chính tả "
        "-ed như 'watch'+'ed'='watch<u>ed</u>', không phải chèn thêm chữ tùy tiện.\n"
        "(3) So sánh âm chung không phải đuôi -s/-es hay -ed: mọi từ cùng chứa 1 cụm chữ cái "
        "giống nhau ở vị trí tương ứng, phần lớn đọc cụm đó giống nhau, đúng 1 từ khác mỗi "
        "câu — vd 'cl<u>ea</u>n', 'br<u>ea</u>d', 't<u>ea</u>ch', 't<u>ea</u>m' (đáp án 'bread' "
        "vì phát âm /e/, ba từ còn lại /iː/).\n"
        "BẮT BUỘC với MỌI câu, không phân biệt kiểu nào:\n"
        "- 4 lựa chọn phải là 4 TỪ ĐƠN KHÁC NHAU (không trùng từ giữa các lựa chọn, không phải "
        "cụm từ/câu — KHÔNG được dùng như 'computer games'/'free time').\n"
        "- Mỗi lựa chọn sau khi bỏ markup <u>...</u> đi PHẢI là 1 từ tiếng Anh có thật, đánh "
        "vần đúng chính tả — không tự chế/nhân đôi ký tự để khớp đuôi.\n"
        "- CẢ 4 lựa chọn (kể cả các lựa chọn sai) đều phải bọc phần đang so sánh trong "
        "<u>...</u> — không được bỏ sót lựa chọn nào.\n"
        "Giải thích nêu rõ ký hiệu IPA khác biệt."
    ),
    "stress": (
        "Dạng chọn từ có trọng âm khác 3 từ còn lại. BẮT BUỘC: 4 lựa chọn phải là 4 TỪ ĐƠN "
        "KHÁC NHAU (không trùng từ, không phải cụm từ/câu) có CÙNG số âm tiết — 3 từ trọng âm "
        "rơi vào cùng vị trí âm tiết, đúng 1 từ trọng âm rơi vào vị trí khác (đó là đáp án "
        "đúng). CẢ 4 lựa chọn (kể cả lựa chọn sai) đều phải bọc âm tiết mang trọng âm trong "
        "<u>...</u> — không bỏ sót lựa chọn nào. Ví dụ 4 lựa chọn "
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
        f"Mảng questions PHẢI có đúng {question_count} phần tử. "
        f"{instruction} "
        "CHỈ dùng kiến thức có trong tài liệu nguồn được cung cấp bên dưới — không tự bịa từ vựng/ngữ pháp "
        "ngoài phạm vi đó. Nếu tài liệu nguồn không đủ để sinh đúng số câu yêu cầu, vẫn sinh tối đa có thể "
        "và ghi rõ lý do vào insufficient_source_warning; nếu đủ thì để insufficient_source_warning là null. "
        "source_chunk_ids của mỗi câu phải là ID (trong ngoặc vuông trước mỗi đoạn nguồn) đã thực sự dùng. "
        "Khi cần đánh dấu phần gạch chân trong 1 lựa chọn (bắt buộc với dạng phát âm/trọng âm, xem hướng dẫn "
        "dạng bài ở trên), bọc đúng phần đó bằng <u>...</u> ngay trong option.text — hệ thống sẽ tự render "
        "thành gạch chân thật khi xuất file, không cần và không được dùng ký hiệu nào khác (không markdown **, "
        "không dấu ngoặc kép quanh phần gạch chân). CHỈ dùng markup <u>...</u> bên trong option.text — TUYỆT "
        "ĐỐI KHÔNG dùng trong prompt_text, passage_text hay bất kỳ trường nào khác (câu dẫn/câu hỏi không cần "
        "và không được gạch chân, kể cả khi nhắc lại từ/chữ cái đang so sánh — chỉ mô tả bằng lời)."
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
