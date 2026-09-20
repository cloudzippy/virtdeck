import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useAuth } from "../src/hooks/useAuth";
import * as client from "../src/api/client";

describe("useAuth", () => {
  beforeEach(() => {
    window.localStorage.clear();
    vi.restoreAllMocks();
  });

  it("starts unauthenticated when there is no stored token", () => {
    const { result } = renderHook(() => useAuth());
    expect(result.current.isAuthenticated).toBe(false);
  });

  it("becomes authenticated after a successful login", async () => {
    vi.spyOn(client, "login").mockResolvedValue({ access_token: "abc123", token_type: "bearer" });

    const { result } = renderHook(() => useAuth());
    await act(async () => {
      await result.current.login("user@example.com", "password");
    });

    await waitFor(() => expect(result.current.isAuthenticated).toBe(true));
    expect(client.getToken()).toBe("abc123");
  });

  it("clears the token on logout", async () => {
    vi.spyOn(client, "login").mockResolvedValue({ access_token: "abc123", token_type: "bearer" });

    const { result } = renderHook(() => useAuth());
    await act(async () => {
      await result.current.login("user@example.com", "password");
    });
    act(() => {
      result.current.logout();
    });

    expect(result.current.isAuthenticated).toBe(false);
    expect(client.getToken()).toBeNull();
  });
});
