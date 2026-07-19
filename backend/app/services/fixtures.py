"""Fixture bank cho MockAIProvider. Nội dung MOCK viết tay — dữ liệu thật sẽ đến
từ RAG (chưa code, xem quyết định #15 trong PRD). Bộ GOLDEN_UNIT3_QUESTIONS lấy
nguyên văn 6 câu mẫu đã dùng trong prototype (bước 3 - Duyệt câu hỏi) để khớp
golden test Global Success 7 - Unit 3 Community Service.
"""


def _opts(*pairs: tuple[str, bool]) -> list[dict]:
    labels = ["A", "B", "C", "D"]
    return [{"label": labels[i], "text": text, "is_correct": correct} for i, (text, correct) in enumerate(pairs)]


GOLDEN_UNIT3_QUESTIONS: dict[str, list[dict]] = {
    "pronunciation": [
        {
            "prompt_text": "Choose the word whose underlined part is pronounced differently.",
            "options": _opts(("clean", False), ("bread", True), ("teach", False), ("team", False)),
            "answer_text": "B. bread",
            "explanation": '"bread" phát âm /e/, ba từ còn lại phát âm /iː/.',
            "target_knowledge": "Nguyên âm /iː/ – /e/",
            "source_ref": "GS7-U3 §3",
        },
        {
            "prompt_text": "Choose the word whose underlined part is pronounced differently.",
            "options": _opts(("helped", False), ("donated", True), ("cooked", False), ("washed", False)),
            "answer_text": "B. donated",
            "explanation": '"donated" phát âm /ɪd/, ba từ còn lại phát âm /t/.',
            "target_knowledge": "Đuôi -ed",
            "source_ref": "GS7-U3 §3",
        },
    ],
    "multiple_choice": [
        {
            "prompt_text": "We ______ old books and clothes to the children in the village last month.",
            "options": _opts(("donate", False), ("donated", True), ("will donate", False), ("are donating", False)),
            "answer_text": "B. donated",
            "explanation": '"last month" là dấu hiệu thì quá khứ đơn.',
            "target_knowledge": "Past Simple",
            "source_ref": "GS7-U3 §5",
        },
        {
            "prompt_text": "Volunteers in our neighbourhood often ______ elderly people with their daily housework.",
            "options": _opts(("help", True), ("helps", False), ("helping", False), ("helped", False)),
            "answer_text": "A. help",
            "explanation": 'Chủ ngữ số nhiều "Volunteers" + thì hiện tại đơn.',
            "target_knowledge": "Từ vựng Unit 3",
            "source_ref": "GS7-U3 §2",
        },
    ],
    "reading_true_false": [
        {
            "prompt_text": "The students taught English on weekdays. (True/False)",
            "passage_text": (
                "Last summer, students at Le Loi Secondary School joined a community project. "
                "They cleaned the lake, planted trees and taught English to primary pupils at the weekend."
            ),
            "answer_text": 'False. Đoạn văn ghi "at the weekend".',
            "explanation": 'Đoạn văn ghi "at the weekend", không phải weekdays.',
            "target_knowledge": "True/False",
            "source_ref": "GS7-U3 §8",
        }
    ],
    "sentence_rewrite": [
        {
            "prompt_text": "They will build a new library next year. → A new library ______ next year.",
            "answer_text": "will be built",
            "explanation": "Chuyển câu chủ động sang bị động, giữ nguyên thì tương lai đơn.",
            "target_knowledge": "Câu bị động",
            "level_code": "B1",
            "source_ref": "GS7-U3 §11",
        }
    ],
}

# Template chung cho 10 dạng bài — dùng khi không khớp golden test hoặc cần thêm câu.
GENERIC_TEMPLATES: dict[str, list[dict]] = {
    "pronunciation": [
        {
            "prompt_text": "Choose the word whose underlined part is pronounced differently.",
            "options": _opts(("book", False), ("food", True), ("look", False), ("good", False)),
            "answer_text": "B. food",
            "explanation": '"food" phát âm /uː/, ba từ còn lại phát âm /ʊ/.',
            "target_knowledge": "Nguyên âm /uː/ – /ʊ/",
        },
        {
            "prompt_text": "Choose the word whose underlined part is pronounced differently.",
            "options": _opts(("seat", False), ("meat", False), ("great", True), ("heat", False)),
            "answer_text": "C. great",
            "explanation": '"great" phát âm /eɪ/, ba từ còn lại phát âm /iː/.',
            "target_knowledge": "Nguyên âm /iː/ – /eɪ/",
        },
        {
            "prompt_text": "Choose the word whose underlined part is pronounced differently.",
            "options": _opts(("passed", False), ("missed", False), ("talked", False), ("played", True)),
            "answer_text": "D. played",
            "explanation": '"played" phát âm /d/, ba từ còn lại phát âm /t/.',
            "target_knowledge": "Đuôi -ed",
        },
    ],
    "stress": [
        {
            "prompt_text": "Choose the word that has a different stress pattern.",
            "options": _opts(("happy", False), ("lucky", False), ("about", True), ("sunny", False)),
            "answer_text": "C. about",
            "explanation": '"about" trọng âm rơi vào âm tiết thứ hai, ba từ còn lại trọng âm rơi vào âm tiết đầu.',
            "target_knowledge": "Trọng âm 2 âm tiết",
        },
        {
            "prompt_text": "Choose the word that has a different stress pattern.",
            "options": _opts(("invite", True), ("open", False), ("never", False), ("under", False)),
            "answer_text": "A. invite",
            "explanation": '"invite" trọng âm rơi vào âm tiết thứ hai.',
            "target_knowledge": "Trọng âm 2 âm tiết",
        },
    ],
    "multiple_choice": [
        {
            "prompt_text": "Every weekend, local volunteers ______ rubbish along the beach near our town.",
            "options": _opts(("collect", True), ("collects", False), ("collected", False), ("collecting", False)),
            "answer_text": "A. collect",
            "explanation": '"Every weekend" là dấu hiệu thì hiện tại đơn, chủ ngữ số nhiều.',
            "target_knowledge": "Present Simple",
        },
        {
            "prompt_text": "The Green Club always ______ old clothes to families in need every winter.",
            "options": _opts(("donate", False), ("donates", True), ("donating", False), ("donated", False)),
            "answer_text": "B. donates",
            "explanation": '"The Green Club" là chủ ngữ số ít, thì hiện tại đơn.',
            "target_knowledge": "Present Simple",
        },
        {
            "prompt_text": "Last Saturday, our class ______ a small library for children in the village.",
            "options": _opts(("built", True), ("build", False), ("builds", False), ("building", False)),
            "answer_text": "A. built",
            "explanation": '"Last Saturday" là dấu hiệu thì quá khứ đơn.',
            "target_knowledge": "Past Simple",
        },
    ],
    "matching": [
        {
            "prompt_text": "Match the word (1-4) with its meaning (A-D).",
            "options": _opts(
                ("1. volunteer — A. a person who works without being paid", True),
                ("2. donate — B. to give money or goods to help others", False),
                ("3. elderly — C. old people", False),
                ("4. rubbish — D. waste material", False),
            ),
            "answer_text": "1-A, 2-B, 3-C, 4-D",
            "explanation": "Nối đúng từ vựng chủ đề hoạt động tình nguyện với nghĩa tương ứng.",
            "target_knowledge": "Từ vựng hoạt động cộng đồng",
        }
    ],
    "gap_fill": [
        {
            "prompt_text": "Our school often organises a ______ (charity) fair to raise money for poor children.",
            "answer_text": "charity",
            "explanation": "Điền đúng danh từ chỉ hoạt động từ thiện, giữ nguyên nghĩa câu.",
            "target_knowledge": "Từ vựng hoạt động cộng đồng",
        }
    ],
    "cloze_test": [
        {
            "prompt_text": "Choose the best option to complete the passage. (blank 1)",
            "passage_text": (
                "Every summer, students in our town join a community (1) ______ programme. "
                "They help clean public parks, plant trees and visit elderly people who live alone. "
                "Many students say this experience teaches them to care more about others."
            ),
            "options": _opts(("service", True), ("services", False), ("serving", False), ("served", False)),
            "answer_text": "A. service",
            "explanation": '"community service" là cụm danh từ ghép quen thuộc của Unit.',
            "target_knowledge": "Cụm từ community service",
        }
    ],
    "reading_true_false": [
        {
            "prompt_text": "The volunteers only worked in the city centre. (True/False)",
            "passage_text": (
                "Last month, a group of teenagers travelled to a small village to help repair "
                "an old primary school. They painted the classrooms and donated books and desks."
            ),
            "answer_text": 'False. Đoạn văn nói họ tới "a small village", không phải trung tâm thành phố.',
            "explanation": "Chi tiết địa điểm trong đoạn văn khác với nhận định.",
            "target_knowledge": "True/False",
        }
    ],
    "sign_reading": [
        {
            "prompt_text": (
                "A sign at the park gate reads: \"Please keep the park clean. No littering.\" "
                "What does the sign ask people to do?"
            ),
            "options": _opts(
                ("Not to throw rubbish in the park", True),
                ("Not to walk on the grass", False),
                ("Not to bring pets", False),
                ("Not to take photos", False),
            ),
            "answer_text": "A. Not to throw rubbish in the park",
            "explanation": '"No littering" nghĩa là không xả rác. (Mô tả biển báo bằng văn bản — thư viện hình ảnh chưa có, chờ RAG.)',
            "target_knowledge": "Đọc biển báo",
        }
    ],
    "word_form": [
        {
            "prompt_text": "Volunteering gives young people a great sense of ______ (RESPONSIBLE) towards their community.",
            "answer_text": "responsibility",
            "explanation": "Cần danh từ sau mạo từ + tính từ 'great sense of', chuyển RESPONSIBLE thành responsibility.",
            "target_knowledge": "Word form: adjective → noun",
        }
    ],
    "sentence_rewrite": [
        {
            "prompt_text": "The volunteers cleaned the whole park in one day. → The whole park ______ in one day.",
            "answer_text": "was cleaned by the volunteers",
            "explanation": "Chuyển câu chủ động sang bị động, giữ nguyên thì quá khứ đơn.",
            "target_knowledge": "Câu bị động",
        }
    ],
}


def fallback_template(exercise_type_code: str) -> list[dict]:
    """Dùng khi một dạng bài chưa có template (ví dụ Admin thêm dạng mới) — vẫn trả
    về nội dung hợp lệ tối thiểu thay vì để trống, kèm cảnh báo rõ trong answer_text."""
    return [
        {
            "prompt_text": f"[MOCK] Câu hỏi mẫu cho dạng bài '{exercise_type_code}' chưa có fixture riêng.",
            "answer_text": "—",
            "explanation": "Chưa có fixture cho dạng bài này; cần bổ sung template hoặc chờ RAG.",
            "target_knowledge": exercise_type_code,
        }
    ]
