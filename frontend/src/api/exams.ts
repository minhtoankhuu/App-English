import { apiGet, apiPost, apiRequest } from "./client";
import type {
  BlockCreateRequest,
  BlockOut,
  BlockUpdateRequest,
  ExamCreateRequest,
  ExamDetailOut,
  ExamSummaryOut,
  ExportConfigRequest,
  QuestionFlagsUpdateRequest,
  QuestionOut,
} from "../types/exam";
import type { ExamPreviewOut } from "../types/examPreview";

export const listExams = (): Promise<ExamSummaryOut[]> => apiGet("/exams");

export const getExam = (examId: string): Promise<ExamDetailOut> => apiGet(`/exams/${examId}`);

export const getExamPreview = (examId: string): Promise<ExamPreviewOut> => apiGet(`/exams/${examId}/preview`);

export const createExam = (payload: ExamCreateRequest): Promise<ExamDetailOut> => apiPost("/exams", payload);

export const setGrammarSelection = (examId: string, grammarPointIds: string[]): Promise<ExamDetailOut> =>
  apiRequest(`/exams/${examId}/grammar-selection`, {
    method: "PUT",
    body: JSON.stringify({ grammar_point_ids: grammarPointIds }),
  });

export const addBlock = (examId: string, payload: BlockCreateRequest): Promise<BlockOut> =>
  apiPost(`/exams/${examId}/blocks`, payload);

export const updateBlock = (examId: string, blockId: string, payload: BlockUpdateRequest): Promise<BlockOut> =>
  apiRequest(`/exams/${examId}/blocks/${blockId}`, { method: "PATCH", body: JSON.stringify(payload) });

export const deleteBlock = (examId: string, blockId: string): Promise<void> =>
  apiRequest(`/exams/${examId}/blocks/${blockId}`, { method: "DELETE" });

export const reorderBlocks = (examId: string, blockIds: string[]): Promise<ExamDetailOut> =>
  apiPost(`/exams/${examId}/blocks/reorder`, { block_ids: blockIds });

export const generateExam = (examId: string): Promise<ExamDetailOut> => apiPost(`/exams/${examId}/generate`);

export const updateQuestionFlags = (
  examId: string,
  questionId: string,
  payload: QuestionFlagsUpdateRequest,
): Promise<QuestionOut> =>
  apiRequest(`/exams/${examId}/questions/${questionId}`, { method: "PATCH", body: JSON.stringify(payload) });

export const regenerateQuestion = (examId: string, questionId: string): Promise<QuestionOut> =>
  apiPost(`/exams/${examId}/questions/${questionId}/regenerate`);

export const completeReview = (examId: string): Promise<ExamDetailOut> =>
  apiPost(`/exams/${examId}/complete-review`);

export const saveExportConfig = (examId: string, payload: ExportConfigRequest): Promise<ExamDetailOut> =>
  apiPost(`/exams/${examId}/export-config`, payload);

export function downloadExportUrl(examId: string, variant: string): string {
  const base: string = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
  return `${base}/exams/${examId}/export.docx?variant=${encodeURIComponent(variant)}`;
}
