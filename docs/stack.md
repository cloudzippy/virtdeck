# Technology stack

This page records **what** VirtDeck is built with and **why**. The short version lives in the
tech-stack table in [AGENTS.md](../AGENTS.md); this page holds the reasoning and the alternatives
we rejected.

Guiding rule: keep the stack small. Every new component must pay for itself with a concrete
requirement (see "Don't add new dependencies without a clear reason" in AGENTS.md).

## Stack at a glance

| Concern | Choice | Status | Why |
|---|---|---|---|
| Backend API | Python 3.11+, FastAPI, Pydantic v2 | in place | Async, typed, generates the OpenAPI spec the frontend is typed against |
| Hypervisor access | `libvirt-python`, only inside `backend/app/libvirt/` | in place | Official bindings; stable APIs for domains, storage volumes, networks, and lifecycle events |
| Domain / volume XML | stdlib `xml.etree.ElementTree` builders | planned (phase 1) | Escapes values by construction, which satisfies the "never concatenate user strings into XML" rule, and needs no new dependency |
| Cloud-init seed ISO | `pycdlib` | planned (phase 1) | Pure-Python ISO9660 writer. Builds the NoCloud `cidata` ISO with no `genisoimage`/`xorriso` subprocess |
| Database | PostgreSQL (prod), SQLite (dev), SQLAlchemy 2 + Alembic | in place | Holds data VirtDeck owns: users, VM ownership/spec, tasks, images, hosts, audit |
| Jobs, events, short-lived tokens | **Redis 7 + `arq`** | planned (phase 1) | One component covers three needs: async long-running tasks (AGENTS rule 4), pub/sub fan-out of libvirt events to WebSockets, and single-use console tokens with a TTL |
| Live updates | FastAPI WebSocket `/api/ws/events` | planned (phase 1) | Pushes VM state and task progress to the browser, so no polling |
| Browser console | noVNC (`@novnc/novnc`) + FastAPI WebSocket proxy + libvirt `openGraphicsFD` | planned (phase 1) | Guests expose **no VNC port at all** (`<listen type='none'/>`). The proxy gets a VNC file descriptor straight from libvirt, which also works from inside a container |
| Frontend | React 18 + TypeScript (strict) + Vite + React Router | in place | — |
| Frontend server state | **TanStack Query** | planned (phase 1) | Caching, mutations, and cache invalidation driven by WebSocket events. Replaces hand-rolled fetch hooks |
| Auth | Argon2 hashes, short-lived access JWT (in memory), rotating refresh token in an HTTP-only cookie | partly in place | Matches the AGENTS.md security rules. Moves tokens out of `localStorage` |
| HTTP client (image import, agent calls) | `httpx` | planned (move from dev to runtime deps) | Already used by the test suite. Async, supports mTLS client certificates |
| Multi-host transport | HTTPS + **mTLS** REST between the control plane and `virtdeck-agent` (FastAPI) | planned (phase 2) | Reuses FastAPI and the Pydantic schemas on both ends |
| Internal CA for agent certs | `cryptography` | planned (phase 2) | Signs agent CSRs at enrollment |
| Metrics | Prometheus `/metrics` endpoint | planned (phase 2) | Host capacity, task durations, API latency |
| Packaging | Docker Compose (nginx, api, worker, events, redis, postgres); systemd units for host installs and the agent | partly in place | — |
| Testing | pytest + fakes, libvirt `test:///default` for integration tests, Vitest, Playwright | in place | — |

## New dependencies and what justifies each

| Package | Side | Needed for |
|---|---|---|
| `redis`, `arq` | backend | Task queue, event pub/sub, console tokens |
| `pycdlib` | backend | Cloud-init seed ISO without a subprocess |
| `httpx` (runtime) | backend | Image import from allow-listed URLs, and the phase 2 `AgentDriver` |
| `cryptography` | backend (phase 2) | Internal CA for agent mTLS |
| `@tanstack/react-query` | frontend | Server-state cache and mutations |
| `@novnc/novnc` | frontend | In-browser VNC client |

## Alternatives considered and rejected

| Alternative | Rejected because |
|---|---|
| **Celery** | Synchronous worker model and heavier operations. `arq` is asyncio-native and fits FastAPI; Redis is needed anyway for pub/sub and tokens |
| **Postgres-only job table** (`SKIP LOCKED`) | Workable, but we would still need pub/sub and TTL keys, and SQLite (dev) has no `SKIP LOCKED` |
| **gRPC** for controller ↔ agent | More tooling (codegen, proto versioning) for no gain at this scale. FastAPI + Pydantic already gives typed contracts |
| **Remote libvirt URIs** (`qemu+tls://host/system`) from the controller | No local filesystem access on the host for images and seed ISOs, awkward console routing, exposes the libvirt socket over the network, and makes the controller the only place state lives |
| **VNC on `127.0.0.1:59xx` + TCP proxy** | Unreachable from the containerised backend without host networking, and it still opens a listening port per VM. `openGraphicsFD` avoids both |
| **Websockify** as a separate proxy | One more process, and it can't enforce VirtDeck's per-VM authorization or single-use tokens |
| **Proxmox / oVirt / OpenStack** | Full platforms with their own opinions. VirtDeck's goal is a small, auditable manager on plain libvirt |
| **Tokens in `localStorage`** | Readable by any XSS. Replaced by an in-memory access token plus an HTTP-only refresh cookie |
