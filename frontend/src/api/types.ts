export type DomainState =
  | "unknown"
  | "running"
  | "blocked"
  | "paused"
  | "shutting_down"
  | "shutoff"
  | "crashed"
  | "suspended";

export interface VMSummary {
  uuid: string;
  name: string;
  state: DomainState;
  vcpus: number;
  memory_kib: number;
  persistent: boolean;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}
