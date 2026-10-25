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
* Health probe: http://localhost:8000/health
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

## Deployment

The same compose file deploys the product to a server:

```bash
docker compose up --build -d
```

Behind HTTPS set COOKIE_SECURE=true in .env and point CORS_ORIGINS at the public origin. All data lives in the postgres_data and redis_data volumes.

For the Kubernetes deployment (helmfile, Gateway API routing, logging and alerting) see [k8s/README.md](k8s/README.md).

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
* METRICS_ENABLED, METRICS_HOST, METRICS_PORT: OpenMetrics endpoint on a dedicated port (default 9100)
* LOG_LEVEL: root log level for the structured JSON log (default INFO)
* SERVICE_NAME, SERVICE_VERSION, DEPLOYMENT_ENVIRONMENT_NAME: service identity fields attached to every log record
* K8S_POD_NAME: pod name for log records, set automatically via the downward API in Kubernetes
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

## Logging

The backend emits structured JSON logs to stdout, one JSON object per line. Every record carries timestamp (ISO 8601, UTC, milliseconds), level and severity_number, message, service.name, service.version, deployment.environment.name, host.name, k8s.pod.name, request_id and trace_id, plus duration_ms and error.message / error.stack where they make sense. Each HTTP request produces a single access event (method, path, status_code, duration_ms, user_id), probes under /health are skipped. The response header X-Request-Id echoes the request id so a client can join its own logs to the request trace. Uvicorn access log is disabled in favour of the middleware event. Secrets, connection string credentials, tokens and card numbers are scrubbed or masked before rendering, session identifiers are logged as hashes.

## Monitoring and alerting

Container logs from every node are shipped by the vlagent DaemonSet (namespace observability) into single-node VictoriaLogs, so all JSON fields stay queryable with LogsQL. The stack is plain manifests applied with kubectl, details in [k8s/README.md](k8s/README.md).

* The backend serves an OpenMetrics endpoint at /metrics on a dedicated port (METRICS_PORT, default 9100): request RED metrics per route template and business metrics (task flows, comments, notifications, auth attempts, realtime streams). The port carries no authentication and must be restricted at the network level: the chart ships the backend-metrics Service and a NetworkPolicy admitting the observability namespace. Scraping and central storage (vmagent, VictoriaMetrics) is a planned addition.
* Grafana with the official VictoriaLogs datasource plugin (victoriametrics-logs-datasource), provisioned from a ConfigMap together with log level rules. Access: kubectl port-forward svc/grafana -n observability 3000:3000 (admin/admin), then Explore -> VictoriaLogs.
* vmalert evaluates LogsQL rules (group type vlogs) every minute with a 2 minute pending window: BackendErrors fires on ERROR records from the backend, DbRoleErrors watches postgres "role does not exist" failures on nexadesk-db-postgresql-0. UI: kubectl port-forward svc/vmalert -n observability 8880:8880, page /vmalert.
* Alertmanager receives fired alerts; the bundled receiver is named "null" and drops them, so add a real receiver (webhook, mail) in k8s/observability/monitoring/alertmanager-config.yaml when alert delivery is needed. UI: kubectl port-forward svc/alertmanager -n observability 9093:9093.

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
|- k8s/                 Kubernetes charts, helmfile, observability stack
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
