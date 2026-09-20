# Architecture

## Layering

```
frontend (React/Vite)  --HTTP/JSON-->  backend/app/api  -->  backend/app/services  -->  backend/app/libvirt  -->  libvirt daemon
                                              |
                                              v
                                        backend/app/models (SQLAlchemy / Postgres or SQLite)
```

- **`api/`** — FastAPI routers. Request/response validation only; no business logic, no libvirt calls.
- **`services/`** — business logic, authorization decisions, and audit logging. Calls into `libvirt/` for VM state and `models/` for persistence.
- **`libvirt/`** — the only place `import libvirt` is allowed. `connection.py` owns the single shared connection; `domains.py` wraps domain (VM) operations and translates `libvirt.libvirtError` into typed exceptions (`libvirt/exceptions.py`).
- **`models/`** — SQLAlchemy ORM models for data VirtDeck itself owns (users, audit log). VM state itself is *not* duplicated in the database — it's read live from libvirt on each request.

Blocking libvirt calls are run off the event loop via `asyncio.to_thread` in the service layer (see `services/vm_service.py`), so FastAPI's async handlers never block on them.

## Auth and RBAC

- JWT access tokens (`core/security.py`), Argon2 password hashing.
- Three roles: `admin`, `operator`, `viewer`. `viewer` can read VM state; `operator` and `admin` can start/stop/reboot; only `admin` can delete (undefine) a VM. Enforced via the `require_role(...)` dependency in `api/deps.py`.

## Desktop app (planned)

The frontend is a plain React/Vite SPA that only talks to the backend over `/api`. The planned desktop client wraps this same frontend build in a native shell (Tauri) that points at a VirtDeck server — no separate desktop-only backend or libvirt access path. This keeps a single backend implementation for both web and desktop.

## Testing

- Unit tests (`backend/tests/`) mock the `app.libvirt` layer directly (see `tests/conftest.py`, `tests/fakes/`) — no real hypervisor needed. A stub `libvirt` module is substituted automatically when `libvirt-python` isn't installed (e.g. a dev machine without `libvirt-dev`), so the test suite runs anywhere.
- Integration tests (`backend/tests/integration/`, marked `@pytest.mark.integration`) exercise the real `libvirt-python` bindings against libvirt's built-in `test:///default` driver — no real KVM host required, but real `libvirt-dev` + `libvirt-python` are. They self-skip when those aren't present.

## Deployment

- `deploy/Dockerfile.backend` / `Dockerfile.frontend` + `deploy/docker-compose.yml` for containerized deployment. The backend container talks to the **host's** libvirt daemon over its Unix socket (mounted in), rather than running its own `libvirtd`.
- `deploy/systemd/virtdeck.service` for a direct host install (no containers), running as a dedicated `virtdeck` user in the `libvirt` group.
