import { apiGet, apiPost } from "./client";
import type { LoginRequest, UserOut } from "../types/auth";

export function login(payload: LoginRequest): Promise<UserOut> {
  return apiPost<UserOut>("/auth/login", payload);
}

export function logout(): Promise<void> {
  return apiPost<void>("/auth/logout");
}

export function fetchCurrentUser(): Promise<UserOut> {
  return apiGet<UserOut>("/auth/me");
}
