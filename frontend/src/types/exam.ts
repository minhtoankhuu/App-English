export type SourceType = "global_success" | "common_knowledge" | "cambridge";
export type ExamStatus = "draft" | "reviewed" | "ready";
export type ExportMode = "plain" | "answer_key";
export type Difficulty = "nhan_biet" | "thong_hieu" | "van_dung" | "hon_hop";

export interface RefOut {
  id: string;
  code: string;
}

export interface ExerciseTypeRefOut {
  id: string;
  code: string;
  name: string;
  has_passage: boolean;
}

export interface QuestionOption {
  label: string;
  text: string;
  is_correct: boolean;
}

export interface QuestionOut {
  id: string;
  order_no: number;
  prompt_text: string;
  passage_text: string | null;
  options: QuestionOption[] | null;
  answer_text: string;
  explanation: string;
  target_knowledge: string;
  level: RefOut;
  source_ref: string;
  warnings: string[];
  is_approved: boolean;
  is_locked: boolean;
  part_id: string | null;
}

export interface BlockPartOut {
  id: string;
  order_no: number;
  title: string;
  instruction: string | null;
  question_count: number;
  prompt_override: string | null;
}

export interface BlockPartCreateRequest {
  title: string;
  instruction?: string | null;
  question_count: number;
  prompt_override?: string | null;
}

export type BlockPartUpdateRequest = Partial<BlockPartCreateRequest>;

export interface BlockOut {
  id: string;
  order_no: number;
  exercise_type: ExerciseTypeRefOut;
  title: string;
  instruction: string | null;
  question_count: number;
  points: string;
  difficulty: Difficulty;
  level_override: RefOut | null;
  shuffle_questions: boolean;
  shuffle_answers: boolean;
  prompt_override: string | null;
  passage_word_target: number | null;
  questions: QuestionOut[];
  parts: BlockPartOut[];
}

export interface ExamSummaryOut {
  id: string;
  title: string;
  status: ExamStatus;
  grade_number: number;
  level_code: string;
  total_questions: number;
  total_points: string;
  export_mode: ExportMode | null;
  variant_count: number;
  updated_at: string;
}

export interface ExamDetailOut {
  id: string;
  title: string;
  status: ExamStatus;
  source_type: SourceType;
  grade_id: string;
  level: RefOut;
  unit_id: string | null;
  grammar_topic_id: string | null;
  cambridge_certificate_id: string | null;
  extra_prompt: string | null;
  export_mode: ExportMode | null;
  variant_count: number;
  grammar_point_ids: string[];
  blocks: BlockOut[];
}

export interface ExamCreateRequest {
  title: string;
  grade_id: string;
  level_id: string;
  source_type: SourceType;
  unit_id?: string | null;
  grammar_topic_id?: string | null;
  cambridge_certificate_id?: string | null;
  extra_prompt?: string | null;
}

export interface BlockCreateRequest {
  exercise_type_id: string;
  title: string;
  instruction?: string | null;
  question_count: number;
  points: number;
  difficulty?: Difficulty;
  level_override_id?: string | null;
  shuffle_questions?: boolean;
  shuffle_answers?: boolean;
  prompt_override?: string | null;
  passage_word_target?: number | null;
}

export type BlockUpdateRequest = Partial<BlockCreateRequest>;

export interface QuestionFlagsUpdateRequest {
  is_approved?: boolean;
  is_locked?: boolean;
}

export interface ExportConfigRequest {
  export_mode: ExportMode;
  variant_count: number;
}
