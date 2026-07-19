"""Seed toàn bộ dữ liệu danh mục đã được giáo viên chốt.

Nguồn dữ liệu: docs/engineering/IMPLEMENTATION_NOTES.vi.md mục 1.
Idempotent: chạy lại nhiều lần không tạo trùng, dựa trên các cột code/unique tự nhiên.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import SessionLocal
from app.models.academic import BookSeries, CambridgeCertificate, Grade, ProficiencyLevel, SchoolStage, Unit
from app.models.exercise import ExerciseType, PassageLengthRule, SentenceLengthRule
from app.models.grammar import GrammarGroup, GrammarPoint, GrammarTopic
from app.models.user import User, UserRole
from app.security import hash_password

CEFR_LEVELS = [
    ("A1", 1),
    ("A2", 2),
    ("B1", 3),
    ("B2", 4),
    ("C1", 5),
]

CAMBRIDGE_TO_CEFR = {
    "Starters": "A1",
    "Movers": "A1",
    "Flyers": "A2",
    "KET": "B1",
    "PET": "B2",
}

SCHOOL_STAGES = [
    ("primary", "Primary — Tiểu học", 1),
    ("secondary", "Secondary — THCS", 2),
    ("high_school", "High school — THPT", 3),
]

# Khối lớp -> (school_stage_code, trình độ gợi ý CEFR)
GRADE_SUGGEST = {
    1: ("primary", "A1"),
    2: ("primary", "A1"),
    3: ("primary", "A1"),
    4: ("primary", "A1"),
    5: ("primary", "A2"),
    6: ("secondary", "A2"),
    7: ("secondary", "A2"),
    8: ("secondary", "B1"),
    9: ("secondary", "B1"),
    10: ("high_school", "B2"),
    11: ("high_school", "B2"),
    12: ("high_school", "B2"),
}

GS_UNIT_TITLES: dict[int, list[str]] = {
    6: [
        "My New School", "My House", "My Friends", "My Neighbourhood",
        "Natural Wonders of Viet Nam", "Our Tet Holiday", "Television", "Sports and Games",
        "Cities of the World", "Our Houses in the Future", "Our Greener World", "Robots",
    ],
    7: [
        "Hobbies", "Healthy Living", "Community Service", "Music and Arts",
        "Food and Drink", "A Visit to a School", "Traffic", "Films",
        "Festivals Around the World", "Energy Sources", "Travelling in the Future",
        "English-speaking Countries",
    ],
    8: [
        "Leisure Time", "Life in the Countryside", "Teenagers", "Ethnic Groups of Viet Nam",
        "Our Customs and Traditions", "Lifestyles", "Environmental Protection", "Shopping",
        "Natural Disasters", "Communication in the Future", "Science and Technology",
        "Life on Other Planets",
    ],
    9: [
        "Local Community", "City Life", "Healthy Living for Teens", "Remembering the Past",
        "Our Experiences", "Vietnamese Lifestyle: Then and Now", "Natural Wonders of the World",
        "Tourism", "World Englishes", "Planet Earth", "Electronic Devices", "Career Choices",
    ],
    10: [
        "Family Life", "Humans and the Environment", "Music", "For a Better Community",
        "Inventions", "Gender Equality", "Viet Nam and International Organisations",
        "New Ways to Learn", "Protecting the Environment", "Ecotourism",
    ],
    11: [
        "A Long and Healthy Life", "The Generation Gap", "Cities of the Future", "ASEAN and Viet Nam",
        "Global Warming", "Preserving Our Heritage", "Education Options for School-leavers",
        "Becoming Independent", "Social Issues", "The Ecosystem",
    ],
    12: [
        "Life Stories We Admire", "A Multicultural World", "Green Living", "Urbanisation",
        "The World of Work", "Artificial Intelligence", "The World of Mass Media",
        "Wildlife Conservation", "Career Paths", "Lifelong Learning",
    ],
}

# (code, name, min_level) theo nhóm — Implementation Notes 1.2
TENSE_GROUPS = [
    ("Hiện tại", [
        ("Present Simple", "A1"),
        ("Present Continuous", "A1"),
        ("Present Perfect", "A2"),
        ("Present Perfect Continuous", "B1"),
    ]),
    ("Quá khứ", [
        ("Past Simple", "A1"),
        ("Past Continuous", "A2"),
        ("Past Perfect", "B1"),
        ("Past Perfect Continuous", "B2"),
    ]),
    ("Tương lai", [
        ("Future Simple", "A1"),
        ("Future Continuous", "B1"),
        ("Future Perfect", "B2"),
        ("Future Perfect Continuous", "B2"),
    ]),
]

# Implementation Notes 1.3
STRUCTURE_GROUPS = [
    ("Cấu trúc nền tảng (Primary)", [
        ("Khẳng định / phủ định / nghi vấn", "A1"),
        ("There is / There are", "A1"),
        ("Câu mệnh lệnh (imperatives)", "A1"),
        ("Câu cảm thán (What a...! / How...!)", "A2"),
        ("So sánh hơn / nhất / bằng", "A2"),
        ("Câu hỏi đuôi (tag questions)", "A2"),
    ]),
    ("Trọng tâm THCS (Secondary)", [
        ("Câu điều kiện loại 0, 1, 2", "A2"),
        ("Câu bị động (passive voice)", "B1"),
        ("Câu tường thuật (reported speech)", "B1"),
        ("Mệnh đề quan hệ (relative clauses)", "B1"),
        ("Câu ước (wish clauses)", "B1"),
        ("Used to / be used to", "B1"),
        ("too...to / enough / so...that / such...that", "B1"),
        ("V + to-V / V-ing (gerund & infinitive)", "B1"),
    ]),
    ("Nâng cao THPT (High school)", [
        ("Câu điều kiện loại 3 và hỗn hợp", "B2"),
        ("Đảo ngữ (inversion)", "B2"),
        ("Câu chẻ (cleft: It is... that...)", "B2"),
        ("Câu truyền khiến (causative)", "B2"),
        ("Rút gọn mệnh đề (participle clauses)", "B2"),
        ("Câu giả định (subjunctive)", "C1"),
    ]),
]

# (code, name, default_instruction, has_passage) — Implementation Notes 1.5
EXERCISE_TYPES = [
    ("pronunciation", "Phát âm", "Choose the word whose underlined part is pronounced differently.", False),
    ("stress", "Trọng âm", "Choose the word that has a different stress pattern.", False),
    ("multiple_choice", "Trắc nghiệm", "Choose the best answer A, B, C or D.", False),
    ("matching", "Matching", "Match the items in column A with the ones in column B.", False),
    ("gap_fill", "Điền vào chỗ trống", "Fill in each blank with a suitable word.", False),
    ("cloze_test", "Cloze test", "Choose the best option to complete the passage.", True),
    ("reading_true_false", "Đọc hiểu True/False", "Read the passage and decide whether the statements are True or False.", True),
    ("sign_reading", "Đọc biển báo có hình", "Look at each sign and choose the best answer.", False),
    ("word_form", "Word form", "Give the correct form of the words in brackets.", False),
    ("sentence_rewrite", "Viết lại câu", "Rewrite the sentences using the given words.", False),
]

# Implementation Notes 1.6a — school_stage_code -> (min, max, is_confirmed)
SENTENCE_LENGTH_RULES = {
    "primary": (6, 10, False),
    "secondary": (12, 14, True),
    "high_school": (14, 18, False),
}

# Implementation Notes 1.6b — (grade_min, grade_max, min_words, max_words)
PASSAGE_LENGTH_RULES = [
    (1, 2, 20, 40),
    (3, 5, 40, 80),
    (6, 7, 80, 150),
    (8, 9, 150, 250),
    (10, 12, 250, 350),
]


def _get_or_create(db: Session, model, defaults: dict | None = None, **lookup):
    instance = db.scalar(select(model).filter_by(**lookup))
    if instance:
        return instance, False
    instance = model(**lookup, **(defaults or {}))
    db.add(instance)
    db.flush()
    return instance, True


def seed_proficiency_levels(db: Session) -> dict[str, ProficiencyLevel]:
    levels: dict[str, ProficiencyLevel] = {}
    for code, rank in CEFR_LEVELS:
        level, _ = _get_or_create(db, ProficiencyLevel, code=code, defaults={"rank": rank})
        levels[code] = level
    return levels


def seed_cambridge_certificates(db: Session, levels: dict[str, ProficiencyLevel]) -> None:
    for order_no, (code, cefr_code) in enumerate(CAMBRIDGE_TO_CEFR.items(), start=1):
        _get_or_create(
            db,
            CambridgeCertificate,
            code=code,
            defaults={"order_no": order_no, "cefr_level_id": levels[cefr_code].id},
        )


def seed_school_stages(db: Session) -> dict[str, SchoolStage]:
    stages: dict[str, SchoolStage] = {}
    for code, name, order_no in SCHOOL_STAGES:
        stage, _ = _get_or_create(db, SchoolStage, code=code, defaults={"name": name, "order_no": order_no})
        stages[code] = stage
    return stages


def seed_grades(
    db: Session, stages: dict[str, SchoolStage], levels: dict[str, ProficiencyLevel]
) -> dict[int, Grade]:
    grades: dict[int, Grade] = {}
    for number, (stage_code, level_code) in GRADE_SUGGEST.items():
        grade, _ = _get_or_create(
            db,
            Grade,
            number=number,
            defaults={
                "school_stage_id": stages[stage_code].id,
                "suggested_level_id": levels[level_code].id,
            },
        )
        grades[number] = grade
    return grades


def seed_units(db: Session, grades: dict[int, Grade]) -> None:
    book_series, _ = _get_or_create(
        db, BookSeries, code="global_success", defaults={"name": "Global Success"}
    )
    for grade_number, titles in GS_UNIT_TITLES.items():
        grade = grades[grade_number]
        for order_no, title in enumerate(titles, start=1):
            _get_or_create(
                db,
                Unit,
                grade_id=grade.id,
                order_no=order_no,
                defaults={"book_series_id": book_series.id, "title": title},
            )


def seed_grammar(db: Session, levels: dict[str, ProficiencyLevel]) -> None:
    def seed_topic(code: str, name: str, groups: list[tuple[str, list[tuple[str, str]]]]) -> None:
        topic, _ = _get_or_create(db, GrammarTopic, code=code, defaults={"name": name})
        for group_order, (group_name, points) in enumerate(groups, start=1):
            group, _ = _get_or_create(
                db,
                GrammarGroup,
                topic_id=topic.id,
                order_no=group_order,
                defaults={"name": group_name},
            )
            for point_order, (point_name, min_level_code) in enumerate(points, start=1):
                _get_or_create(
                    db,
                    GrammarPoint,
                    group_id=group.id,
                    order_no=point_order,
                    defaults={"name": point_name, "min_level_id": levels[min_level_code].id},
                )

    seed_topic("tense", "Tense — 12 thì tiếng Anh", TENSE_GROUPS)
    seed_topic("sentence_structure", "Các dạng cấu trúc câu", STRUCTURE_GROUPS)


def seed_exercise_types(db: Session) -> None:
    for order_no, (code, name, instruction, has_passage) in enumerate(EXERCISE_TYPES, start=1):
        _get_or_create(
            db,
            ExerciseType,
            code=code,
            defaults={
                "name": name,
                "default_instruction": instruction,
                "has_passage": has_passage,
                "order_no": order_no,
            },
        )


def seed_length_rules(db: Session, stages: dict[str, SchoolStage]) -> None:
    for stage_code, (min_words, max_words, confirmed) in SENTENCE_LENGTH_RULES.items():
        _get_or_create(
            db,
            SentenceLengthRule,
            school_stage_id=stages[stage_code].id,
            defaults={"min_words": min_words, "max_words": max_words, "is_confirmed": confirmed},
        )
    for grade_min, grade_max, min_words, max_words in PASSAGE_LENGTH_RULES:
        _get_or_create(
            db,
            PassageLengthRule,
            grade_min=grade_min,
            grade_max=grade_max,
            defaults={"min_words": min_words, "max_words": max_words},
        )


def seed_admin_user(db: Session) -> None:
    settings = get_settings()
    existing = db.scalar(select(User).where(User.role == UserRole.ADMIN))
    if existing:
        return
    db.add(
        User(
            email=settings.seed_admin_email,
            password_hash=hash_password(settings.seed_admin_password),
            full_name="Admin",
            role=UserRole.ADMIN,
            is_active=True,
        )
    )


def run_seed(db: Session) -> None:
    levels = seed_proficiency_levels(db)
    seed_cambridge_certificates(db, levels)
    stages = seed_school_stages(db)
    grades = seed_grades(db, stages, levels)
    seed_units(db, grades)
    seed_grammar(db, levels)
    seed_exercise_types(db)
    seed_length_rules(db, stages)
    seed_admin_user(db)
    db.commit()


def main() -> None:
    db = SessionLocal()
    try:
        run_seed(db)
        print("Seed OK.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
