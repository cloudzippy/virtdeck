import { VMList } from "../components/VMList";
import { useAuth } from "../hooks/useAuth";

export function DashboardPage(): JSX.Element {
  const { logout } = useAuth();

  return (
    <main className="dashboard-page">
      <header>
        <h1>VirtDeck</h1>
        <button type="button" onClick={logout}>
          Sign out
        </button>
      </header>
      <VMList />
    </main>
  );
}
