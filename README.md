# VirtDeck

A web-based virtual machine management tool for Linux hosts running KVM/QEMU through libvirt.

Manage every VM from one place.

## Status

Early scaffold: user auth (JWT + RBAC), VM listing/lifecycle (start/stop/reboot/delete) against
libvirt, and an audit log are wired up end to end. Console access (noVNC), storage pools,
networks, and snapshots are not yet implemented.

## Getting started

See [AGENTS.md](AGENTS.md) for the full architecture, conventions, and setup commands.

```bash
# Backend (requires libvirt-dev + libvirt-daemon-system on the host)
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env   # then edit as needed
alembic upgrade head
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

Docs live in [docs/](docs/), starting with [docs/architecture.md](docs/architecture.md).
