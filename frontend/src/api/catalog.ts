import { apiGet } from "./client";
import type {
  CambridgeCertificateOut,
  ExerciseTypeOut,
  GradeOut,
  GrammarTopicOut,
  PassageLengthRuleOut,
  ProficiencyLevelOut,
  SchoolStageOut,
  SentenceLengthRuleOut,
  UnitOut,
} from "../types/catalog";

export const listSchoolStages = (): Promise<SchoolStageOut[]> => apiGet("/catalog/school-stages");

export const listProficiencyLevels = (): Promise<ProficiencyLevelOut[]> => apiGet("/catalog/proficiency-levels");

export const listCambridgeCertificates = (): Promise<CambridgeCertificateOut[]> =>
  apiGet("/catalog/cambridge-certificates");

export const listGrades = (): Promise<GradeOut[]> => apiGet("/catalog/grades");

export const listUnitsForGrade = (gradeId: string): Promise<UnitOut[]> =>
  apiGet(`/catalog/grades/${gradeId}/units`);

export const listGrammarTopics = (): Promise<GrammarTopicOut[]> => apiGet("/catalog/grammar-topics");

export const listExerciseTypes = (): Promise<ExerciseTypeOut[]> => apiGet("/catalog/exercise-types");

export const listSentenceLengthRules = (): Promise<SentenceLengthRuleOut[]> =>
  apiGet("/catalog/sentence-length-rules");

export const listPassageLengthRules = (): Promise<PassageLengthRuleOut[]> =>
  apiGet("/catalog/passage-length-rules");
