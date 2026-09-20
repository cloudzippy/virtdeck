import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { VMList } from "../src/components/VMList";
import * as client from "../src/api/client";
import type { VMSummary } from "../src/api/types";

const SAMPLE: VMSummary = {
  uuid: "11111111-1111-1111-1111-111111111111",
  name: "web-01",
  state: "running",
  vcpus: 2,
  memory_kib: 2097152,
  persistent: true,
};

describe("VMList", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("shows a loading state, then renders VMs", async () => {
    vi.spyOn(client, "listVMs").mockResolvedValue([SAMPLE]);

    render(<VMList />);

    expect(screen.getByText(/loading/i)).toBeInTheDocument();
    expect(await screen.findByText("web-01")).toBeInTheDocument();
    expect(screen.getByText("running")).toBeInTheDocument();
  });

  it("shows an error message when the request fails", async () => {
    vi.spyOn(client, "listVMs").mockRejectedValue(new client.ApiError(502, "backend unreachable"));

    render(<VMList />);

    expect(await screen.findByRole("alert")).toHaveTextContent("backend unreachable");
  });

  it("shows an empty state when there are no VMs", async () => {
    vi.spyOn(client, "listVMs").mockResolvedValue([]);

    render(<VMList />);

    expect(await screen.findByText(/no vms found/i)).toBeInTheDocument();
  });
});
