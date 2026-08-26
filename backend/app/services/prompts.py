"""Hướng dẫn sinh câu hỏi theo từng dạng bài (10 dạng, PRD mục 7) dùng cho
`OpenAIProvider`. Một dict thay vì 1 file/dạng bài — nội dung mỗi dạng chỉ vài câu,
tách file riêng chỉ thêm phiền mà không ích lợi ở quy mô này. Đổi nội dung hướng
dẫn thì tăng `PROMPT_VERSION` (ghi vào `GenerationLog.prompt_version`) để phân biệt
được câu hỏi sinh ra từ phiên bản prompt nào khi debug chất lượng.
"""

PROMPT_VERSION = "v18"

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
        "(3) So sánh âm chung không phải đuôi -s/-es hay -ed: cả 4 lựa chọn cùng chứa ĐÚNG MỘT "
        "cụm chữ cái GIỐNG HỆT NHAU, 3 từ đọc cụm đó giống nhau và đúng 1 từ đọc khác — vd "
        "'cl<u>ea</u>n', 'br<u>ea</u>d', 't<u>ea</u>ch', 't<u>ea</u>m' (đáp án 'bread' vì phát "
        "âm /e/, ba từ còn lại /iː/). Ba ràng buộc BẮT BUỘC của kiểu này:\n"
        "  • Phần bọc <u> phải đúng cụm chữ cái đang so sánh và NGẮN NHẤT có thể (thường 1-3 chữ "
        "cái, chỉ nguyên âm/cụm nguyên âm hoặc phụ âm đang xét) — KHÔNG bọc lan sang phần còn lại "
        "của từ (SAI: 'g<u>ather</u>', 'd<u>ifferent</u>', 'c<u>onfusing</u>'; ĐÚNG: "
        "'g<u>a</u>ther', 'd<u>i</u>fferent', 'conf<u>u</u>sing').\n"
        "  • Cụm bọc <u> của CẢ 4 lựa chọn phải là CÙNG một chuỗi chữ cái (SAI: 3 từ bọc 'ar' "
        "nhưng từ còn lại bọc 'a'; SAI: 3 từ bọc 'ather' nhưng từ còn lại bọc 'other').\n"
        "  • TUYỆT ĐỐI KHÔNG bịa từ để cho đủ bộ 4: không được đổi 1 chữ cái của từ có thật để "
        "tạo từ mới (SAI: từ 'boring' chế ra 'foring'/'woring'/'soring' — không phải từ tiếng "
        "Anh). Nếu không tìm đủ 4 từ CÓ THẬT cùng cụm chữ cái, hãy đổi sang cụm chữ cái khác.\n"
        "BẮT BUỘC với MỌI câu, không phân biệt kiểu nào:\n"
        "- QUY TẮC 3-1 VỀ ÂM (quan trọng nhất, kiểm tra lại từng câu trước khi trả kết quả): "
        "trong 4 lựa chọn phải có ĐÚNG 3 từ phát âm phần đang xét GIỐNG NHAU và ĐÚNG 1 từ khác "
        "— tuyệt đối không được 2-2 hay 1-1-1-1. Với đuôi -s/-es hãy tự đọc thầm âm cuối từng "
        "từ rồi đếm: SAI 'twins /z/, types /s/, separates /s/, overalls /z/' (2-2, không có đáp "
        "án duy nhất); ĐÚNG 'rings /z/, endings /z/, saves /z/, shoots /s/'. Với đuôi -ed: SAI "
        "'saved /d/, loved /d/, wanted /ɪd/, visited /ɪd/' (2-2) và SAI 'learned /d/, played "
        "/d/, worked /t/, talked /t/' (2-2); ĐÚNG 'wanted /ɪd/, visited /ɪd/, decided /ɪd/, "
        "escaped /t/'.\n"
        "- 4 lựa chọn phải là 4 TỪ ĐƠN KHÁC NHAU: đúng MỘT từ, KHÔNG có dấu cách và KHÔNG có "
        "dấu gạch nối (SAI: 'native languages', 'southeast Asia', 'black-and-white', 'computer "
        "games', 'free time'; ĐÚNG: 'languages', 'films', 'voices').\n"
        "- KHÔNG thêm -s vào trạng từ hay từ không có dạng số nhiều/ngôi thứ 3 (SAI: "
        "'magicallys', 'wiselys', 'violentlys' — trạng từ không bao giờ thêm -s).\n"
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
        "Phần VOCABULARY AND GRAMMAR: trắc nghiệm 4 lựa chọn A/B/C/D, đúng 1 đáp án đúng.\n"
        "ĐỊNH DẠNG BẮT BUỘC — MỌI câu đều là HỘI THOẠI 2 LƯỢT, không có ngoại lệ, TUYỆT ĐỐI "
        "KHÔNG dùng câu đơn kiểu 'Solar energy is a ______ source of energy.'\n"
        "Lượt 1 là lời của người A, lượt 2 là lời đáp của người B. Mỗi lượt một dòng, phân cách "
        "bằng ký tự xuống dòng, dạng 'Tên: câu nói'. Chỗ trống '______' chỉ nằm ở LƯỢT 2 và "
        "toàn bộ câu có ĐÚNG MỘT chỗ trống (lượt 1 không được có chỗ trống). Ví dụ định dạng:\n"
        "  Minh Khoa: Why does Duc Minh always join the school football club?\n"
        "  Bao Han: Because he is really crazy ______ sports and loves playing in his free time.\n"
        "  → 4 lựa chọn cho ví dụ trên: A. about  B. on  C. at  D. to\n"
        "PHÂN VAI RÕ RÀNG — sai chỗ này là câu hỏng hẳn: prompt_text chứa CẢ HAI lượt và chứa "
        "chỗ trống; option.text chỉ là TỪ hoặc CỤM TỪ NGẮN (tối đa 6 từ) điền vào chỗ trống đó. "
        "Lựa chọn TUYỆT ĐỐI không được chứa dấu ______, không được là câu hoàn chỉnh, và 4 lựa "
        "chọn không được lặp chung một đoạn đầu dài.\n"
        "SAI (đề sinh thử 24/08/2026 — nhét cả lượt trả lời vào lựa chọn, học sinh không còn gì để chọn):\n"
        "  prompt_text: 'Khanh Ngoc: What do we usually do at the firework festival?'\n"
        "  A. We enjoy the show and ______ with friends.  B. We enjoy the show and ______ gifts.\n"
        "MỖI CÂU MỘT NỘI DUNG KHÁC NHAU — không ra lại cùng một câu chỉ đổi tên nhân vật.\n"
        "Dùng TÊN RIÊNG VIỆT NAM không dấu cho nhân vật (Minh Khoa, Bao Han, Khanh Ngoc, "
        "Tu Anh, Phuc Hung, Gia Linh, Lan Chi, Quang Huy...), mỗi câu đổi cặp tên khác nhau.\n"
        "Lượt 1 phải là câu có nội dung thật (câu hỏi hoặc lời kể) dẫn dắt tự nhiên tới lượt 2, "
        "không được là câu chào rỗng kiểu 'Hi!' / 'Hello!' chỉ để lấp chỗ.\n"
        "Câu ví dụ trên chỉ để minh hoạ ĐỊNH DẠNG — TUYỆT ĐỐI KHÔNG chép lại nội dung của nó, "
        "phải tự đặt câu mới bám từ vựng/ngữ pháp của bài.\n"
        "TUYỆT ĐỐI KHÔNG dùng câu đố nghĩa/dịch — SAI: "
        "\"What does 'in person' mean?\", \"Which phrase means to stay in touch?\", "
        "\"How do you say 'giao tiếp với' in English?\".\n"
        "TOÀN BỘ đề bằng TIẾNG ANH (tên riêng Việt Nam thì giữ nguyên) — KHÔNG chèn câu chữ "
        "tiếng Việt vào prompt_text hay lựa chọn; riêng explanation vẫn viết tiếng Việt.\n"
        "CÂN ĐỐI NỘI DUNG: khoảng MỘT NỬA số câu kiểm tra NGỮ PHÁP (bám đúng mục ngữ pháp có "
        "trong tài liệu nguồn: giới từ, thì của động từ, liên từ, so sánh, V-ing/to-V...), "
        "nửa còn lại kiểm tra TỪ VỰNG (chọn từ hợp ngữ cảnh của câu).\n"
        "4 lựa chọn phải CÙNG LOẠI (cùng từ loại, hoặc cùng là các dạng chia của một động từ) "
        "và CHỈ DUY NHẤT 1 phương án đúng. BẮT BUỘC tự kiểm NGAY KHI SINH: với MỖI phương án "
        "nhiễu, hãy thay nó vào chỗ trống rồi ghi vào trường why_wrong lý do NGẮN GỌN vì sao "
        "câu trở nên SAI (sai ngữ pháp, sai collocation, hoặc sai nghĩa trong ngữ cảnh). Nếu "
        "không nêu được lý do rõ ràng — tức phương án đó CŨNG ĐÚNG — thì PHẢI thay bằng "
        "phương án nhiễu khác trước khi trả kết quả. why_wrong của đáp án đúng để null.\n"
        "Ví dụ phải tránh: "
        "(SAI: 'They will ______ with each other.' với cả interact/connect/communicate).\n"
        "KHÔNG hỏi phiên âm/IPA hay trọng âm (đã có phần riêng). KHÔNG dùng markup <u>...</u> "
        "ở dạng này. KHÔNG hỏi kiến thức khoa học/đời sống mà không cần biết tiếng Anh vẫn "
        "trả lời được."
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
        "Dạng WORD FORMATION theo format đề thi thật, có 2 KIỂU — phần con sẽ ghi rõ dùng kiểu nào; "
        "nếu không ghi thì dùng kiểu (A). TUYỆT ĐỐI không trộn 2 kiểu trong cùng một lần sinh. "
        "KHÔNG sinh lựa chọn trắc nghiệm cho dạng này: trường options PHẢI là null — đây là bài ĐIỀN TỪ, "
        "học sinh tự viết đáp án chứ không chọn A/B/C/D. "
        "KIỂU (A) NHÓM THEO HỌ TỪ: TẤT CẢ các câu của lần sinh này dùng CHUNG ĐÚNG MỘT họ từ duy nhất — "
        "không được mỗi câu một họ từ khác nhau. Mọi câu ghi target_knowledge Y HỆT NHAU, "
        "theo mẫu 'adore (v) → adorable (adj) → adorably (adv)': 2-4 thành phần (KHÔNG quá 4), phân cách bằng →, "
        "mỗi thành phần là 1 từ kèm từ loại trong ngoặc (v/n/adj/adv) — không thêm dấu hai chấm hay lời giải thích, "
        "không lặp lại cùng một từ hai lần trong chuỗi. "
        "Mỗi câu điền MỘT dạng KHÁC NHAU của họ từ đó, trải đều các từ loại đã liệt kê. "
        "prompt_text TUYỆT ĐỐI KHÔNG chứa từ gốc trong ngoặc — họ từ đã in sẵn ở dòng tiêu đề nhóm, "
        "thêm '(together)' vào cuối câu là lộ đáp án. "
        "KIỂU (B) TỪ GỐC TRONG NGOẶC — là bài ÔN TẬP TỔNG HỢP của kiểu (A): prompt_text KẾT THÚC "
        "bằng từ gốc trong ngoặc đơn, vd 'I want to become a ______ (science).' để điền 'scientist'. "
        "Từ trong ngoặc PHẢI thuộc đúng họ từ được chỉ định, và PHẢI KHÁC TỪ LOẠI với dạng cần "
        "điền — TUYỆT ĐỐI không đặt sẵn chính đáp án vào ngoặc. Chỉ 1 từ, không viết hoa toàn bộ. "
        "Mỗi câu phải CÓ NGHĨA tự nhiên — không ghép bừa một từ vào chỗ trống cho đủ số câu "
        "(SAI: 'To keep fit, you should ______ junk food. (benefit)'). "
        "target_knowledge ở kiểu này mô tả chuyển đổi bằng lời, KHÔNG viết thành chuỗi họ từ. "
        "CẢ 2 KIỂU: mỗi câu đúng MỘT chỗ trống viết bằng ______ (6 dấu gạch dưới), câu toàn tiếng Anh, "
        "nội dung hợp ngữ cảnh học sinh THCS Việt Nam (được dùng tên riêng tiếng Việt), "
        "answer_text là từ đã biến đổi và CHỈ 1 từ, không dùng markup <u>...</u>."
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
    feedback: str | None = None,
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
    if feedback:
        lines.append(f"Câu vừa sinh BỊ LỖI, hãy sinh câu mới KHÁC sửa đúng lỗi này: {feedback}")
    return "\n".join(lines)
