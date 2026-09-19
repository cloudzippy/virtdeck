# AGENTS.md

Guidance for AI coding agents (and human contributors) working on **VirtDeck**.

## Project overview

**VirtDeck** is a web-based virtual machine management tool for Linux hosts running **KVM/QEMU** through **libvirt**. It lets users create, control, monitor, and access VMs from a browser.

Tagline: *Manage every VM from one place.*

### Core capabilities

- VM lifecycle: create, start, stop, reboot, pause, delete
- Browser console access (noVNC / SPICE)
- Storage pools and disk images
- Virtual networks and bridges
- Snapshots and backups
- Users, roles, and audit logging

## Tech stack

> Update this section if the stack changes. Agents should follow what is here, not assume alternatives.

| Layer | Technology |
|---|---|
| Backend API | Python 3.11+, FastAPI |
| Hypervisor access | `libvirt-python` (libvirt API) |
| Frontend | React + TypeScript, Vite |
| Console | noVNC via a WebSocket proxy |
| Database | SQLite (dev), PostgreSQL (prod) via SQLAlchemy + Alembic |
| Auth | JWT sessions, role-based access control |
| Testing | pytest (backend), Vitest + Playwright (frontend) |
| Packaging | Docker for the app, systemd unit for host installs |

## Repository layout

```
virtdeck/
├── backend/
│   ├── app/
│   │   ├── api/          # FastAPI routers (one module per resource)
│   │   ├── core/         # config, security, logging
│   │   ├── libvirt/      # ALL libvirt access lives here
│   │   ├── models/       # SQLAlchemy models
│   │   ├── schemas/      # Pydantic request/response schemas
│   │   └── services/     # business logic between API and libvirt layers
│   ├── migrations/       # Alembic
│   └── tests/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── api/          # typed API client
│   │   └── hooks/
│   └── tests/
├── deploy/               # Dockerfile, compose, systemd units
├── docs/
└── AGENTS.md
```

## Setup and commands

### Prerequisites

- Linux host with KVM support (`ls /dev/kvm`)
- `libvirt-daemon-system`, `qemu-kvm`, and `libvirt-dev` installed
- Python 3.11+, Node 20+

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
alembic upgrade head
uvicorn app.main:app --reload        # dev server
pytest                               # run tests
ruff check . && ruff format --check .  # lint and format check
mypy app                             # type check
```

### Frontend

```bash
cd frontend
npm install
npm run dev          # dev server
npm run test         # unit tests
npm run lint         # eslint
npm run typecheck    # tsc --noEmit
npm run build        # production build
```

**Before finishing any task, run the lint, type check, and tests for every part of the codebase you touched.** Do not report work as done if these fail.

## Architecture rules

1. **Layering:** `api → services → libvirt`. Routers must not call libvirt directly, and the libvirt layer must not import from `api`.
2. **All libvirt calls go through `backend/app/libvirt/`.** No `import libvirt` anywhere else. This keeps the hypervisor layer mockable and swappable.
3. **Libvirt connections are managed centrally.** Use the connection helper; never open ad-hoc connections in handlers. Always close or release them, and handle `libvirt.libvirtError` explicitly.
4. **Long-running operations** (disk creation, snapshots, migrations) must be asynchronous: return a task ID and let the client poll or subscribe. Never block a request handler.
5. **Idempotency:** start, stop, and delete operations should be safe to retry and should return clear state, not errors, when the VM is already in the target state.
6. **API contracts:** every endpoint has a Pydantic request and response schema. Keep the OpenAPI spec accurate; the frontend client is generated from or typed against it.

## Coding conventions

### Python

- Follow PEP 8; format with `ruff format`; lint with `ruff`.
- Type hints on all function signatures; the code must pass `mypy`.
- Prefer small, single-purpose functions. Use `async def` for I/O-bound handlers, and run blocking libvirt calls in a thread pool.
- Raise domain-specific exceptions in services; translate them to HTTP errors in the API layer.
- Use `logging` (never `print`). Include VM UUID and user ID in log context where relevant.

### TypeScript / React

- Strict TypeScript. No `any` without a comment explaining why.
- Functional components and hooks only.
- Data fetching through the typed API client in `src/api/`, never raw `fetch` in components.
- Keep components small; move logic into hooks.

### General

- Descriptive names over comments. Comment the *why*, not the *what*.
- Conventional Commits for commit messages (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`).
- Keep changes focused. One concern per pull request.

## Security requirements

VirtDeck controls infrastructure, so treat security as a first-class concern.

- **Never build shell commands from user input.** Use libvirt APIs; if a subprocess is unavoidable, pass an argument list, never a string with `shell=True`.
- **Validate and sanitize all input**, especially VM names, disk paths, and network settings. Reject path traversal (`..`) and paths outside configured storage pools.
- **Generate libvirt domain XML with a proper XML builder or templates with escaping.** Never concatenate raw user strings into XML.
- **Enforce authorization on every endpoint.** Check the user's role and ownership of the target VM, not just that they are logged in.
- **Never log or return secrets**: passwords, tokens, VNC passwords, or private keys.
- **Console access:** VNC/SPICE ports must not be exposed publicly. Use short-lived, single-use tokens through the WebSocket proxy.
- **Audit log** all state-changing actions (who, what, which VM, when).
- Hash passwords with Argon2 or bcrypt. Use secure, HTTP-only cookies or short-lived JWTs with refresh.
- Do not commit credentials, `.env` files, or host-specific paths.

## Testing guidelines

- New features and bug fixes need tests. Bug fixes should include a regression test.
- **Unit tests must not require a real hypervisor.** Mock the `libvirt` layer (see `backend/tests/fakes/`).
- Integration tests that need a real libvirt daemon go under `backend/tests/integration/` and are marked `@pytest.mark.integration`. Use the libvirt **test driver** (`test:///default`) where possible.
- Frontend: unit-test hooks and components with Vitest; cover key flows (login, create VM, start/stop, console) with Playwright.
- Do not delete or weaken existing tests to make a change pass.

## Do

- Read existing code in the relevant module before adding new code, and match its patterns.
- Add or update docs in `docs/` when behavior, configuration, or the API changes.
- Add an Alembic migration for every database schema change.
- Ask for clarification or leave a clear note when requirements are ambiguous, instead of guessing on security-sensitive behavior.

## Don't

- Don't add new dependencies without a clear reason; prefer the standard library and existing dependencies.
- Don't run destructive operations (deleting VMs, undefining domains, wiping pools) against a real libvirt host during development or testing. Use the test driver or mocks.
- Don't edit generated files, lockfiles (by hand), or files under `migrations/` that have already been applied.
- Don't hard-code hostnames, IPs, paths, or credentials. Use configuration via environment variables (`VIRTDECK_*`).
- Don't refactor unrelated code in a feature or bugfix change.

## Configuration

Configuration is read from environment variables with the `VIRTDECK_` prefix. Key settings:

| Variable | Purpose | Example |
|---|---|---|
| `VIRTDECK_LIBVIRT_URI` | libvirt connection URI | `qemu:///system` |
| `VIRTDECK_DATABASE_URL` | database connection string | `sqlite:///./virtdeck.db` |
| `VIRTDECK_SECRET_KEY` | token signing key (required in prod) | *(generate randomly)* |
| `VIRTDECK_STORAGE_ROOT` | allowed base path for disk images | `/var/lib/libvirt/images` |
| `VIRTDECK_LOG_LEVEL` | logging verbosity | `INFO` |

## Definition of done

A change is complete when:

1. It does what was asked and nothing unrelated.
2. Lint, type checks, and tests pass for all touched code.
3. New behavior has tests, and docs are updated if needed.
4. No secrets, debug output, or commented-out code is left behind.
5. Security rules above are respected.

## Where to look

- API reference: run the backend and open `/docs` (Swagger UI)
- Architecture notes: `docs/architecture.md`
- libvirt reference: https://libvirt.org/docs.html
