import { apiGet, apiPost, apiRequest, apiUpload } from "./client";
import type {
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

export const uploadKnowledgeDocument = (unitId: string, file: File): Promise<KnowledgeDocumentOut> => {
  const formData = new FormData();
  formData.append("unit_id", unitId);
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
