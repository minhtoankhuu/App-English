export interface SchoolStageOut {
  id: string;
  code: string;
  name: string;
  order_no: number;
}

export interface ProficiencyLevelOut {
  id: string;
  code: string;
  rank: number;
}

export interface CambridgeCertificateOut {
  id: string;
  code: string;
  order_no: number;
  cefr_level: ProficiencyLevelOut;
}

export interface GradeOut {
  id: string;
  number: number;
  school_stage: SchoolStageOut;
  suggested_level: ProficiencyLevelOut;
}

export interface UnitOut {
  id: string;
  order_no: number;
  title: string;
}

export interface GrammarPointOut {
  id: string;
  name: string;
  order_no: number;
  min_level: ProficiencyLevelOut;
}

export interface GrammarGroupOut {
  id: string;
  name: string;
  order_no: number;
  points: GrammarPointOut[];
}

export interface GrammarTopicOut {
  id: string;
  code: string;
  name: string;
  groups: GrammarGroupOut[];
}

export interface ExerciseTypeOut {
  id: string;
  code: string;
  name: string;
  default_instruction: string;
  has_passage: boolean;
  order_no: number;
}

export interface SentenceLengthRuleOut {
  school_stage: SchoolStageOut;
  min_words: number;
  max_words: number;
  is_confirmed: boolean;
}

export interface PassageLengthRuleOut {
  grade_min: number;
  grade_max: number;
  min_words: number;
  max_words: number;
}
