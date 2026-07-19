import type { AuditLogPage } from "../types/audit";
import { apiGet } from "./client";

export function listAuditLogs(limit: number, offset: number): Promise<AuditLogPage> {
  return apiGet(`/admin/audit-logs?limit=${limit}&offset=${offset}`);
}
