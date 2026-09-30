# NexaDesk

NexaDesk is a collaborative task management platform for teams. It organizes work into projects, breaks it down into tasks and tracks progress on a kanban board. Teammates collaborate through comments with mentions, labels and watchers, receive notifications and see every change in real time.

The repository is a monorepo: a FastAPI backend, a React web client and a single Docker Compose file that starts the whole product with one command.

## Features

* Projects with membership roles (owner, admin, member, viewer) and ownership transfer
* Kanban board with drag and drop, per-column ordering and one-step status transitions
* Tasks with project-scoped keys, priorities, assignment, due dates, hour estimates and parent tasks
* Optimistic concurrency for task edits via If-Match
* Comments with @username mentions and an immutable activity trail
* Labels, task watchers and task filters
* Activity history for projects and tasks
* Notifications (mentions, assignments, watched-task changes) with read state
* Real-time project updates over SSE with replay after reconnect
* JWT authentication with refresh token rotation and revocation
* Role-based access control, rate limiting, health probes, centralized error model

## Tech Stack

* Backend: Python 3.12, FastAPI, SQLAlchemy 2 (async), Alembic, Pydantic
* Data: PostgreSQL 16, Redis 7 (Pub/Sub for domain events, refresh token revocation)
* Frontend: React 19, TypeScript, Vite, TanStack Query, Zustand, dnd-kit
* Realtime: sse-starlette with Last-Event-ID replay from the activity history
* Infrastructure: Docker, Docker Compose, nginx

## Architecture

```text
Browser
   |
   v
nginx (web)      static SPA, proxies /api and /health, keeps SSE unbuffered
   |
   v
FastAPI (app)    REST API, SSE streams, domain events after commit
   |        |
   v        v
PostgreSQL  Redis
```

The web client is served by nginx on a single port and calls the API through relative /api paths, so the refresh cookie stays same-origin. nginx forwards /api and /health to the backend container and never buffers the event stream. The backend writes domain events to Redis after commit and fans them out to per-project SSE streams.

## Quick Start

Prerequisites: Docker and Docker Compose.

1. Create the environment file and fill in the secrets:

```bash
cp .env.template .env
```

Generate each JWT secret with `openssl rand -hex 32` and set ACCESS_SECRET and REFRESH_SECRET.

2. Start the stack (web client, API, PostgreSQL, Redis):

```bash
docker compose up --build
```

Database migrations are applied automatically before the API starts.

3. Open the product:

* Web client: http://localhost:8080
* Swagger UI: http://localhost:8000/docs
* ReDoc: http://localhost:8000/redoc
* Readiness probe: http://localhost:8000/health/ready

Register the first account, create a project and start working on the board.

Makefile shortcuts:

```bash
make up        # build and start the stack
make down      # stop the stack
make logs      # follow container logs
make migrate   # apply database migrations manually
make clean     # stop the stack and drop data volumes
```

## Configuration

All settings live in the .env file (git-ignored). The full annotated list is in [.env.template](.env.template).

* POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD: database name and credentials, used by PostgreSQL and by DATABASE_URL
* DATABASE_URL: async SQLAlchemy URL, the host must stay `db` inside the compose network
* REDIS_URL: Redis URL, the host must stay `redis` inside the compose network
* ACCESS_SECRET, REFRESH_SECRET: JWT secrets, at least 32 characters, must not start with CHANGE_ME
* ACCESS_TOKEN_EXPIRE_M, REFRESH_TOKEN_EXPIRE_M: token lifetimes in minutes
* COOKIE_SECURE: false over plain HTTP, true behind HTTPS
* COOKIE_SAMESITE: lax, strict or none
* CORS_ORIGINS: JSON array of origins allowed to call the API directly
* DEBUG: FastAPI debug mode
* SSE_HEARTBEAT_S, SSE_IDLE_TIMEOUT_S, SSE_MAX_QUEUED_EVENTS, SSE_REPLAY_LIMIT: realtime stream tuning
* WEB_PORT, API_PORT: host ports published by Docker Compose

The API validates the configuration on startup and refuses to run with missing or default secrets.

## Development

Backend (full guide in [backend/README.md](backend/README.md)):

```bash
cd backend
cp .env.template .env       # point DATABASE_URL and REDIS_URL at localhost
poetry install --with dev
poetry run alembic upgrade head
poetry run uvicorn app.main:app --reload --port 8000
```

Web client (development server with an /api proxy to the backend):

```bash
cd frontend
npm install
npm run dev                 # http://localhost:3000
```

## Testing

```bash
cd backend && poetry run pytest     # unit tests
cd frontend && npm run typecheck    # TypeScript
cd frontend && npm run lint         # ESLint
```

## API Documentation

* Swagger UI: http://localhost:8000/docs, ReDoc: http://localhost:8000/redoc
* Full contract with request and response examples: [docs/api-endpoints.md](docs/api-endpoints.md)
* Errors use a stable envelope: {"detail": "...", "code": "project_not_found"}, the code registry is in the contract

## Repository Layout

```text
.
|- backend/             FastAPI API, Alembic migrations, unit tests
|- frontend/            React web client (Vite + TypeScript)
|- docs/                API contract
|- docker-compose.yml   the whole stack
|- .env.template        configuration reference
|- Makefile             stack commands
|- README.md
```

## Roadmap

* [x] Backend core: auth, users, RBAC, async stack
* [x] Projects and project membership
* [x] Tasks and kanban board
* [x] Comments, labels, watchers
* [x] Activity history
* [x] Notifications
* [x] Real-time updates
* [x] Web client
* [ ] Task relations and cross-project task moves
* [ ] Search and reporting
