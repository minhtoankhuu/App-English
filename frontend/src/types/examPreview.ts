export interface PreviewQuestionOut {
  question_number: number;
  prompt_text: string | null;
  passage_text: string | null;
  is_placeholder: boolean;
  part_number: number | null;
  part_title: string | null;
  part_instruction: string | null;
}

export interface PreviewBlockOut {
  block_id: string;
  section_number: number;
  section_label: string;
  title: string;
  instruction: string | null;
  question_start: number | null;
  question_end: number | null;
  question_count: number;
  points: string;
  continuation: boolean;
  questions: PreviewQuestionOut[];
}

export interface PreviewPageOut {
  page_number: number;
  blocks: PreviewBlockOut[];
}

export interface ExamPreviewOut {
  exam_id: string;
  title: string;
  grade_number: number;
  level_code: string;
  total_questions: number;
  total_points: string;
  page_count: number;
  pages: PreviewPageOut[];
}
