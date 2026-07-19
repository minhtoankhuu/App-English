import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.deps import require_any_role
from app.models.academic import CambridgeCertificate, Grade, ProficiencyLevel, SchoolStage, Unit
from app.models.exercise import ExerciseType, PassageLengthRule, SentenceLengthRule
from app.models.grammar import GrammarGroup, GrammarPoint, GrammarTopic
from app.schemas.catalog import (
    CambridgeCertificateOut,
    ExerciseTypeOut,
    GradeOut,
    GrammarTopicOut,
    PassageLengthRuleOut,
    ProficiencyLevelOut,
    SchoolStageOut,
    SentenceLengthRuleOut,
    UnitOut,
)

router = APIRouter(prefix="/catalog", tags=["catalog"], dependencies=[Depends(require_any_role)])


@router.get("/school-stages", response_model=list[SchoolStageOut])
def list_school_stages(db: Session = Depends(get_db)) -> list[SchoolStage]:
    return list(db.scalars(select(SchoolStage).order_by(SchoolStage.order_no)))


@router.get("/proficiency-levels", response_model=list[ProficiencyLevelOut])
def list_proficiency_levels(db: Session = Depends(get_db)) -> list[ProficiencyLevel]:
    return list(db.scalars(select(ProficiencyLevel).order_by(ProficiencyLevel.rank)))


@router.get("/cambridge-certificates", response_model=list[CambridgeCertificateOut])
def list_cambridge_certificates(db: Session = Depends(get_db)) -> list[CambridgeCertificate]:
    stmt = (
        select(CambridgeCertificate)
        .options(selectinload(CambridgeCertificate.cefr_level))
        .order_by(CambridgeCertificate.order_no)
    )
    return list(db.scalars(stmt))


@router.get("/grades", response_model=list[GradeOut])
def list_grades(db: Session = Depends(get_db)) -> list[Grade]:
    stmt = (
        select(Grade)
        .options(selectinload(Grade.school_stage), selectinload(Grade.suggested_level))
        .order_by(Grade.number)
    )
    return list(db.scalars(stmt))


@router.get("/grades/{grade_id}/units", response_model=list[UnitOut])
def list_units_for_grade(grade_id: uuid.UUID, db: Session = Depends(get_db)) -> list[Unit]:
    grade = db.get(Grade, grade_id)
    if grade is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy khối lớp")
    stmt = select(Unit).where(Unit.grade_id == grade_id).order_by(Unit.order_no)
    return list(db.scalars(stmt))


@router.get("/grammar-topics", response_model=list[GrammarTopicOut])
def list_grammar_topics(db: Session = Depends(get_db)) -> list[GrammarTopic]:
    stmt = select(GrammarTopic).options(
        selectinload(GrammarTopic.groups)
        .selectinload(GrammarGroup.points)
        .selectinload(GrammarPoint.min_level)
    )
    return list(db.scalars(stmt))


@router.get("/exercise-types", response_model=list[ExerciseTypeOut])
def list_exercise_types(db: Session = Depends(get_db)) -> list[ExerciseType]:
    return list(db.scalars(select(ExerciseType).order_by(ExerciseType.order_no)))


@router.get("/sentence-length-rules", response_model=list[SentenceLengthRuleOut])
def list_sentence_length_rules(db: Session = Depends(get_db)) -> list[SentenceLengthRule]:
    stmt = select(SentenceLengthRule).options(selectinload(SentenceLengthRule.school_stage))
    return list(db.scalars(stmt))


@router.get("/passage-length-rules", response_model=list[PassageLengthRuleOut])
def list_passage_length_rules(db: Session = Depends(get_db)) -> list[PassageLengthRule]:
    stmt = select(PassageLengthRule).order_by(PassageLengthRule.grade_min)
    return list(db.scalars(stmt))
