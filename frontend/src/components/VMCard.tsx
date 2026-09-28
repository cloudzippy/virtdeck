import { useState } from "react";
import { ApiError, pauseVM, resumeVM, shutdownVM, startVM } from "../api/client";
import type { DomainState, VMSummary } from "../api/types";

interface VMCardProps {
  vm: VMSummary;
  onChange: () => void;
}

interface VMAction {
  label: string;
  run: (uuid: string) => Promise<VMSummary>;
}

// "blocked" is a running guest waiting on I/O, so it gets the same actions as "running".
// A paused guest can't act on an ACPI shutdown request, so it is only offered Resume.
function actionsFor(state: DomainState): VMAction[] {
  switch (state) {
    case "running":
    case "blocked":
      return [
        { label: "Shut down", run: shutdownVM },
        { label: "Pause", run: pauseVM },
      ];
    case "paused":
      return [{ label: "Resume", run: resumeVM }];
    default:
      return [{ label: "Start", run: startVM }];
  }
}

export function VMCard({ vm, onChange }: VMCardProps): JSX.Element {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleAction = async (action: VMAction): Promise<void> => {
    setPending(true);
    setError(null);
    try {
      await action.run(vm.uuid);
      onChange();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Operation failed");
    } finally {
      setPending(false);
    }
  };

  return (
    <li className="vm-card">
      <div className="vm-card__header">
        <span className="vm-card__name">{vm.name}</span>
        <span className={`vm-card__state vm-card__state--${vm.state}`}>{vm.state}</span>
      </div>
      <dl className="vm-card__details">
        <dt>vCPUs</dt>
        <dd>{vm.vcpus}</dd>
        <dt>Memory</dt>
        <dd>{Math.round(vm.memory_kib / 1024)} MiB</dd>
      </dl>
      {actionsFor(vm.state).map((action) => (
        <button
          key={action.label}
          type="button"
          onClick={() => void handleAction(action)}
          disabled={pending}
        >
          {action.label}
        </button>
      ))}
      {error && <p className="vm-card__error">{error}</p>}
    </li>
  );
}
