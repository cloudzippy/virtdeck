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
  /** `null` means unassigned: only admins can see the VM until an owner is set. */
  owner_id: string | null;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}
