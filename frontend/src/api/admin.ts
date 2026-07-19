import { apiGet, apiPost, apiRequest } from "./client";
import type { TeacherCreateRequest, TeacherOut, TeacherUpdateRequest } from "../types/admin";

export const listTeachers = (): Promise<TeacherOut[]> => apiGet("/admin/teachers");

export const createTeacher = (payload: TeacherCreateRequest): Promise<TeacherOut> =>
  apiPost("/admin/teachers", payload);

export const updateTeacher = (teacherId: string, payload: TeacherUpdateRequest): Promise<TeacherOut> =>
  apiRequest(`/admin/teachers/${teacherId}`, { method: "PATCH", body: JSON.stringify(payload) });
