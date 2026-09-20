import type { TokenResponse, VMSummary } from "./types";

const TOKEN_STORAGE_KEY = "virtdeck.access_token";

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export function getToken(): string | null {
  return window.localStorage.getItem(TOKEN_STORAGE_KEY);
}

export function setToken(token: string | null): void {
  if (token === null) {
    window.localStorage.removeItem(TOKEN_STORAGE_KEY);
  } else {
    window.localStorage.setItem(TOKEN_STORAGE_KEY, token);
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers = new Headers(init.headers);
  headers.set("Content-Type", "application/json");
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`/api${path}`, { ...init, headers });

  if (!response.ok) {
    const body = await response.json().catch(() => ({}) as Record<string, unknown>);
    const detail = typeof body.detail === "string" ? body.detail : response.statusText;
    throw new ApiError(response.status, detail);
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export async function login(email: string, password: string): Promise<TokenResponse> {
  return request<TokenResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export async function listVMs(): Promise<VMSummary[]> {
  return request<VMSummary[]>("/vms");
}

export async function getVM(uuid: string): Promise<VMSummary> {
  return request<VMSummary>(`/vms/${uuid}`);
}

export async function startVM(uuid: string): Promise<VMSummary> {
  return request<VMSummary>(`/vms/${uuid}/start`, { method: "POST" });
}

export async function shutdownVM(uuid: string): Promise<VMSummary> {
  return request<VMSummary>(`/vms/${uuid}/shutdown`, { method: "POST" });
}

export async function forceStopVM(uuid: string): Promise<VMSummary> {
  return request<VMSummary>(`/vms/${uuid}/force-stop`, { method: "POST" });
}

export async function rebootVM(uuid: string): Promise<VMSummary> {
  return request<VMSummary>(`/vms/${uuid}/reboot`, { method: "POST" });
}

export async function deleteVM(uuid: string): Promise<void> {
  return request<void>(`/vms/${uuid}`, { method: "DELETE" });
}
