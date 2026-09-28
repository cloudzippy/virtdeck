import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { VMCard } from "../src/components/VMCard";
import * as client from "../src/api/client";
import type { DomainState, VMSummary } from "../src/api/types";

function makeVM(state: DomainState): VMSummary {
  return {
    uuid: "11111111-1111-1111-1111-111111111111",
    name: "web-01",
    state,
    vcpus: 2,
    memory_kib: 2097152,
    persistent: true,
  };
}

function buttonLabels(): string[] {
  return screen.getAllByRole("button").map((button) => button.textContent ?? "");
}

describe("VMCard", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it.each<[DomainState, string[]]>([
    ["running", ["Shut down", "Pause"]],
    ["blocked", ["Shut down", "Pause"]],
    ["paused", ["Resume"]],
    ["shutoff", ["Start"]],
    ["crashed", ["Start"]],
  ])("offers the right actions for a %s VM", (state, expected) => {
    render(<VMCard vm={makeVM(state)} onChange={vi.fn()} />);

    expect(buttonLabels()).toEqual(expected);
  });

  it("pauses a running VM and refreshes", async () => {
    const pause = vi.spyOn(client, "pauseVM").mockResolvedValue(makeVM("paused"));
    const onChange = vi.fn();
    render(<VMCard vm={makeVM("running")} onChange={onChange} />);

    fireEvent.click(screen.getByRole("button", { name: "Pause" }));

    await waitFor(() => expect(onChange).toHaveBeenCalledOnce());
    expect(pause).toHaveBeenCalledWith("11111111-1111-1111-1111-111111111111");
  });

  it("resumes a paused VM and refreshes", async () => {
    const resume = vi.spyOn(client, "resumeVM").mockResolvedValue(makeVM("running"));
    const onChange = vi.fn();
    render(<VMCard vm={makeVM("paused")} onChange={onChange} />);

    fireEvent.click(screen.getByRole("button", { name: "Resume" }));

    await waitFor(() => expect(onChange).toHaveBeenCalledOnce());
    expect(resume).toHaveBeenCalledWith("11111111-1111-1111-1111-111111111111");
  });

  it("disables every action while a request is in flight", async () => {
    let finish: (vm: VMSummary) => void = () => undefined;
    vi.spyOn(client, "pauseVM").mockReturnValue(
      new Promise<VMSummary>((resolve) => {
        finish = resolve;
      }),
    );
    render(<VMCard vm={makeVM("running")} onChange={vi.fn()} />);

    fireEvent.click(screen.getByRole("button", { name: "Pause" }));

    for (const button of screen.getAllByRole("button")) {
      expect(button).toBeDisabled();
    }
    finish(makeVM("paused"));
    await waitFor(() => expect(screen.getByRole("button", { name: "Pause" })).toBeEnabled());
  });

  it("shows the API error and does not refresh when the action fails", async () => {
    vi.spyOn(client, "pauseVM").mockRejectedValue(
      new client.ApiError(409, "cannot pause domain while it is shutoff"),
    );
    const onChange = vi.fn();
    render(<VMCard vm={makeVM("running")} onChange={onChange} />);

    fireEvent.click(screen.getByRole("button", { name: "Pause" }));

    expect(await screen.findByText(/cannot pause domain/)).toBeInTheDocument();
    expect(onChange).not.toHaveBeenCalled();
  });
});
