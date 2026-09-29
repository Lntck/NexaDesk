> This document describes the intended API design and domain model.
> Last reviewed: 2026-09-29

# NexaDesk — Backend API Specification

## 1. Purpose

NexaDesk is a collaborative task management platform in the style of Jira.

The backend is built around:

- FastAPI
- PostgreSQL
- async SQLAlchemy 2.0
- Redis
- JWT authentication
- project-level RBAC
- REST API
- Server-Sent Events (SSE) for server-to-client realtime updates

The existing authentication layer already provides:

- `POST /api/v1/register`
- `POST /api/v1/login`
- `POST /api/v1/refresh`
- `POST /api/v1/logout`
- `GET /api/v1/about_me`
- global roles (`user`, `admin`)
- JWT access tokens
- refresh-token rotation through Redis
- rate limiting
- health probes

Domain APIs are added under `/api/v1/`.

---

# 2. Domain Model

Core entities:

```text
User
Project
ProjectMember
TaskStatus
Task
Comment
Label
TaskLabel
TaskWatcher
TaskRelation
ActivityEvent
Notification
```

Relationships:

```text
User
 ├── ProjectMember
 ├── created Tasks
 ├── assigned Tasks
 ├── Comments
 ├── Watchers
 ├── ActivityEvents
 └── Notifications

Project
 ├── Members
 ├── TaskStatuses
 ├── Tasks
 ├── Labels
 └── ActivityEvents

Task
 ├── Comments
 ├── Labels
 ├── Watchers
 ├── Relations
 └── ActivityEvents
```

---

## 2.1 Field Formats

Canonical formats used across the API:

```text
project.key       ^[A-Z][A-Z0-9]{1,9}$, unique, immutable after creation
status.key        ^[A-Z][A-Z0-9_]{1,29}$, unique within a project
task.number       integer, starts at 1, unique within a project
task key          {project.key}-{task.number}   (e.g. NEXA-17)
label.color       #RRGGBB
timestamps        ISO 8601 with timezone (UTC): 2026-09-29T16:00:00Z
due_date          date: 2026-10-15 (end of that day, UTC)
estimated_hours   non-negative decimal
```

## 2.2 Enumerations

All enumerations are defined explicitly and shared by the API and the database:

```text
Role (global)     user | admin
ProjectRole       owner | admin | member | viewer
Priority          LOW | MEDIUM | HIGH | CRITICAL        (default: MEDIUM)
TaskRelationType  BLOCKS | BLOCKED_BY | RELATES_TO | DUPLICATES | DUPLICATED_BY
ActivityEventType project.created | project.updated | member.added | member.removed |
                  member.role_changed | task.created | task.updated | task.deleted |
                  task.assigned | task.unassigned | task.status_changed |
                  comment.created | comment.updated | comment.deleted |
                  label.added | label.removed
NotificationType  task.assigned | comment.created | task.status_changed |
                  task.updated | member.added
```

Event IDs (`ActivityEvent.id` and the SSE `id:` field) are opaque,
lexicographically sortable strings (ULID or UUIDv7) so they can be used directly
as `Last-Event-ID` for replay.

---

# 3. Roles

There are two permission levels in the system.

## 3.1 Global role

```text
user
admin
```

The existing authentication layer uses hierarchical global RBAC.

## 3.2 Project role

Every project member has a project-specific role:

```text
owner
admin
member
viewer
```

Recommended permissions:

| Action | Owner | Admin | Member | Viewer |
|---|---:|---:|---:|---:|
| View project | Yes | Yes | Yes | Yes |
| Edit project | Yes | Yes | No | No |
| Archive project | Yes | Yes | No | No |
| Manage members | Yes | Yes | No | No |
| Create task | Yes | Yes | Yes | No |
| Edit task | Yes | Yes | Yes | No |
| Delete task | Yes | Yes | Restricted | No |
| Assign task | Yes | Yes | Yes | No |
| Change status | Yes | Yes | Yes | No |
| Comment | Yes | Yes | Yes | No |
| Manage labels | Yes | Yes | No | No |
| Watch task | Yes | Yes | Yes | No |

Permission checks must live in the service/policy layer rather than being duplicated inside every endpoint.

---

# 4. HTTP Conventions

Base URL:

```text
/api/v1
```

Authentication:

```http
Authorization: Bearer <access_token>
```

Content type:

```http
Content-Type: application/json
```

Application errors:

```json
{
  "detail": "Human-readable error message"
}
```

Common statuses:

```text
200 OK
201 Created
204 No Content

400 Bad Request
401 Unauthorized
403 Forbidden
404 Not Found
409 Conflict
422 Unprocessable Entity
429 Too Many Requests
```

---

# 5. Pagination

Collection endpoints should support pagination.

Preferred initial format:

```text
?page=1&page_size=20
```

Example:

```http
GET /api/v1/projects/42/tasks?page=1&page_size=50
```

Response:

```json
{
  "items": [],
  "page": 1,
  "page_size": 50,
  "total": 128
}
```

Cursor pagination may be introduced later for very large collections.

---

# 6. Authentication

These endpoints already exist.

## POST `/api/v1/register`

Create a new user.

### Request

```json
{
  "username": "john_doe",
  "email": "john@example.com",
  "password": "StrongPass123"
}
```

### Response

`201 Created`

### Errors

```text
409 — username/email already exists
422 — invalid input
429 — rate limit exceeded
```

---

## POST `/api/v1/login`

Authenticate a user.

### Request

Form data:

```text
username=john_doe
password=StrongPass123
```

### Response

```json
{
  "access_token": "<jwt>",
  "token_type": "bearer"
}
```

Refresh token is stored in an `HttpOnly` cookie.

---

## POST `/api/v1/refresh`

Rotate the refresh token and issue a new access token.

```text
POST /api/v1/refresh
```

The old refresh token must become invalid after successful rotation.

---

## POST `/api/v1/logout`

Revoke the current refresh token and clear the cookie.

---

## GET `/api/v1/about_me`

Get the current authenticated user.

---

# 7. Projects API

## GET `/api/v1/projects`

Get projects available to the current user.

### Query parameters

```text
page
page_size
search
archived
```

Example:

```http
GET /api/v1/projects?search=nexa&archived=false
```

### Response

```json
{
  "items": [
    {
      "id": 42,
      "key": "NEXA",
      "name": "NexaDesk",
      "role": "owner",
      "is_archived": false,
      "created_at": "2026-09-29T16:00:00Z"
    }
  ],
  "page": 1,
  "page_size": 20,
  "total": 1
}
```

### Rules

- Regular users see only projects they belong to.
- Global admins may have additional access according to the global authorization policy.
- Archived projects are excluded by default.

---

## POST `/api/v1/projects`

Create a project.

### Request

```json
{
  "key": "NEXA",
  "name": "NexaDesk",
  "description": "Collaborative task management platform"
}
```

### Response

`201 Created`

```json
{
  "id": 42,
  "key": "NEXA",
  "name": "NexaDesk",
  "description": "Collaborative task management platform",
  "owner_id": 7,
  "is_archived": false,
  "created_at": "2026-09-29T16:00:00Z"
}
```

### Business rules

When a project is created:

1. The creator becomes `owner`.
2. Default task statuses are created.

Recommended defaults:

```text
TODO
IN_PROGRESS
REVIEW
DONE
```

### Errors

```text
401 — unauthenticated
409 — project key already exists
422 — invalid input
```

---

## GET `/api/v1/projects/{project_id}`

Get project details.

### Response

```json
{
  "id": 42,
  "key": "NEXA",
  "name": "NexaDesk",
  "description": "Collaborative task management platform",
  "owner": {
    "id": 7,
    "username": "rush"
  },
  "members_count": 7,
  "tasks_count": 128,
  "is_archived": false,
  "created_at": "2026-09-29T16:00:00Z",
  "updated_at": "2026-09-29T16:20:00Z"
}
```

### Errors

```text
403 — user is not a project member
404 — project not found
```

---

## PATCH `/api/v1/projects/{project_id}`

Update project metadata.

### Request

```json
{
  "name": "NexaDesk Backend",
  "description": "Updated description"
}
```

Any omitted field remains unchanged.

### Permissions

Allowed for:

```text
owner
project admin
```

---

## POST `/api/v1/projects/{project_id}/archive`

Archive a project.

### Rules

After archival:

- creating tasks is forbidden
- adding members is forbidden
- changing tasks is forbidden
- commenting is forbidden
- reading the project and its history remains available
- restoration is allowed to project owner/admin

---

## POST `/api/v1/projects/{project_id}/restore`

Restore an archived project.

---

# 8. Project Members API

## GET `/api/v1/projects/{project_id}/members`

List project members.

### Response

```json
{
  "items": [
    {
      "user": {
        "id": 7,
        "username": "rush"
      },
      "role": "owner",
      "joined_at": "2026-09-29T16:00:00Z"
    }
  ]
}
```

---

## POST `/api/v1/projects/{project_id}/members`

Add an existing user to a project.

### Request

```json
{
  "user_id": 17,
  "role": "member"
}
```

### Business rules

- The user must exist.
- The user must not already be a member.
- Only owner/admin can add members.
- A regular member cannot assign `owner`.
- Project ownership changes should be a separate operation.

### Errors

```text
404 — user/project not found
409 — user is already a member
403 — insufficient permission
422 — invalid role
```

---

## PATCH `/api/v1/projects/{project_id}/members/{user_id}`

Change a project member's role.

### Request

```json
{
  "role": "admin"
}
```

Only owner/admin can perform this action.

Recommended rule:

```text
Only owner can create another owner.
```

Better yet, keep `owner` unique and support explicit ownership transfer later.

---

## DELETE `/api/v1/projects/{project_id}/members/{user_id}`

Remove a project member.

### Rules

- A member cannot remove another admin.
- An owner cannot be removed without ownership transfer.
- Removing a member does not automatically delete their historical activity.
- Tasks assigned to the removed member remain assigned until explicitly changed or policy handles reassignment.

---

# 9. Task Status API

Task statuses belong to a project.

## GET `/api/v1/projects/{project_id}/statuses`

List project task statuses.

### Response

```json
{
  "items": [
    {
      "id": 1,
      "name": "TODO",
      "key": "TODO",
      "color": "#...",
      "position": 1
    },
    {
      "id": 2,
      "name": "In Progress",
      "key": "IN_PROGRESS",
      "color": "#...",
      "position": 2
    }
  ]
}
```

---

## POST `/api/v1/projects/{project_id}/statuses`

Create a custom status.

### Request

```json
{
  "name": "QA",
  "key": "QA",
  "color": "#...",
  "position": 3
}
```

Permissions:

```text
owner
admin
```

---

## PATCH `/api/v1/projects/{project_id}/statuses/{status_id}`

Update status metadata or board position.

---

## DELETE `/api/v1/projects/{project_id}/statuses/{status_id}`

Delete a status.

### Important rule

A status containing tasks cannot simply disappear.

Possible policies:

```text
reject deletion with 409
```

or:

```text
require target_status_id and migrate tasks
```

The first version should use `409 Conflict`.

---

# 10. Tasks API

Tasks are the primary domain object.

A task has:

```text
id
project_id
number
title
description
status_id
priority
creator_id
assignee_id
parent_task_id
due_date
estimated_hours
created_at
updated_at
```

The public task key is:

```text
{project.key}-{task.number}
```

Example:

```text
NEXA-17
```

---

## GET `/api/v1/projects/{project_id}/tasks`

List and filter project tasks.

### Query parameters

```text
page
page_size

search

status
priority

assignee_id
creator_id

label
due_before
due_after

sort
```

Example:

```http
GET /api/v1/projects/42/tasks?status=IN_PROGRESS&priority=HIGH&assignee_id=17&sort=-created_at
```

### Response

```json
{
  "items": [
    {
      "id": 123,
      "key": "NEXA-17",
      "title": "Implement SSE notifications",
      "status": {
        "id": 2,
        "key": "IN_PROGRESS",
        "name": "In Progress"
      },
      "priority": "HIGH",
      "assignee": {
        "id": 17,
        "username": "john"
      },
      "created_at": "2026-09-29T16:00:00Z",
      "updated_at": "2026-09-29T16:30:00Z"
    }
  ],
  "page": 1,
  "page_size": 50,
  "total": 1
}
```

---

## POST `/api/v1/projects/{project_id}/tasks`

Create a task.

### Request

```json
{
  "title": "Implement SSE notifications",
  "description": "Broadcast task updates to connected clients",
  "assignee_id": 17,
  "status_id": 2,
  "priority": "HIGH",
  "due_date": "2026-10-15",
  "estimated_hours": 8
}
```

### Business rules

- User must have task-creation permission.
- Assignee must be a project member.
- Status must belong to the same project.
- Archived projects reject creation.
- `number` is generated by the backend.
- Creator is taken from the authenticated user and cannot be spoofed.

### Response

`201 Created`

---

## GET `/api/v1/tasks/{task_id}`

Get a single task.

### Response

```json
{
  "id": 123,
  "key": "NEXA-17",
  "project_id": 42,
  "title": "Implement SSE notifications",
  "description": "Broadcast task updates to connected clients",
  "status": {
    "id": 2,
    "key": "IN_PROGRESS",
    "name": "In Progress"
  },
  "priority": "HIGH",
  "creator": {
    "id": 7,
    "username": "rush"
  },
  "assignee": {
    "id": 17,
    "username": "john"
  },
  "labels": [],
  "comments_count": 0,
  "watchers_count": 0,
  "due_date": "2026-10-15",
  "estimated_hours": 8,
  "created_at": "2026-09-29T16:00:00Z",
  "updated_at": "2026-09-29T16:30:00Z"
}
```

---

## PATCH `/api/v1/tasks/{task_id}`

Update editable task fields.

### Request

```json
{
  "title": "Implement production SSE notifications",
  "description": "Updated details",
  "priority": "CRITICAL",
  "due_date": "2026-10-20"
}
```

### Important

Do not use this endpoint for operations that have meaningful domain behavior.

These should be explicit commands:

```text
transition
assign
unassign
move
watch
unwatch
```

---

## DELETE `/api/v1/tasks/{task_id}`

Delete/archive a task.

Recommended first-version behavior:

- soft delete
- retain activity history
- prevent access to deleted task from normal task lists

Permanent deletion should not be necessary initially.

---

# 11. Task Workflow

## POST `/api/v1/tasks/{task_id}/transition`

Move a task to another status.

### Request

```json
{
  "status_id": 4
}
```

### Example

```text
TODO → IN_PROGRESS
IN_PROGRESS → REVIEW
REVIEW → DONE
```

### Business logic

The service should:

1. Authenticate user.
2. Load task.
3. Validate project membership.
4. Validate permission.
5. Validate source and target status.
6. Perform status update.
7. Create activity event.
8. Publish realtime event.
9. Create notifications when required.
10. Commit transaction.

### Response

```json
{
  "id": 123,
  "key": "NEXA-17",
  "status": {
    "id": 4,
    "key": "DONE",
    "name": "Done"
  },
  "updated_at": "2026-09-29T17:00:00Z"
}
```

### Invalid transition

Return:

```text
409 Conflict
```

Example:

```json
{
  "detail": "Task cannot transition from DONE to TODO"
}
```

---

# 12. Task Assignment

## POST `/api/v1/tasks/{task_id}/assign`

Assign task to a project member.

### Request

```json
{
  "user_id": 17
}
```

### Rules

- Assignee must belong to the task's project.
- User must have assignment permission.
- Assignment must generate an activity event.
- Assignment should generate a notification to the new assignee.
- Assignment should generate an SSE event.

---

## POST `/api/v1/tasks/{task_id}/unassign`

Remove the current assignee.

No request body required.

---

# 13. Task Move

## POST `/api/v1/tasks/{task_id}/move`

Move a task between projects.

### Request

```json
{
  "project_id": 55
}
```

### Required permission

The current user must have permission in both:

```text
source project
target project
```

### Important domain decisions

When moving a task, decide what happens to:

```text
status
assignee
labels
comments
task number/key
```

Recommended first-version policy:

- task receives a new number in the target project
- old project key is stored in activity/history
- assignee must belong to target project or becomes unassigned
- status must be mapped to a target-project status
- labels are preserved only when matching labels exist in target project
- comments remain attached to the task

---

# 14. Kanban Board

## GET `/api/v1/projects/{project_id}/board`

Return tasks grouped by status.

### Response

```json
{
  "columns": [
    {
      "status": {
        "id": 1,
        "key": "TODO",
        "name": "TODO",
        "position": 1
      },
      "tasks": []
    },
    {
      "status": {
        "id": 2,
        "key": "IN_PROGRESS",
        "name": "In Progress",
        "position": 2
      },
      "tasks": []
    }
  ]
}
```

The frontend can use the same transition endpoint for drag-and-drop:

```text
POST /api/v1/tasks/{task_id}/transition
```

Do not create a separate "move card" endpoint.

---

# 15. Comments API

## GET `/api/v1/tasks/{task_id}/comments`

List comments.

Support:

```text
page
page_size
```

---

## POST `/api/v1/tasks/{task_id}/comments`

Create a comment.

### Request

```json
{
  "body": "I implemented the SSE publisher."
}
```

### Rules

- Comment author comes from JWT.
- User must have comment permission.
- The task must belong to a project the user can access.
- Empty comments are rejected.
- Comment creation generates an activity event.
- Comment creation generates an SSE event.
- Watchers may receive notifications.

---

## PATCH `/api/v1/comments/{comment_id}`

Update a comment.

Allowed for:

```text
comment author
project admin
global admin
```

---

## DELETE `/api/v1/comments/{comment_id}`

Soft-delete a comment.

Do not erase activity history.

---

# 16. Labels API

## GET `/api/v1/projects/{project_id}/labels`

List project labels.

---

## POST `/api/v1/projects/{project_id}/labels`

Create a label.

### Request

```json
{
  "name": "backend",
  "color": "#..."
}
```

Permissions:

```text
owner
admin
```

---

## PATCH `/api/v1/projects/{project_id}/labels/{label_id}`

Update label.

---

## DELETE `/api/v1/projects/{project_id}/labels/{label_id}`

Delete label.

If the label is attached to tasks, remove the relation but do not modify the task itself.

---

## POST `/api/v1/tasks/{task_id}/labels/{label_id}`

Attach a label to a task.

### Rules

- Label and task must belong to the same project.
- Duplicate relation should return `409 Conflict` or be handled idempotently.
- Operation generates an activity event.

---

## DELETE `/api/v1/tasks/{task_id}/labels/{label_id}`

Remove a label from a task.

---

# 17. Watchers

A watcher subscribes to changes related to a task.

## GET `/api/v1/tasks/{task_id}/watchers`

List watchers.

---

## POST `/api/v1/tasks/{task_id}/watch`

Current user starts watching the task.

---

## POST `/api/v1/tasks/{task_id}/unwatch`

Current user stops watching the task.

---

## DELETE `/api/v1/tasks/{task_id}/watchers/{user_id}`

Remove another watcher.

Recommended permission:

```text
task watcher can remove himself
project admin can remove anyone
```

---

# 18. Task Relations

Optional but strongly recommended for a Jira-like version.

## GET `/api/v1/tasks/{task_id}/relations`

List task relationships.

---

## POST `/api/v1/tasks/{task_id}/relations`

Create a relation.

### Request

```json
{
  "target_task_id": 145,
  "type": "BLOCKS"
}
```

Supported types:

```text
BLOCKS
BLOCKED_BY
RELATES_TO
DUPLICATES
DUPLICATED_BY
```

### Rules

Reject:

- relation to itself
- duplicate relation
- task from inaccessible project

---

## DELETE `/api/v1/tasks/{task_id}/relations/{relation_id}`

Delete relation.

---

# 19. Activity API

Activity is an immutable history of important domain changes.

## GET `/api/v1/projects/{project_id}/activity`

Get project activity.

Example events:

```text
project.created
member.added
member.removed
member.role_changed
task.created
task.deleted
task.assigned
task.unassigned
task.status_changed
task.updated
comment.created
comment.updated
comment.deleted
label.added
label.removed
```

---

## GET `/api/v1/tasks/{task_id}/activity`

Get activity for a single task.

### Response

```json
{
  "items": [
    {
      "id": "evt_01928",
      "type": "task.status_changed",
      "actor": {
        "id": 7,
        "username": "rush"
      },
      "data": {
        "from": "TODO",
        "to": "IN_PROGRESS"
      },
      "created_at": "2026-09-29T17:00:00Z"
    }
  ]
}
```

Activity events must be append-only.

---

# 20. Notifications API

## GET `/api/v1/notifications`

Get notifications for the current user.

### Query

```text
page
page_size
read
```

---

## GET `/api/v1/notifications/unread`

Get unread notifications.

Example:

```json
{
  "items": [
    {
      "id": 100,
      "type": "task.assigned",
      "title": "Task assigned to you",
      "message": "NEXA-17 was assigned to you",
      "task_id": 123,
      "read": false,
      "created_at": "2026-09-29T17:05:00Z"
    }
  ]
}
```

---

## POST `/api/v1/notifications/{notification_id}/read`

Mark one notification as read.

---

## POST `/api/v1/notifications/read-all`

Mark all current user's notifications as read.

---

# 21. Realtime — SSE

NexaDesk uses **Server-Sent Events**, not WebSocket.

SSE is appropriate because the realtime requirement is primarily:

```text
server → browser
```

Examples:

```text
task changed
comment created
notification created
member changed
activity added
```

Client commands continue to use REST.

---

## GET `/api/v1/projects/{project_id}/events`

Open a server-sent events stream.

### Request

```http
GET /api/v1/projects/42/events
Authorization: Bearer <access_token>
Accept: text/event-stream
```

### Response headers

```http
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive
```

---

## SSE Event Format

Example:

```text
event: task.status_changed
id: evt_01928
data: {"task_id":123,"project_id":42,"from":"TODO","to":"IN_PROGRESS","actor_id":7}

```

Recommended common fields:

```json
{
  "id": "evt_01928",
  "type": "task.status_changed",
  "project_id": 42,
  "task_id": 123,
  "actor": {
    "id": 7,
    "username": "rush"
  },
  "timestamp": "2026-09-29T17:00:00Z",
  "data": {
    "from": "TODO",
    "to": "IN_PROGRESS"
  }
}
```

---

# 22. SSE Event Types

Recommended events:

```text
project.updated

member.added
member.removed
member.role_changed

task.created
task.updated
task.deleted
task.assigned
task.unassigned
task.status_changed

comment.created
comment.updated
comment.deleted

label.added
label.removed

notification.created

activity.created
```

The frontend listens to one project stream and updates local state when events arrive.

---

# 23. SSE Authentication and Authorization

When a user connects to:

```http
GET /api/v1/projects/{project_id}/events
```

the backend must:

1. Validate JWT.
2. Resolve the current user.
3. Verify project existence.
4. Verify project membership/access.
5. Start the stream.

Unauthorized users must not be able to receive events from projects they cannot access.

For browser clients, prefer an authentication mechanism compatible with your frontend architecture. If using native `EventSource`, avoid putting bearer tokens into URLs. A cookie-based authenticated session or an appropriate SSE-compatible auth bridge can be used.

---

# 24. Redis and SSE

Redis can be used as the cross-process event broker.

Architecture:

```text
REST request
    ↓
TaskService
    ↓
PostgreSQL transaction
    ↓
publish event
    ↓
Redis Pub/Sub
    ↓
SSE connection(s)
    ↓
Browser clients
```

This matters when multiple FastAPI workers are running.

Without a shared broker:

```text
Worker A
 └── client 1

Worker B
 └── client 2
```

A task update handled by Worker A would not automatically reach a client connected to Worker B.

Redis Pub/Sub solves this distribution problem.

---

# 25. SSE Connection Lifecycle

A client should:

1. Open project event stream.
2. Receive events.
3. Keep the connection alive.
4. Reconnect automatically after network failure.
5. Use event IDs to recover from missed events if the implementation supports replay.

Heartbeat example:

```text
: heartbeat

```

This prevents idle connections from being incorrectly closed by proxies.

---

# 26. Realtime Service Flow

Every business operation with realtime behavior should follow:

```text
HTTP Endpoint
    ↓
Service
    ↓
Permission validation
    ↓
Database transaction
    ↓
ActivityEvent
    ↓
Domain event
    ↓
Redis publisher
    ↓
SSE subscribers
```

Example:

```text
POST /api/v1/tasks/123/transition
        ↓
TaskService.transition()
        ↓
validate transition
        ↓
UPDATE task
        ↓
create activity
        ↓
publish task.status_changed
        ↓
Redis
        ↓
SSE
        ↓
all connected project clients
```

---

# 27. Search API

## GET `/api/v1/search`

Global search for the current user.

### Query

```text
q
```

Example:

```http
GET /api/v1/search?q=websocket
```

### Response

```json
{
  "projects": [],
  "tasks": [
    {
      "id": 123,
      "key": "NEXA-17",
      "title": "Implement SSE notifications",
      "project_id": 42
    }
  ],
  "users": []
}
```

The first version can use PostgreSQL `ILIKE`.

Full text search can be added later.

---

# 28. Current User API

## GET `/api/v1/me/tasks`

Get tasks assigned to the current user.

Recommended query:

```text
status
priority
project_id
page
page_size
```

---

## GET `/api/v1/me/projects`

Get projects where the current user is a member.

---

## GET `/api/v1/me/activity`

Get the current user's activity.

---

# 29. Important Business Scenarios

## Scenario A — Create task

```text
Client
  ↓
POST /projects/42/tasks
  ↓
check membership
  ↓
check create permission
  ↓
validate status
  ↓
validate assignee
  ↓
create task
  ↓
create activity
  ↓
publish SSE event
```

---

## Scenario B — Drag task on board

```text
Client
  ↓
POST /tasks/123/transition
  ↓
validate transition
  ↓
update status
  ↓
activity
  ↓
SSE
```

No separate board-specific mutation endpoint is required.

---

## Scenario C — Assign task

```text
POST /tasks/123/assign
        ↓
check target user is project member
        ↓
update assignee
        ↓
activity
        ↓
notification
        ↓
SSE
```

---

## Scenario D — Add comment

```text
POST /tasks/123/comments
        ↓
validate access
        ↓
create comment
        ↓
activity
        ↓
notification to relevant watchers
        ↓
SSE
```

---

## Scenario E — Remove project member

```text
DELETE /projects/42/members/17
        ↓
check admin permission
        ↓
remove membership
        ↓
create activity
        ↓
publish member.removed
```

Tasks created by that user and historical activity remain intact.

---

# 30. Edge Cases

The following cases must be explicitly covered in tests and services.

## Project

- duplicate project key
- empty project name
- archived project modification
- non-member access
- removing project owner
- deleting a project with existing tasks

## Members

- adding nonexistent user
- adding existing member
- assigning invalid role
- removing owner
- member attempting to promote himself
- admin attempting forbidden ownership operation

## Tasks

- assignee is not a project member
- status belongs to another project
- create task in archived project
- update task without permission
- deleting already deleted task
- moving task to inaccessible project
- invalid task transition
- self-relation
- duplicate relation

## Comments

- commenting on inaccessible task
- editing another user's comment
- deleting another user's comment
- empty body
- editing a deleted comment

## SSE

- invalid JWT
- non-member opening project stream
- client reconnect
- broken connection
- multiple FastAPI workers
- Redis unavailable
- event delivery after transaction failure

---

# 31. Transaction Rules

A business operation must not publish a successful domain event before the database transaction is safely committed.

Bad:

```text
UPDATE task
publish SSE
COMMIT
```

If commit fails, clients may receive a false event.

Preferred:

```text
BEGIN
UPDATE task
CREATE activity
COMMIT
PUBLISH event
```

For stronger delivery guarantees, introduce an **Outbox Pattern** later:

```text
BEGIN
  update task
  create activity
  create outbox event
COMMIT

background publisher
  ↓
Redis
  ↓
SSE
```

The Outbox Pattern should be considered for a production-grade version with reliable event delivery.

---

# 32. Optimistic Concurrency

Concurrent editing should not silently overwrite data.

A task may contain:

```text
version
```

Example:

```text
Task NEXA-17
version = 7
```

Client sends:

```http
If-Match: 7
```

If server version is already `8`:

```http
409 Conflict
```

This protects against:

```text
User A edits task
User B edits old copy
User B accidentally overwrites A's changes
```

This feature can be introduced after the first CRUD implementation.

---

# 33. API Design Principle

Use CRUD endpoints for data manipulation and explicit command endpoints for domain actions.

CRUD:

```text
GET task
POST task
PATCH task
DELETE task
```

Commands:

```text
POST /tasks/{id}/transition
POST /tasks/{id}/assign
POST /tasks/{id}/unassign
POST /tasks/{id}/move
POST /tasks/{id}/watch
POST /tasks/{id}/unwatch
```

This keeps business operations explicit and prevents large `PATCH` endpoints from becoming difficult to maintain.

---

# 34. Recommended Endpoint Tree

```text
/api/v1
│
├── auth
│   ├── POST   /register
│   ├── POST   /login
│   ├── POST   /refresh
│   └── POST   /logout
│
├── me
│   ├── GET    /about_me
│   ├── GET    /me/projects
│   ├── GET    /me/tasks
│   └── GET    /me/activity
│
├── projects
│   ├── GET    /
│   ├── POST   /
│   ├── GET    /{project_id}
│   ├── PATCH  /{project_id}
│   ├── POST   /{project_id}/archive
│   ├── POST   /{project_id}/restore
│   │
│   ├── GET    /{project_id}/members
│   ├── POST   /{project_id}/members
│   ├── PATCH  /{project_id}/members/{user_id}
│   ├── DELETE /{project_id}/members/{user_id}
│   │
│   ├── GET    /{project_id}/statuses
│   ├── POST   /{project_id}/statuses
│   ├── PATCH  /{project_id}/statuses/{status_id}
│   ├── DELETE /{project_id}/statuses/{status_id}
│   │
│   ├── GET    /{project_id}/labels
│   ├── POST   /{project_id}/labels
│   ├── PATCH  /{project_id}/labels/{label_id}
│   ├── DELETE /{project_id}/labels/{label_id}
│   │
│   ├── GET    /{project_id}/tasks
│   ├── POST   /{project_id}/tasks
│   ├── GET    /{project_id}/board
│   ├── GET    /{project_id}/activity
│   └── GET    /{project_id}/events
│
├── tasks
│   ├── GET    /{task_id}
│   ├── PATCH  /{task_id}
│   ├── DELETE /{task_id}
│   │
│   ├── POST   /{task_id}/transition
│   ├── POST   /{task_id}/assign
│   ├── POST   /{task_id}/unassign
│   ├── POST   /{task_id}/move
│   │
│   ├── GET    /{task_id}/comments
│   ├── POST   /{task_id}/comments
│   │
│   ├── GET    /{task_id}/labels
│   ├── POST   /{task_id}/labels/{label_id}
│   ├── DELETE /{task_id}/labels/{label_id}
│   │
│   ├── GET    /{task_id}/watchers
│   ├── POST   /{task_id}/watch
│   ├── POST   /{task_id}/unwatch
│   │
│   ├── GET    /{task_id}/relations
│   ├── POST   /{task_id}/relations
│   └── DELETE /{task_id}/relations/{relation_id}
│
├── comments
│   ├── PATCH  /{comment_id}
│   └── DELETE /{comment_id}
│
├── notifications
│   ├── GET    /
│   ├── GET    /unread
│   ├── POST   /{notification_id}/read
│   └── POST   /read-all
│
└── search
    └── GET    /?q=...
```

---

# 35. Suggested Implementation Order

Implement the backend in this order.

## Phase 1 — Foundation

```text
Project
ProjectMember
TaskStatus
Task
```

Implement:

```text
projects
members
statuses
tasks
board
```

Goal:

```text
create project
→ add members
→ create task
→ assign task
→ move task across board
```

---

## Phase 2 — Collaboration

Add:

```text
Comment
Label
Watcher
ActivityEvent
```

Goal:

```text
comment
label
watch
activity history
```

---

## Phase 3 — Realtime

Add:

```text
Redis event publisher
SSE endpoint
event schemas
connection management
```

Goal:

```text
User A changes task
→ User B sees update instantly
```

---

## Phase 4 — Notifications

Add:

```text
Notification
notification service
read/unread state
```

Goal:

```text
assignment
mention/comment
watched-task changes
```

---

## Phase 5 — Advanced Jira Features

Add:

```text
TaskRelation
Subtasks
Search
advanced filters
bulk operations
optimistic concurrency
Outbox Pattern
```

Possible future features:

```text
Sprint
Backlog
Epics
Attachments
Custom Fields
Time Tracking
Reports
JQL-like search
GitHub/GitLab integration
```

---

# 36. Architecture Target

The final backend should follow:

```text
API
 ↓
Service
 ↓
CRUD / Repository
 ↓
SQLAlchemy Models
 ↓
PostgreSQL
```

Cross-cutting infrastructure:

```text
Redis
 ├── refresh token revocation
 ├── rate limiting
 └── realtime event distribution

SSE
 └── server → client realtime updates
```

Business events:

```text
Service
 ↓
ActivityEvent
 ↓
Notification
 ↓
Redis
 ↓
SSE
```

The key principle is:

> Endpoints stay thin. Business rules stay in services. Data access stays in CRUD/repositories. Realtime and notifications react to domain operations rather than being manually implemented in every endpoint.

---

# 37. MVP Definition

NexaDesk MVP is complete when a user can:

```text
Register
Login
Create project
Add members
Create task
Assign task
Filter tasks
Open Kanban board
Move task between statuses
Comment on task
Add labels
Watch task
See activity history
Receive realtime SSE updates
Receive notifications
```

That is enough to make NexaDesk a real collaborative task-management backend rather than a simple CRUD demonstration.
