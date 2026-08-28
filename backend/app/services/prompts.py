"""Hướng dẫn sinh câu hỏi theo từng dạng bài (10 dạng, PRD mục 7) dùng cho
`OpenAIProvider`. Một dict thay vì 1 file/dạng bài — nội dung mỗi dạng chỉ vài câu,
tách file riêng chỉ thêm phiền mà không ích lợi ở quy mô này. Đổi nội dung hướng
dẫn thì tăng `PROMPT_VERSION` (ghi vào `GenerationLog.prompt_version`) để phân biệt
được câu hỏi sinh ra từ phiên bản prompt nào khi debug chất lượng.
"""

import random

PROMPT_VERSION = "v26"

# Hướng dẫn dạng phát âm tách theo KIỂU. Phần con nào cũng đã ghim đúng 1 kiểu qua
# prompt_override, nên gửi cả 3 kiểu là trả tiền cho ~600-880 token/lượt mô tả những
# kiểu model bị cấm dùng (đo 27/08/2026: hướng dẫn dạng này 1543 token, riêng phần
# chung 502).
_PRON_INTRO_ALL = 'Dạng chọn từ có phần phát âm khác 3 từ còn lại. Có 3 KIỂU — CHỌN ĐÚNG 1 KIỂU DUY NHẤT (kiểu phù hợp nhất với từ vựng có sẵn trong nguồn) rồi ÁP DỤNG ĐÚNG KIỂU ĐÓ CHO TOÀN BỘ số câu được yêu cầu trong lần sinh này — KHÔNG trộn nhiều kiểu khác nhau trong cùng 1 lần sinh (giáo viên muốn nhiều kiểu sẽ tự tạo nhiều lượt/phần riêng, không phải việc của bạn tự đổi kiểu giữa chừng):\n'
_PRON_KIND: dict[str, str] = {
    "s": "(1) Đuôi -s/-es: mọi từ đều tận cùng -s/-es nhưng đọc khác nhau /s/, /z/ hoặc /ɪz/ tùy âm đứng trước — vd 'look<u>s</u>' /s/, 'game<u>s</u>' /z/, 'dress<u>es</u>' /ɪz/. CHỈ bọc đúng chữ cái 's' hoặc 'es' VỐN ĐÃ CÓ SẴN ở cuối từ thật — KHÔNG bọc thêm chữ nào trước đó (SAI: 'dre<u>sses</u>'; ĐÚNG: 'dress<u>es</u>') và TUYỆT ĐỐI KHÔNG được thêm/nhân đôi ký tự 's' để tự tạo ra đuôi giả cho từ vốn đã đúng chính tả — nếu từ đã tận cùng bằng đúng 1 chữ 's' (vd 'stars', 'cars', 'bus', 'class', 'glass') thì dùng NGUYÊN từ đó, chỉ bọc <u> quanh chữ 's' có sẵn (SAI: 'star' → 'star<u>s</u>s' hay 'starss'; ĐÚNG: 'star<u>s</u>'. SAI: 'bus' → 'bu<u>s</u>s'; ĐÚNG: 'bu<u>s</u>' — từ sau khi bỏ markup phải là 1 từ tiếng Anh có thật, đánh vần đúng).\n",
    "ed": "(2) Đuôi -ed: mọi từ đều tận cùng -ed nhưng đọc khác nhau /t/, /d/ hoặc /ɪd/ tùy âm đứng trước — vd 'watch<u>ed</u>' /t/, 'lov<u>ed</u>' /d/, 'want<u>ed</u>' /ɪd/. CHỈ bọc đúng 2 chữ 'ed' VỐN ĐÃ CÓ SẴN ở cuối từ thật, không bọc thêm chữ nào trước đó và cũng không được thêm/nhân đôi ký tự để tạo đuôi giả — áp dụng đúng quy tắc chính tả -ed như 'watch'+'ed'='watch<u>ed</u>', không phải chèn thêm chữ tùy tiện.\n",
    "vowel": "(3) So sánh âm chung không phải đuôi -s/-es hay -ed: cả 4 lựa chọn cùng chứa ĐÚNG MỘT cụm chữ cái GIỐNG HỆT NHAU, 3 từ đọc cụm đó giống nhau và đúng 1 từ đọc khác — vd 'cl<u>ea</u>n', 'br<u>ea</u>d', 't<u>ea</u>ch', 't<u>ea</u>m' (đáp án 'bread' vì phát âm /e/, ba từ còn lại /iː/). Ba ràng buộc BẮT BUỘC của kiểu này:\n  • Phần bọc <u> phải đúng cụm chữ cái đang so sánh và NGẮN NHẤT có thể (thường 1-3 chữ cái, chỉ nguyên âm/cụm nguyên âm hoặc phụ âm đang xét) — KHÔNG bọc lan sang phần còn lại của từ (SAI: 'g<u>ather</u>', 'd<u>ifferent</u>', 'c<u>onfusing</u>'; ĐÚNG: 'g<u>a</u>ther', 'd<u>i</u>fferent', 'conf<u>u</u>sing').\n  • Cụm bọc <u> của CẢ 4 lựa chọn phải là CÙNG một chuỗi chữ cái (SAI: 3 từ bọc 'ar' nhưng từ còn lại bọc 'a'; SAI: 3 từ bọc 'ather' nhưng từ còn lại bọc 'other').\n  • TUYỆT ĐỐI KHÔNG bịa từ để cho đủ bộ 4: không được đổi 1 chữ cái của từ có thật để tạo từ mới (SAI: từ 'boring' chế ra 'foring'/'woring'/'soring' — không phải từ tiếng Anh). Nếu không tìm đủ 4 từ CÓ THẬT cùng cụm chữ cái, hãy đổi sang cụm chữ cái khác.\n",
}
_PRON_COMMON = "BẮT BUỘC với MỌI câu, không phân biệt kiểu nào:\n- QUY TẮC 3-1 VỀ ÂM (quan trọng nhất, kiểm tra lại từng câu trước khi trả kết quả): trong 4 lựa chọn phải có ĐÚNG 3 từ phát âm phần đang xét GIỐNG NHAU và ĐÚNG 1 từ khác — tuyệt đối không được 2-2 hay 1-1-1-1. Với đuôi -s/-es hãy tự đọc thầm âm cuối từng từ rồi đếm: SAI 'twins /z/, types /s/, separates /s/, overalls /z/' (2-2, không có đáp án duy nhất); ĐÚNG 'rings /z/, endings /z/, saves /z/, shoots /s/'. Với đuôi -ed: SAI 'saved /d/, loved /d/, wanted /ɪd/, visited /ɪd/' (2-2) và SAI 'learned /d/, played /d/, worked /t/, talked /t/' (2-2); ĐÚNG 'wanted /ɪd/, visited /ɪd/, decided /ɪd/, escaped /t/'.\n- 4 lựa chọn phải là 4 TỪ ĐƠN KHÁC NHAU: đúng MỘT từ, KHÔNG có dấu cách và KHÔNG có dấu gạch nối (SAI: 'native languages', 'southeast Asia', 'black-and-white', 'computer games', 'free time'; ĐÚNG: 'languages', 'films', 'voices').\n- KHÔNG thêm -s vào trạng từ hay từ không có dạng số nhiều/ngôi thứ 3 (SAI: 'magicallys', 'wiselys', 'violentlys' — trạng từ không bao giờ thêm -s).\n- Mỗi lựa chọn sau khi bỏ markup <u>...</u> đi PHẢI là 1 từ tiếng Anh có thật, đánh vần đúng chính tả — không tự chế/nhân đôi ký tự để khớp đuôi.\n- CẢ 4 lựa chọn (kể cả các lựa chọn sai) đều phải bọc phần đang so sánh trong <u>...</u> — không được bỏ sót lựa chọn nào.\nGiải thích nêu rõ ký hiệu IPA khác biệt."
_PRON_INTRO_ONE = (
    "Dạng chọn từ có phần phát âm khác 3 từ còn lại. Phần này ĐÃ CHỐT sẵn đúng 1 kiểu — "
    "áp dụng kiểu mô tả dưới đây cho TOÀN BỘ số câu, không dùng kiểu nào khác:\n"
)


def detect_pronunciation_kind(prompt_override: str | None) -> str | None:
    """Suy 'kiểu' bài phát âm từ prompt_override của Phần con (preset ở ExamBuilder ghi
    'kiểu (1)/(2)/(3)'). None = không rõ kiểu -> gửi cả 3 kiểu."""
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


def pronunciation_instruction(kind: str | None) -> str:
    """Chỉ gửi luật của kiểu đang ra đề; kiểu không rõ thì gửi cả 3 như trước."""
    if kind is None or kind not in _PRON_KIND:
        return _PRON_INTRO_ALL + _PRON_KIND["s"] + _PRON_KIND["ed"] + _PRON_KIND["vowel"] + _PRON_COMMON
    return _PRON_INTRO_ONE + _PRON_KIND[kind] + _PRON_COMMON


EXERCISE_INSTRUCTIONS: dict[str, str] = {
    "pronunciation": pronunciation_instruction(None),
    "stress": (
        "Dạng chọn từ có trọng âm khác 3 từ còn lại. BẮT BUỘC: 4 lựa chọn phải là 4 TỪ ĐƠN "
        "KHÁC NHAU (không trùng từ, không phải cụm từ/câu) có CÙNG số âm tiết — 3 từ trọng âm "
        "rơi vào cùng vị trí âm tiết, đúng 1 từ trọng âm rơi vào vị trí khác (đó là đáp án "
        "đúng). TUYỆT ĐỐI KHÔNG gạch chân, KHÔNG dùng <u>...</u> trong bất kỳ lựa chọn nào: "
        "gạch chân âm tiết mang trọng âm chính là chỉ sẵn đáp án cho học sinh, đề thật để từ "
        "trần. option.text chỉ là từ viết thường bình thường. Ví dụ 4 lựa chọn hợp lệ (2 âm "
        "tiết): 'handsome', 'travel', 'begin', 'modern' — đáp án 'begin' vì trọng âm rơi vào "
        "âm tiết 2, ba từ còn lại rơi vào âm tiết 1. "
        "Giải thích nêu rõ vị trí trọng âm (âm tiết thứ mấy) của từng từ."
    ),
    "multiple_choice": (
        "Phần VOCABULARY AND GRAMMAR: trắc nghiệm 4 lựa chọn A/B/C/D, đúng 1 đáp án đúng.\n"
        "ĐỊNH DẠNG BẮT BUỘC — MỌI câu đều là HỘI THOẠI 2 LƯỢT, không có ngoại lệ, TUYỆT ĐỐI "
        "KHÔNG dùng câu đơn kiểu 'Solar energy is a ______ source of energy.'\n"
        "prompt_text BẮT BUỘC có ĐÚNG HAI DÒNG, mỗi dòng một lượt nói dạng 'Tên: câu nói', "
        "phân cách bằng ký tự xuống dòng. MỘT DÒNG LÀ SAI — dù câu đó hay đến mấy: thiếu "
        "lượt đáp thì không còn là hội thoại (SAI: 'Bao Han: I enjoy planting flowers in my "
        "______. How about you?' — chỉ có 1 người nói).\n"
        "Toàn bộ câu có ĐÚNG MỘT chỗ trống '______', đặt ở lượt 1 HOẶC lượt 2 (đề thật dùng "
        "cả hai, lượt 1 hơi nhiều hơn) — lượt còn lại không được có chỗ trống nào. Ví dụ định dạng:\n"
        "  Minh Khoa: Why does Duc Minh always join the school football club?\n"
        "  Bao Han: Because he is really crazy ______ sports and loves playing in his free time.\n"
        "  → 4 lựa chọn cho ví dụ trên: A. about  B. on  C. at  D. to\n"
        "ĐÁP ÁN PHẢI ĐIỀN VÀO CHỖ TRỐNG THÀNH CÂU ĐÚNG NGỮ PHÁP — tự đọc lại cả câu sau khi "
        "thay ______ bằng đáp án trước khi trả kết quả. Hai lỗi hay gặp: (a) lựa chọn nhắc lại "
        "danh từ ĐÃ CÓ trong câu (SAI: 'I like to ______ old coins' với lựa chọn 'collect coin' "
        "-> 'collect coin old coins'; ĐÚNG: 'collect'); (b) sai dạng động từ theo từ đứng trước "
        "(SAI: 'I love ______ dollhouses' với đáp án 'build' -> 'I love build dollhouses'; ĐÚNG: "
        "'building'). 4 lựa chọn phải CÙNG một dạng từ để dạng từ không tự tố cáo đáp án.\n"
        "KHÔNG dùng lại một đáp án cho hai câu khác nhau trong cùng lần sinh.\n"
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
    "word_entry": (
        "Dạng WORD ENTRY (tra mục từ điển) — xuất hiện 11/13 đề thật: cho sẵn MỤC TỪ ĐIỂN của một từ, "
        "học sinh đọc mục đó rồi điền dạng đúng vào câu.\n"
        "passage_text là mục từ điển, viết như từ điển thật: từ, phiên âm, rồi từng nghĩa đánh số kèm "
        "từ loại và ví dụ. Mẫu:\n"
        "  leisure /ˈleʒər/\n"
        "  1. (n) time when you are not working and can do what you enjoy: I read comics in my leisure time.\n"
        "  2. leisurely (adj) done slowly, without hurrying: We had a leisurely walk around the lake.\n"
        "Mục từ PHẢI có ít nhất 2 nghĩa/dạng từ khác nhau, nếu không thì câu hỏi không cần tra mục từ.\n"
        "Mỗi câu hỏi có ĐÚNG MỘT chỗ trống ______ và điền được nhờ ĐỌC MỤC TỪ ở trên — mỗi câu dùng một "
        "nghĩa/dạng KHÁC nhau của mục từ đó. Câu toàn tiếng Anh, hợp ngữ cảnh học sinh THCS Việt Nam "
        "(được dùng tên riêng tiếng Việt). answer_text là từ đã điền, chỉ 1 từ.\n"
        "KHÔNG sinh lựa chọn A/B/C/D: options PHẢI là null, đây là bài điền từ.\n"
        "KHÔNG đặt từ gốc trong ngoặc ở cuối câu — mục từ điển đã cho sẵn, thêm nữa là thừa."
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


# --- Kho câu mẫu ------------------------------------------------------------
# Sách Global Success trong Knowledge_Base gần như KHÔNG có câu ví dụ: file
# "GS7 - UNIT 1 - LESSON.docx" chỉ có 2/231 đoạn là câu tiếng Anh hoàn chỉnh, phần còn
# lại là mục từ điển ("hobby (n) /ˈhɑː.bi/ : sở thích"). Model vì thế không có câu thật
# nào để bắt chước, nên tự bịa câu từ vốn chung của nó — ra đề nhạt và lặp ngữ cảnh.
#
# Kho này bù vào chỗ đó. Mỗi lần gọi chỉ đưa một NHÓM NHỎ luân phiên, vì hai lý do:
# đưa hết thì prompt phình và model bị kéo về một khuôn duy nhất; và model từng chép
# nguyên câu ví dụ vào đề ("Solar energy is a ______ source of energy." — đề sinh thử
# 07/08/2026), nên càng ít mẫu mỗi lần thì càng cần luân phiên để đề không giống nhau.
# mcq_check/word_form_check lấy chính kho này làm danh sách "cấm chép" nên luôn đồng bộ.
_EXAMPLES_PER_CALL = 4

MULTIPLE_CHOICE_EXAMPLES: tuple[str, ...] = (
    "Minh Khoa: Why does Duc Minh always join the school football club?\n"
    "Bao Han: Because he is really crazy ______ sports and loves playing in his free time.\n"
    "A. about   B. on   C. at   D. to",
    "Khanh Ngoc: Are you keen ______ gardening or going shopping this Saturday?\n"
    "Tu Anh: Gardening! I love growing vegetables and flowers with my grandma.\n"
    "A. on   B. in   C. at   D. about",
    "Lan Chi: What did your class do to help the flood victims last month?\n"
    "Quang Huy: We ______ warm clothes and books for the children in the village.\n"
    "A. collected   B. collect   C. collecting   D. have collected",
    "Gia Linh: My brother spends three hours a day playing video games.\n"
    "Phuc Hung: That is ______ long. He should go outside and get some exercise.\n"
    "A. far too   B. much more   C. very many   D. so much",
    "Tu Anh: Do you know the girl ______ is standing near the school gate?\n"
    "Minh Quan: Yes, she is my cousin. She has just moved to our neighbourhood.\n"
    "A. who   B. which   C. whose   D. whom",
    "Bao Han: Our village is much quieter ______ the city where you live.\n"
    "Khanh Ngoc: That is why I enjoy visiting you every summer holiday.\n"
    "A. than   B. as   C. from   D. like",
    "Phuc Hung: If we recycle more paper, we ______ thousands of trees every year.\n"
    "Lan Chi: You are right. Our school should start a recycling club.\n"
    "A. will save   B. saved   C. would save   D. have saved",
    "Minh Quan: Would you mind ______ the window? It is quite cold in here.\n"
    "Gia Linh: Not at all. Let me do it for you right now.\n"
    "A. closing   B. to close   C. close   D. closed",
    "Quang Huy: How often do you take part ______ the school English club?\n"
    "Bao Han: Twice a week, and we always practise speaking with our teacher.\n"
    "A. in   B. on   C. of   D. for",
    "Khanh Ngoc: My grandmother made this bamboo basket ______ herself.\n"
    "Tu Anh: It looks beautiful. She is really good at traditional crafts.\n"
    "A. by   B. with   C. for   D. on",
    "Gia Linh: The students were very ______ when they heard the exam results.\n"
    "Minh Khoa: I understand. They had studied hard for the whole month.\n"
    "A. excited   B. exciting   C. excitement   D. excitedly",
    "Lan Chi: You look tired. What ______ you doing at midnight yesterday?\n"
    "Phuc Hung: I was finishing my science project for the school contest.\n"
    "A. were   B. are   C. did   D. have",
)

WORD_FORM_FAMILY_EXAMPLES: tuple[str, ...] = (
    "❖ create (v) → creation (n) → creative (adj) → creatively (adv)\n"
    "1. My sister loves to ______ small dollhouses from cardboard.\n"
    "2. The teacher praised the ______ of every student in the art club.\n"
    "3. Nam is a very ______ boy who always has new ideas.\n"
    "4. She decorated the classroom ______ for the New Year party.",
    "❖ pollute (v) → pollution (n) → polluted (adj)\n"
    "1. Factories near the river ______ the water every single day.\n"
    "2. Air ______ in big cities is becoming a serious problem.\n"
    "3. Fish cannot live in such heavily ______ water.",
)

WORD_FORM_BRACKET_EXAMPLES: tuple[str, ...] = (
    "1. I want to become a ______ when I grow up. (science)",
    "2. The children were playing ______ in the school yard. (happy)",
    "3. Our teacher gave us a very clear ______ of the new lesson. (explain)",
    "4. Please be ______ when you cross this busy street. (care)",
)


def _rotating(pool: tuple[str, ...], offset: int | None) -> list[str]:
    """Lấy _EXAMPLES_PER_CALL mẫu, cuốn chiếu theo offset. offset=None thì lấy ngẫu
    nhiên — mỗi lần sinh thấy bộ mẫu khác nhau nên đề không rập một khuôn."""
    if not pool:
        return []
    start = random.randrange(len(pool)) if offset is None else offset % len(pool)
    return [pool[(start + i) % len(pool)] for i in range(min(_EXAMPLES_PER_CALL, len(pool)))]


def example_block(
    exercise_type_code: str, offset: int | None = None, examples: list[str] | None = None
) -> str:
    """Khối câu mẫu chèn vào system prompt, rỗng nếu dạng bài chưa có kho mẫu.

    `examples` là câu mẫu lấy từ ĐỀ THẬT của đúng Unit (rag_search.exam_examples) — ưu
    tiên hơn kho viết tay vì bám đúng chủ đề và độ khó của bài đang ra đề. Unit chưa nạp
    đề thật thì rơi về kho viết tay, nên không Unit nào bị bỏ trắng.
    """
    if examples:
        return _wrap_examples(list(examples))
    if exercise_type_code == "multiple_choice":
        chosen = _rotating(MULTIPLE_CHOICE_EXAMPLES, offset)
    elif exercise_type_code == "word_form":
        chosen = _rotating(WORD_FORM_FAMILY_EXAMPLES + WORD_FORM_BRACKET_EXAMPLES, offset)
    else:
        return ""
    return _wrap_examples(chosen)


def _wrap_examples(chosen: list[str]) -> str:
    if not chosen:
        return ""
    return (
        "\nCÂU MẪU tham khảo về VĂN PHONG và ĐỘ KHÓ (không phải nội dung bài này) — "
        "học cách đặt câu, đừng chép lại chữ nào:\n" + "\n\n".join(chosen) + "\n"
    )


# Mô tả cụ thể từng trình độ để model có gì mà bám. Trước đây prompt chỉ nêu TÊN mức
# ("trình độ mục tiêu A2") nên A1 và B1 ra đề gần như y hệt nhau — mọi ràng buộc định
# lượng lại khoá theo cấp học/khối lớp, không theo trình độ, nên hạ mức cho lớp yếu
# không có tác dụng thật (chủ dự án duyệt bảng này ngày 28/08/2026).
#
# Độ dài câu do prompt lo, KHÔNG chặn ở Validation Engine: khoảng của cấp học và khoảng
# của trình độ đo hai thứ khác nhau, chấm bằng cái này trong khi model được dặn theo cái
# kia thì mọi câu đều bị cảnh báo oan (chốt 28/08/2026).
LEVEL_GUIDANCE: dict[str, str] = {
    "A1": (
        "Trình độ A1: câu 6-10 từ. CHỈ dùng hiện tại đơn và hiện tại tiếp diễn. Từ vựng "
        "trong khoảng 500 từ thông dụng nhất. KHÔNG dùng mệnh đề quan hệ."
    ),
    "A2": (
        "Trình độ A2: câu 10-14 từ. Ngoài hiện tại đơn/tiếp diễn được dùng thêm quá khứ "
        "đơn, thì tương lai và cấu trúc so sánh. Mệnh đề quan hệ chỉ ở dạng đơn giản."
    ),
    "B1": (
        "Trình độ B1: câu 14-18 từ. Được dùng hiện tại hoàn thành, câu điều kiện, câu bị "
        "động và mệnh đề phụ."
    ),
    "B2": (
        "Trình độ B2: câu 16-22 từ. Được dùng mọi thì, câu điều kiện hỗn hợp, mệnh đề "
        "rút gọn, đảo ngữ và các cấu trúc nhấn mạnh."
    ),
    "C1": (
        "Trình độ C1: câu 18-26 từ. Không giới hạn cấu trúc ngữ pháp; ưu tiên diễn đạt "
        "học thuật, thành ngữ và cách nói trang trọng."
    ),
}

def level_guidance(level_code: str | None) -> str:
    """Mô tả trình độ chèn vào prompt, rỗng nếu mức lạ."""
    return LEVEL_GUIDANCE.get((level_code or "").upper(), "")


def build_system_prompt(
    exercise_type_code: str,
    question_count: int,
    level_code: str,
    example_offset: int | None = None,
    examples: list[str] | None = None,
    prompt_override: str | None = None,
) -> str:
    if exercise_type_code == "pronunciation":
        # Chỉ gửi luật của kiểu phần con này ghim (xem pronunciation_instruction).
        instruction = pronunciation_instruction(detect_pronunciation_kind(prompt_override))
    else:
        instruction = EXERCISE_INSTRUCTIONS.get(
            exercise_type_code,
            "Sinh câu hỏi tiếng Anh phù hợp trình độ mục tiêu, bám sát tài liệu nguồn được cung cấp.",
        )
    return (
        "Bạn là trợ lý tạo đề thi tiếng Anh THCS cho giáo viên Việt Nam. "
        f"Sinh đúng {question_count} câu hỏi dạng '{exercise_type_code}', trình độ mục tiêu {level_code}. "
        f"{level_guidance(level_code)} "
        f"Mảng questions PHẢI có đúng {question_count} phần tử. "
        f"{instruction} "
        "CHỈ dùng kiến thức có trong tài liệu nguồn được cung cấp bên dưới — không tự bịa từ vựng/ngữ pháp "
        "ngoài phạm vi đó. Nếu tài liệu nguồn không đủ để sinh đúng số câu yêu cầu, vẫn sinh tối đa có thể "
        "và ghi rõ lý do vào insufficient_source_warning; nếu đủ thì để insufficient_source_warning là null. "
        "source_chunk_ids của mỗi câu phải là ID (trong ngoặc vuông trước mỗi đoạn nguồn) đã thực sự dùng. "
        "Khi cần đánh dấu phần gạch chân trong 1 lựa chọn (bắt buộc với dạng phát âm; dạng TRỌNG ÂM thì "
        "ngược lại, tuyệt đối không gạch chân — xem hướng dẫn dạng bài ở trên), bọc đúng phần đó "
        "bằng <u>...</u> ngay trong option.text — hệ thống sẽ tự render "
        "thành gạch chân thật khi xuất file, không cần và không được dùng ký hiệu nào khác (không markdown **, "
        "không dấu ngoặc kép quanh phần gạch chân). CHỈ dùng markup <u>...</u> bên trong option.text — TUYỆT "
        "ĐỐI KHÔNG dùng trong prompt_text, passage_text hay bất kỳ trường nào khác (câu dẫn/câu hỏi không cần "
        "và không được gạch chân, kể cả khi nhắc lại từ/chữ cái đang so sánh — chỉ mô tả bằng lời)."
        + example_block(exercise_type_code, example_offset, examples)
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
