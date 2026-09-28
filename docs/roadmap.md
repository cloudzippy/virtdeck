# Roadmap

This page lists the planned work for VirtDeck in delivery order. Each numbered item is sized to be
one pull request (see "One concern per pull request" in [AGENTS.md](../AGENTS.md)). The reasoning
behind the technology choices lives in [stack.md](stack.md).

Every item must meet the AGENTS.md definition of done: tests (fakes for unit tests,
`test:///default` for integration tests), lint and type checks passing, docs updated, and an
Alembic migration for every schema change.

## Current state

Working end to end:

- JWT login with Argon2 password hashes, and three roles: `admin`, `operator`, `viewer`
- Listing VMs and running start, shutdown, force-stop, reboot, and delete through the
  `api → services → libvirt` layers
- An audit log of state-changing actions
- A fake libvirt module for unit tests, and integration tests against `test:///default`
- Docker Compose and a systemd unit

Known gaps against AGENTS.md, fixed in phase 0:

- Authorization checks only the role, never who owns the target VM.
- The access token is stored in `localStorage`.
- Reboot fails on a shut-off VM instead of returning its state (idempotency rule).
- The VM `{uuid}` path parameter is not validated.
- Failed actions are not written to the audit log.
- The default insecure `secret_key` is accepted in production.
- Pause and resume are not implemented.

## Phase 0: Fix the foundations

| # | Pull request | Scope |
|---|---|---|
| 0.1 | `docs: add stack rationale and roadmap` | Add `stack.md` and this roadmap. Update `architecture.md` so it agrees with `stack.md`: libvirt stays the source of truth for runtime state, and the database holds data VirtDeck owns, such as VM ownership and spec. |
| 0.2 | `fix: validate VM UUIDs and make reboot idempotent` | Change the path parameter to the `uuid.UUID` type. Reboot on a shut-off VM returns its state. Add pause and resume. Include regression tests. |
| 0.3 | `feat: VM ownership and per-VM authorization` | Add a `vm_ownership` table and migration. Services check ownership through one shared helper. Filter list results to what the user may see. |
| 0.4 | `fix: audit failed actions, refuse insecure secret in prod` | Record failed attempts in the audit log with an outcome field (needs a migration). Add `VIRTDECK_ENV`. Refuse to start when it is `prod` and the default secret is still set. |
| 0.5 | `feat: refresh-token rotation` | Add a `refresh_tokens` table. Issue a rotating refresh token in an HTTP-only, `SameSite=Strict` cookie. Add `/api/auth/refresh` and `/api/auth/logout`. The frontend keeps the access token in memory only. |

## Phase 1: Single-host feature set

| # | Pull request | Scope |
|---|---|---|
| 1.1 | `feat: task infrastructure` | Add a `Task` model and migration, `GET /api/tasks/{id}`, an `arq` worker, and `redis` and `worker` services in Compose. Unit tests use a Redis stub. |
| 1.2 | `feat: libvirt event stream` | Register libvirt domain events in `app/libvirt/events.py`. A separate events process publishes them to Redis. Add `/api/ws/events` with authentication and per-user filtering. |
| 1.3 | `feat(frontend): TanStack Query and live updates` | Replace the hand-rolled fetch hooks with query hooks. WebSocket events trigger cache refreshes. |
| 1.4 | `feat: storage pools and volumes (read-only)` | Add `app/libvirt/storage.py`, a service, and routes. One shared path check rejects `..` and any path outside `VIRTDECK_STORAGE_ROOT`. |
| 1.5 | `feat: image library` | Import images from allow-listed URLs with `httpx` as a background task. Verify checksums. Add an `Image` model. |
| 1.6 | `feat: domain XML builder` | Add `app/libvirt/xml_builder.py` using `xml.etree.ElementTree`. Graphics use `<listen type='none'/>`. Snapshot tests check that user values are escaped. |
| 1.7 | `feat: create VM` | A background task creates a qcow2 disk from an image, builds a cloud-init seed ISO with `pycdlib`, then defines and starts the VM. Includes a frontend wizard and a Playwright test. |
| 1.8 | `feat: browser console` | Add `openGraphicsFD` to the libvirt layer. Store single-use console tokens in Redis with a TTL. Add a WebSocket proxy that checks ownership, and a noVNC page. |
| 1.9 | `feat: virtual networks` | List and create NAT and isolated networks through the XML builder. Attach network cards to VMs. |
| 1.10 | `feat: snapshots` | Create, list, revert, and delete snapshots as background tasks, with audit entries. |

## Phase 2: Multiple hosts and operations

| # | Pull request | Scope |
|---|---|---|
| 2.1 | `refactor: host driver interface` | Put a `HostDriver` interface in front of the libvirt layer, with a `LocalDriver` implementation. No behavior change. |
| 2.2 | `feat: virtdeck-agent` | A FastAPI agent that runs on each host, reuses the Pydantic schemas, and ships with a systemd unit. |
| 2.3 | `feat: agent enrollment and mTLS` | An internal certificate authority using `cryptography`. Agents enroll, and the control plane talks to them over mTLS with `httpx`. |
| 2.4 | `feat: hosts` | Add a `Host` model, a host picker when placing VMs, and capacity reporting. |
| 2.5 | `feat: metrics` | A Prometheus `/metrics` endpoint covering host capacity, task durations, and API latency. |
| 2.6 | `feat: backups` | Export a disk plus the VM definition as a background task, and restore from it. |

Later: a Tauri desktop app that wraps the same frontend build (see `architecture.md`).

## Open decisions

These affect security-sensitive behavior and need an answer before the related work starts.

| Decision | Blocks |
|---|---|
| Ownership rules: do admins see every VM? Can operators act on VMs they don't own? Is group ownership needed? | 0.3 |
| VMs defined outside VirtDeck: hide them until an admin claims them, or assign them to admins by default? | 0.3 |
| Image allow-list: a `VIRTDECK_IMAGE_URL_ALLOWLIST` variable or an admin-managed database table? | 1.5 |
| Backup destination: a local directory under the storage root, or remote storage (S3 or similar), which adds a dependency? | 2.6 |
