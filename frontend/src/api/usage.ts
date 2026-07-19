import { apiGet } from "./client";
import type { UsageStatus } from "../types/usage";

export const getMyUsage = (): Promise<UsageStatus> => apiGet("/usage/me");
