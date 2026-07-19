"""Import tất cả model để Alembic autogenerate và Base.metadata nhận diện đủ bảng."""

from app.models.academic import (
    BookSeries,
    CambridgeCertificate,
    Grade,
    ProficiencyLevel,
    SchoolStage,
    Unit,
)
from app.models.base import Base
from app.models.exercise import ExerciseType, PassageLengthRule, SentenceLengthRule
from app.models.grammar import GrammarGroup, GrammarPoint, GrammarTopic
from app.models.user import User, UserRole

__all__ = [
    "Base",
    "User",
    "UserRole",
    "SchoolStage",
    "ProficiencyLevel",
    "CambridgeCertificate",
    "Grade",
    "BookSeries",
    "Unit",
    "GrammarTopic",
    "GrammarGroup",
    "GrammarPoint",
    "ExerciseType",
    "SentenceLengthRule",
    "PassageLengthRule",
]
