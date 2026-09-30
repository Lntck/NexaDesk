> This document describes the intended API design and domain model.
> Last reviewed: 29-09-2026

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

## 1.1 Document Status

This document is the executable contract for the API. Every section is in one of two states:

```text
Implemented  — exists in the codebase and is covered by tests
Planned      — the contract for upcoming work; implement exactly as specified here
```

Currently Implemented: §2 Domain Model, §3 Roles, §4 HTTP Conventions, §5 Pagination,
§6 Authentication, §7 Projects, §8 Project Members, §9 Task Status, §10 Tasks,
§11 Task Workflow, §12 Task Assignment, §14 Kanban Board, §32 Optimistic
Concurrency. The remaining sections are Planned.

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
ActivityEventType project.created | project.updated | project.archived |
                  project.restored | member.added | member.removed |
                  member.role_changed | task.created | task.updated | task.deleted |
                  task.assigned | task.unassigned | task.status_changed | task.moved |
                  relation.added | relation.removed | watcher.added | watcher.removed |
                  comment.created | comment.updated | comment.deleted |
                  comment.mentioned | label.added | label.removed
NotificationType  task.assigned | comment.created | comment.mentioned |
                  task.status_changed | task.updated | member.added
```

Event IDs (`ActivityEvent.id` and the SSE `id:` field) are opaque,
lexicographically sortable strings (ULID or UUIDv7) so they can be used directly
as `Last-Event-ID` for replay.

## 2.3 Storage Invariants

Enforced by the database, not by service-level checks alone:

```text
project_members   UNIQUE (project_id, user_id)
projects          exactly one owner: partial unique index on (owner_id) per project
                  or a constraint trigger; ownership moves only via transfer
project.key       UNIQUE
task_statuses     UNIQUE (project_id, key)
labels            UNIQUE (project_id, lower(name))
tasks             UNIQUE (project_id, number)
task_watchers     UNIQUE (task_id, user_id)
task_labels       UNIQUE (task_id, label_id)
task_relations    UNIQUE (task_id, target_task_id, type)
comments          soft-deleted rows stay unique on (id); no hard delete
tasks.deleted_at  NULL for live tasks; non-null for soft-deleted
```

`Task.number` is allocated with a per-project sequence (`SELECT ... FOR UPDATE`
on the project row or a dedicated counter table) so concurrent task creation
cannot produce duplicate `NEXA-17` keys.

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
| Delete task | Yes | Yes | Own tasks | No |
| Assign task | Yes | Yes | Yes | No |
| Change status | Yes | Yes | Yes | No |
| Comment | Yes | Yes | Yes | No |
| Manage labels | Yes | Yes | No | No |
| Watch task | Yes | Yes | Yes | Yes |

Permission checks must live in the service/policy layer rather than being duplicated inside every endpoint.

`Restricted` and `Own tasks` mean: a `member` may delete only a task they created;
`owner`/`admin` may delete any task.

## 3.3 Global Admin Policy

The global `admin` role does not grant automatic membership in every project.
Global admins get a separate platform API (`/api/v1/admin/...`, see §28) for
account management and moderation. To read or modify project data, a global
admin must be a project member like everyone else.

Exception: a moderation endpoint may soft-delete abusive content (comments,
projects) without membership, and this action is always written to the
activity log.

## 3.4 Not-Found vs Forbidden

Rule for every project-scoped resource (project, task, comment, label):

```text
404 — the resource does not exist OR the user is not a member of its project
403 — the user can see the resource but lacks permission for the action
```

This prevents resource enumeration and is the single policy for the whole API.

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

Application errors always carry a human-readable `detail` and a stable
machine-readable `code`:

```json
{
  "detail": "Task cannot transition from DONE to TODO",
  "code": "invalid_transition"
}
```

Error codes are stable identifiers meant for program handling. Clients branch
on `code`, never on the text of `detail`. Initial code registry:

```text
validation_error             422   schema violation
unauthenticated              401   missing/invalid token
token_invalid                401   refresh token rejected
forbidden                    403   member without permission
project_not_found            404   also returned to non-members
task_not_found               404   also returned to non-members
status_not_found             404   task status of a project
user_not_found               404
comment_not_found            404
label_not_found              404
already_exists               409   duplicate key, label attach, etc.
invalid_transition           409   status change not allowed
stale_version                409   If-Match mismatch (see section 32)
status_in_use                409   deleting a status that still has tasks
archived_collection          409   write operation on an archived project
payload_error                422   semantic validation (bad ids, cycles)
precondition_required        428   If-Match header missing (see section 32)
rate_limited                 429
```

The registry grows with the domain model; every new domain error gets a code
from the start rather than a bare string.

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

## 4.1 PATCH Semantics

All `PATCH` endpoints use JSON Merge Patch rules:

```text
omitted field  → unchanged
explicit null  → cleared (only nullable fields)
unknown field  → 422 validation_error
```

Each `PATCH` section below lists its editable fields explicitly. Fields with
domain meaning (`status`, `assignee`, `order`) are never editable through
`PATCH`; they change only through command endpoints (see section 33).

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

Limits and rules:

```text
page       >= 1
page_size  1..100, default 20
sort       whitelist per collection; unknown value → 422 validation_error
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

The project `key` is immutable; rename of the key is not supported because
task keys like `NEXA-17` are referenced in history and comments.

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

## POST `/api/v1/projects/{project_id}/transfer-ownership`

Transfer project ownership to another member.

### Request

```json
{
  "user_id": 17
}
```

### Response

```json
{
  "id": 42,
  "key": "NEXA",
  "name": "NexaDesk",
  "owner": {
    "id": 17,
    "username": "john"
  }
}
```

### Business rules

- Only the current owner can transfer ownership.
- The target user must already be a project member.
- After the transfer the previous owner becomes `admin`.
- Both membership rows change in one transaction; at no point a project has
  two owners (see the invariants in section 2.3).
- The caller must re-read the role from the database for this operation; a
  stale role from an access token is not enough (see section 32).

### Errors

```text
404 — project or user not found (or user is not a member)
403 — caller is not the owner
409 — target is already the owner
```

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

Request:

```json
{
  "title": "Implement production SSE notifications",
  "description": "Updated details",
  "priority": "CRITICAL",
  "due_date": "2026-10-20"
}
```

Editable fields for `PATCH`:

```text
title
description
priority
due_date
estimated_hours
parent_task_id
```

Status, assignee and rank are never editable here. See the command endpoints
in section 33.

`version` in the response grows with every change. Optimistic concurrency is
mandatory on `PATCH` and `DELETE` since Phase 1: the request must carry
`If-Match: <version>`, a mismatch is 409 stale_version (section 32).

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
  "detail": "Task cannot transition from DONE to TODO",
  "code": "invalid_transition"
}
```

### Transition matrix

In v1 transitions follow the status positions: a task may move one position
left or right inside its project. Any other target status is rejected with
409 invalid_transition. The matrix for default statuses:

```text
from \ to     TODO  IN_PROGRESS  REVIEW  DONE
TODO            -        x          -      -
IN_PROGRESS     x        -          x      -
REVIEW          -        x          -      x
DONE            -        -          x      -
```

Custom statuses join the matrix by their position, so the rule is always
the same: only adjacent columns are reachable.

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

This endpoint ships in Phase 5. A move request must include an explicit map
from source statuses to target statuses (at minimum the source status of the
moving task); the server rejects a move with unmapped status using
422 payload_error rather than guessing after project identity changed.

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

Horizontal moves between columns use the transition endpoint above:

```text
POST /api/v1/tasks/{task_id}/transition
```

Do not create a separate "move card" endpoint. Vertical ordering inside a
column has its own key set and is handled by `reorder` (below), so column
changes without reordering stay simple `transition` calls.

Cards are ordered inside every column by `rank` (see section 10). Vertical
ordering changes use a separate command endpoint because a key set change
cannot be expressed through `PATCH` semantics:

```text
POST /api/v1/tasks/{task_id}/reorder
```

Request:

```json
{
  "status_id": 1,
  "before_task_id": 91,
  "after_task_id": 87
}
```

`status_id` names the target column. It may differ from the current status;
in that case the transition matrix from section 11 still applies and the
command returns 409 invalid_transition on a forbidden move. `before_task_id`
places the card before that neighbor, `after_task_id` places it after. Send
null and null to move the card to the top of the column, or null values of
the pair for the end. The server recalculates ranks and answers with the
final position.

Board response and task lists respect `limit_per_column` on the board query
(default 50): each column returns up to that many cards plus a
`has_more` flag so huge projects stay usable. `GET /api/v1/projects/{project_id}/board?limit_per_column=50`.

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
- `@username` mentions generate a notification to the mentioned user even
  when he is not a watcher; mention parsing is done on save of the body.

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
project.archived
project.restored
comment.created
comment.updated
comment.deleted
label.added
label.removed
relation.added
relation.removed
watcher.added
watcher.removed
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
read        false returns only unread notifications (replaces a separate
            /notifications/unread endpoint)
```

---

## POST `/api/v1/notifications/{notification_id}/read`

Mark one notification as read.

Notification `type` values match activity events plus:

```text
mention
```

Mentions are created from `@username` in comment bodies (section 15).

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

For browser clients the access token travels in the `Authorization: Bearer`
header only; tokens in query strings or fragment are forbidden because URLs
end up in logs. Native `EventSource` cannot set request headers, therefore
the browser client opens the stream with `fetch` and reads `text/event-stream`
as described in section 21. Cookie sessions are not an auth path for this
stream.

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
5. Replay missed events after reconnect.

Replay is based on `ActivityEvent` rows (section 19): on reconnect the client
sends the last seen event ID (`Last-Event-ID` header), and the backend finds
the stored `ActivityEvent.id` and streams everything after it. Redis Pub/Sub
alone cannot replay; it only distributes live events, so persistence in
`activity_events` is a hard precondition for this endpoint (the EventPublisher
hook in section 31 must be wired to the outbox before SSE reaches production).

Heartbeat example:

```text
: heartbeat

```

A heartbeat comment is sent about every 15 seconds so proxies do not close
idle connections. The server limits (per client) are: one stream per project,
maximum 5 minutes idle without successful heartbeat write, and automatic
disconnect at 10k queued events (the client is expected to reconnect with
replay).

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
q        required, 2..100 characters
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

## GET `/api/v1/me`

Get the current user profile (id, username, email, global role).

## PATCH `/api/v1/me`

Update own profile: username, email. Password change is a separate command.

## POST `/api/v1/me/password`

Change own password. Requires the current password.

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

## GET `/api/v1/users`

User picker for member assignment and mentions.

### Query

```text
q          optional, min 2 characters
project_id optional, restricts to members of that project
page
page_size
```

### Response

```json
{
  "items": [
    {
      "id": 17,
      "username": "john",
      "email": "john@example.com"
    }
  ],
  "page": 1,
  "page_size": 20,
  "total": 3
}
```

Authenticated users only. Global `admin` additionally manages accounts via
`/api/v1/admin/users` (list, change global role, deactivate).

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
- deleting already deleted task (second delete returns 404)
- moving task to inaccessible project
- invalid task transition
- self-relation
- duplicate relation
- concurrent task creation in one project (number allocation race; see 2.3)
- concurrent update of one task (stale version; 409 stale_version)
- reordering against a neighbor that was deleted concurrently
- deleting a status that still has tasks (409 status_in_use)

## Idempotency

- double submit of a create command returns the same logical result or a
  clean 409 already_exists; never two rows
- marking an already read notification read is a no-op, not an error
- watch/unwatch are idempotent commands

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

For stronger delivery guarantees, use an **Outbox Pattern**:

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

The Outbox Pattern is mandatory before the SSE phase ships. Until then the
service layer publishes through the `EventPublisher` hook (introduced in
Phase 0, a no-op implementation first) strictly after commit, so switching to
outbox delivery means changing the publisher implementation only, not the
services.

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

Optimistic concurrency is mandatory since Phase 1 for tasks: `PATCH` and
`DELETE /tasks/{task_id}` require `If-Match`. Without the header the endpoint
returns 428 Precondition Required; a wrong value returns 409 stale_version.
Task mutations increment `version`. Other entities follow the same contract
later when their edit flows appear.

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
POST /tasks/{id}/reorder
POST /tasks/{id}/move          (Phase 5)
POST /tasks/{id}/watch
POST /tasks/{id}/unwatch
POST /projects/{id}/transfer-ownership
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
│   ├── GET    /                 (?read=false returns only unread)
│   ├── POST   /{notification_id}/read
│   └── POST   /read-all
│
├── users
│   └── GET    /                 (picker: search, project context, paginated)
│
├── admin
│   ├── GET    /users
│   ├── PATCH  /users/{user_id}  (is_active, role)
│   └── DELETE /users/{user_id}
│
└── search
    └── GET    /?q=...
```

---

# 35. Suggested Implementation Order

Implement the backend in this order.

## Phase 0 — Connectors and invariants of the existing app

```text
CORS: allow PATCH, DELETE, OPTIONS
is_active checks in login, refresh and access-token handling
narrow IntegrityError mapping (409 only for unique violations)
email normalization: lowercase + unique index on lower(email)
error envelope: {detail, code} with the code registry from section 4
schemas/common: Paginated[T], page_size cap 100, sort whitelist
PATCH base with exclude_unset semantics
RequireProjectRole policy helper
EventPublisher protocol + no-op implementation (hook for the outbox)
enums ProjectRole, Priority
```

Goal: the existing auth app is safe and extended infra is in place before
domain tables arrive.

---

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
