"""Import tất cả model để Alembic autogenerate và Base.metadata nhận diện đủ bảng."""

from app.models.academic import (
    BookSeries,
    CambridgeCertificate,
    Grade,
    ProficiencyLevel,
    SchoolStage,
    Unit,
)
from app.models.audit import AuditLog
from app.models.base import Base
from app.models.exam import (
    Difficulty,
    Exam,
    ExamBlock,
    ExamBlockPart,
    ExamGrammarSelection,
    ExamStatus,
    ExamVariant,
    ExportMode,
    Question,
    SourceType,
)
from app.models.exercise import ExerciseType, PassageLengthRule, SentenceLengthRule
from app.models.grammar import GrammarGroup, GrammarPoint, GrammarTopic
from app.models.knowledge import DocumentChunkType, KnowledgeChunk, KnowledgeDocument
from app.models.user import User, UserRole
from app.models.usage import DailyUsage

__all__ = [
    "Base",
    "AuditLog",
    "User",
    "UserRole",
    "DailyUsage",
    "KnowledgeDocument",
    "KnowledgeChunk",
    "DocumentChunkType",
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
    "Exam",
    "ExamBlock",
    "ExamBlockPart",
    "ExamGrammarSelection",
    "ExamVariant",
    "Question",
    "SourceType",
    "ExamStatus",
    "ExportMode",
    "Difficulty",
]
