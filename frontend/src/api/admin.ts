import { apiGet, apiPost, apiRequest, apiUpload } from "./client";
import type {
  AIProviderConfigOut,
  AIProviderConfigUpdateRequest,
  KnowledgeChunkAdminOut,
  KnowledgeDocumentOut,
  TeacherCreateRequest,
  TeacherOut,
  TeacherUpdateRequest,
} from "../types/admin";

export const listTeachers = (): Promise<TeacherOut[]> => apiGet("/admin/teachers");

export const createTeacher = (payload: TeacherCreateRequest): Promise<TeacherOut> =>
  apiPost("/admin/teachers", payload);

export const updateTeacher = (teacherId: string, payload: TeacherUpdateRequest): Promise<TeacherOut> =>
  apiRequest(`/admin/teachers/${teacherId}`, { method: "PATCH", body: JSON.stringify(payload) });

export const deleteTeacher = (teacherId: string): Promise<void> =>
  apiRequest(`/admin/teachers/${teacherId}`, { method: "DELETE" });

export const listKnowledgeDocuments = (): Promise<KnowledgeDocumentOut[]> => apiGet("/admin/knowledge-documents");

export type KnowledgeDocumentSource = { unitId: string } | { grammarPointId: string };

export const uploadKnowledgeDocument = (source: KnowledgeDocumentSource, file: File): Promise<KnowledgeDocumentOut> => {
  const formData = new FormData();
  if ("unitId" in source) {
    formData.append("unit_id", source.unitId);
  } else {
    formData.append("grammar_point_id", source.grammarPointId);
  }
  formData.append("file", file);
  return apiUpload("/admin/knowledge-documents", formData);
};

export const updateKnowledgeDocument = (documentId: string, isPublished: boolean): Promise<KnowledgeDocumentOut> =>
  apiRequest(`/admin/knowledge-documents/${documentId}`, {
    method: "PATCH",
    body: JSON.stringify({ is_published: isPublished }),
  });

export const deleteKnowledgeDocument = (documentId: string): Promise<void> =>
  apiRequest(`/admin/knowledge-documents/${documentId}`, { method: "DELETE" });

export const listKnowledgeDocumentChunks = (documentId: string): Promise<KnowledgeChunkAdminOut[]> =>
  apiGet(`/admin/knowledge-documents/${documentId}/chunks`);

export const getAIConfig = (): Promise<AIProviderConfigOut | null> => apiGet("/admin/ai-config");

export const updateAIConfig = (payload: AIProviderConfigUpdateRequest): Promise<AIProviderConfigOut> =>
  apiRequest("/admin/ai-config", { method: "PUT", body: JSON.stringify(payload) });

export const testAIConfig = (apiKey: string): Promise<{ ok: boolean; message: string }> =>
  apiPost("/admin/ai-config/test", { api_key: apiKey });
