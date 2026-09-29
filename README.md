# NexaDesk

A collaborative task management platform for teams — projects, tasks, comments, and real-time updates, built on a production-grade async stack.

NexaDesk lets teams organize work into projects, break it down into tasks, assign them to members, and track progress on a kanban board. Every change is broadcast to teammates in real time, and every action is protected by role-based access control.

## Repository Layout

```text
.
|- backend/     # Backend API (FastAPI, PostgreSQL, Redis) — see backend/README.md
|- frontend/    # Web client (planned)
|- README.md
```

NexaDesk is a monorepo: the backend lives in [`backend/`](backend/) and has its own
[README](backend/README.md) with the full technical documentation (architecture,
API, configuration, development workflow). New domain APIs (projects, tasks,
comments, real-time updates) will be added there.

## Current Status

The backend foundation is implemented and runs via Docker Compose:

- JWT authentication (access/refresh tokens with rotation and revocation)
- Role-Based Access Control (hierarchical `user` < `admin` roles)
- User registration, login, profile endpoints
- Async SQLAlchemy 2.0 + PostgreSQL, Redis
- Health probes, rate limiting, centralized exception handling

## Getting Started

Prerequisites: Docker and Docker Compose.

```bash
cd backend

# 1. create and edit the environment file (secrets, database credentials)
cp .env.template .env

# 2. build and start the stack (app + PostgreSQL + Redis)
docker compose up --build

# 3. apply database migrations
docker compose exec app alembic upgrade head
```

Then open Swagger UI at <http://127.0.0.1:8000/docs>.

Makefile shortcuts are available in `backend/`:

```bash
make up               # docker compose up --build
make down             # docker compose down
make migrate          # alembic upgrade head
make makemigrations m="describe change"
make logs             # follow container logs
```

For local development without Docker, configuration details, request examples,
and the API reference, see [backend/README.md](backend/README.md).

## Roadmap

- ✅ Backend core: auth, users, RBAC, async stack
- ⬜ Projects and project membership
- ⬜ Tasks and kanban board
- ⬜ Comments
- ⬜ Real-time updates
- ⬜ Web client (`frontend/`)