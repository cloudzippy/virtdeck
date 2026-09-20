import { useVMs } from "../hooks/useVMs";
import { VMCard } from "./VMCard";

export function VMList(): JSX.Element {
  const { vms, loading, error, refresh } = useVMs();

  if (loading) {
    return <p>Loading VMs…</p>;
  }

  if (error) {
    return <p role="alert">{error}</p>;
  }

  if (vms.length === 0) {
    return <p>No VMs found.</p>;
  }

  return (
    <ul className="vm-list">
      {vms.map((vm) => (
        <VMCard key={vm.uuid} vm={vm} onChange={refresh} />
      ))}
    </ul>
  );
}
