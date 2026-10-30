"""Synthetic user journey against the NexaDesk API.

One run imitates what a real user does: log in, make sure a project exists,
create a task, move it across the board, leave a comment and read the
notification inbox. Every step is timed; any failure marks the whole run as
failed, which is what the user journey availability SLI measures.
"""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TypeVar

import httpx

SCENARIO_NAME = "user_journey"

STEP_LOGIN = "login"
STEP_ENSURE_PROJECT = "ensure_project"
STEP_CREATE_TASK = "create_task"
STEP_TRANSITION_TASK = "transition_task"
STEP_ADD_COMMENT = "add_comment"
STEP_LIST_NOTIFICATIONS = "list_notifications"

SCENARIO_STEPS = (
    STEP_LOGIN,
    STEP_ENSURE_PROJECT,
    STEP_CREATE_TASK,
    STEP_TRANSITION_TASK,
    STEP_ADD_COMMENT,
    STEP_LIST_NOTIFICATIONS,
)

DEFAULT_PROJECT_KEY = "PROBE"
DEFAULT_PROJECT_NAME = "Synthetic Probing"

REQUEST_TIMEOUT_S = 10.0
ERROR_BODY_LIMIT = 200

T = TypeVar("T")


class StepFailure(Exception):
    """One scenario step did not get the expected answer from the API."""


class ScenarioError(Exception):
    """The user journey stopped because one of its steps failed.

    Attributes:
        step: name of the failing step.
        detail: human readable failure reason.
        completed: durations of the steps finished before the failure.
    """

    def __init__(self, step: str, detail: str, completed: list[StepTiming]) -> None:
        """Store the failure context of one run.

        Args:
            step: name of the failing step.
            detail: human readable failure reason.
            completed: durations of the steps finished before the failure.
        """
        super().__init__(f"{step}: {detail}")
        self.step = step
        self.detail = detail
        self.completed = completed


@dataclass(frozen=True)
class StepTiming:
    """Duration of one completed scenario step.

    Attributes:
        step: step name.
        duration_s: wall time spent in the step, in seconds.
    """

    step: str
    duration_s: float


class UserJourney:
    """Executes the synthetic user journey against one API deployment."""

    def __init__(
        self,
        base_url: str,
        email: str,
        password: str,
        username: str,
        project_key: str = DEFAULT_PROJECT_KEY,
        timeout_s: float = REQUEST_TIMEOUT_S,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        """Prepare the journey with its own HTTP client.

        Args:
            base_url: root URL of the NexaDesk API.
            email: email the probe account is registered with.
            password: password of the probe account.
            username: username of the probe account, used for registration
                and login.
            project_key: key of the project the journey works in.
            timeout_s: per-request timeout, in seconds.
            client: preconfigured client, one is created when omitted.
        """
        self._email = email
        self._password = password
        self._username = username
        self._project_key = project_key
        self._client = client or httpx.AsyncClient(
            base_url=base_url, timeout=timeout_s
        )
        self._token: str | None = None
        self._project_id: int | None = None
        self._task_status_key: str | None = None
        self.step_results: list[StepTiming] = []

    async def close(self) -> None:
        """Release the HTTP client owned by the journey.

        Returns:
            None
        """
        await self._client.aclose()

    async def ensure_account(self) -> None:
        """Make sure the probe account exists and can log in.

        Registers the account on first use, so the journey needs no manual
        seeding of the database.

        Returns:
            None

        Raises:
            ScenarioError: when neither login nor registration works.
        """
        try:
            await self._login()
        except (ScenarioError, StepFailure):
            try:
                await self._register()
                await self._login()
            except (ScenarioError, StepFailure) as exc:
                raise ScenarioError(STEP_LOGIN, str(exc), []) from exc

    async def run(self) -> list[StepTiming]:
        """Run the whole user journey once.

        Returns:
            list[StepTiming]: duration of every completed step.

        Raises:
            ScenarioError: when any step fails.
        """
        self.step_results = []
        await self._measure(STEP_LOGIN, self._login)
        project_id = await self._measure(STEP_ENSURE_PROJECT, self._ensure_project)
        task_id = await self._measure(
            STEP_CREATE_TASK, lambda: self._create_task(project_id)
        )
        await self._measure(
            STEP_TRANSITION_TASK,
            lambda: self._transition_task(project_id, task_id),
        )
        await self._measure(STEP_ADD_COMMENT, lambda: self._add_comment(task_id))
        await self._measure(STEP_LIST_NOTIFICATIONS, self._list_notifications)
        return list(self.step_results)

    async def _measure(self, step: str, action: Callable[[], Awaitable[T]]) -> T:
        """Run one step, timing it and folding failures into a ScenarioError.

        Args:
            step: step name used for the timing record.
            action: coroutine function performing the step.

        Returns:
            T: whatever the step returns.

        Raises:
            ScenarioError: when the step fails.
        """
        started = time.perf_counter()
        try:
            result = await action()
        except ScenarioError:
            raise
        except (StepFailure, httpx.HTTPError) as exc:
            raise ScenarioError(
                step, f"{type(exc).__name__}: {exc}", list(self.step_results)
            ) from exc
        self.step_results.append(StepTiming(step, time.perf_counter() - started))
        return result

    async def _login(self) -> str:
        """Log in and remember the access token.

        Returns:
            str: the issued access token.

        Raises:
            StepFailure: when the API rejects the credentials.
        """
        response = await self._client.post(
            "/api/v1/login",
            data={"username": self._username, "password": self._password},
        )
        self._ensure_status(response, (200,))
        self._token = response.json()["access_token"]
        return self._token

    async def _register(self) -> None:
        """Register the probe account, tolerating an existing one.

        Raises:
            StepFailure: when the API refuses the registration for a reason
                other than an already taken account.
        """
        response = await self._client.post(
            "/api/v1/register",
            json={
                "username": self._username,
                "email": self._email,
                "password": self._password,
            },
        )
        self._ensure_status(response, (201, 409))

    async def _ensure_project(self) -> int:
        """Find or create the project the journey works in.

        Returns:
            int: project id.

        Raises:
            StepFailure: when no project can be prepared.
        """
        response = await self._client.get(
            "/api/v1/projects",
            params={"page": 1, "page_size": 100},
            headers=self._auth_headers(),
        )
        self._ensure_status(response, (200,))
        for item in response.json()["items"]:
            if item["key"] == self._project_key:
                self._project_id = item["id"]
                return self._project_id

        response = await self._client.post(
            "/api/v1/projects",
            json={"key": self._project_key, "name": DEFAULT_PROJECT_NAME},
            headers=self._auth_headers(),
        )
        self._ensure_status(response, (201,))
        self._project_id = response.json()["id"]
        return self._project_id

    async def _create_task(self, project_id: int) -> int:
        """Create one task in the probe project.

        Args:
            project_id: project to create the task in.

        Returns:
            int: id of the created task.

        Raises:
            StepFailure: when the task cannot be created.
        """
        response = await self._client.post(
            f"/api/v1/projects/{project_id}/tasks",
            json={"title": f"Probe task {int(time.time())}", "priority": "MEDIUM"},
            headers=self._auth_headers(),
        )
        self._ensure_status(response, (201,))
        self._task_status_key = response.json()["status"]["key"]
        return response.json()["id"]

    async def _transition_task(self, project_id: int, task_id: int) -> None:
        """Move the probe task to an adjacent board column.

        Args:
            project_id: project owning the task.
            task_id: task to move.

        Raises:
            StepFailure: when the board has no adjacent column to move to or
                the move is rejected.
        """
        response = await self._client.get(
            f"/api/v1/projects/{project_id}/statuses",
            headers=self._auth_headers(),
        )
        self._ensure_status(response, (200,))
        statuses = sorted(response.json(), key=lambda item: item["position"])
        keys = [item["key"] for item in statuses]
        current = keys.index(self._task_status_key or keys[0])
        neighbour = current + 1 if current + 1 < len(statuses) else current - 1
        if neighbour < 0:
            raise StepFailure("the project board has no adjacent column")

        response = await self._client.post(
            f"/api/v1/tasks/{task_id}/transition",
            json={"status_id": statuses[neighbour]["id"]},
            headers=self._auth_headers(),
        )
        self._ensure_status(response, (200,))

    async def _add_comment(self, task_id: int) -> None:
        """Leave one comment on the probe task.

        Args:
            task_id: task to comment on.

        Raises:
            StepFailure: when the comment cannot be created.
        """
        response = await self._client.post(
            f"/api/v1/tasks/{task_id}/comments",
            json={"body": "Synthetic probe comment"},
            headers=self._auth_headers(),
        )
        self._ensure_status(response, (201,))

    async def _list_notifications(self) -> None:
        """Read the notification inbox of the probe account.

        Raises:
            StepFailure: when the inbox cannot be read.
        """
        response = await self._client.get(
            "/api/v1/notifications",
            params={"page": 1, "page_size": 10},
            headers=self._auth_headers(),
        )
        self._ensure_status(response, (200,))

    def _auth_headers(self) -> dict[str, str]:
        """Build the authorization header of the logged in account.

        Returns:
            dict[str, str]: bearer token headers.
        """
        return {"Authorization": f"Bearer {self._token or ''}"}

    def _ensure_status(
        self, response: httpx.Response, expected: tuple[int, ...]
    ) -> None:
        """Fail one step when the API answered with an unexpected status.

        Args:
            response: answer to check.
            expected: status codes the step accepts.

        Returns:
            None

        Raises:
            StepFailure: when the status code is not expected.
        """
        if response.status_code not in expected:
            body = response.text[:ERROR_BODY_LIMIT]
            raise StepFailure(
                f"{response.request.method} {response.request.url.path} "
                f"answered {response.status_code}: {body}"
            )
