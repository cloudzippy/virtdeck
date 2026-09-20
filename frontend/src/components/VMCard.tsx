import { useState } from "react";
import { ApiError, shutdownVM, startVM } from "../api/client";
import type { VMSummary } from "../api/types";

interface VMCardProps {
  vm: VMSummary;
  onChange: () => void;
}

export function VMCard({ vm, onChange }: VMCardProps): JSX.Element {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isRunning = vm.state === "running";

  const handleToggle = async (): Promise<void> => {
    setPending(true);
    setError(null);
    try {
      if (isRunning) {
        await shutdownVM(vm.uuid);
      } else {
        await startVM(vm.uuid);
      }
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
      <button type="button" onClick={handleToggle} disabled={pending}>
        {isRunning ? "Shut down" : "Start"}
      </button>
      {error && <p className="vm-card__error">{error}</p>}
    </li>
  );
}
