import uuid

from pydantic import BaseModel, ConfigDict


class SchoolStageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    order_no: int


class ProficiencyLevelOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    rank: int


class CambridgeCertificateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    order_no: int
    cefr_level: ProficiencyLevelOut


class GradeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    number: int
    school_stage: SchoolStageOut
    suggested_level: ProficiencyLevelOut


class UnitOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    order_no: int
    title: str


class GrammarPointOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    order_no: int
    min_level: ProficiencyLevelOut


class GrammarGroupOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    order_no: int
    points: list[GrammarPointOut]


class GrammarTopicOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    groups: list[GrammarGroupOut]


class ExerciseTypeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    default_instruction: str
    has_passage: bool
    order_no: int


class SentenceLengthRuleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    school_stage: SchoolStageOut
    min_words: int
    max_words: int
    is_confirmed: bool


class PassageLengthRuleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    grade_min: int
    grade_max: int
    min_words: int
    max_words: int
