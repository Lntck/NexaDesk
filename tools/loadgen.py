"""Background load generator for the NexaDesk SLI/SLO screencast.

The script keeps a steady stream of user-like traffic flowing to the API so
that the RED metrics and the SLI dashboards move while the demo changes the
application behaviour. Every iteration performs one weighted mix of reads and
writes through the same endpoints a real user would use.

Usage:
    python tools/loadgen.py --target http://localhost:8080 --rps 5
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import random
import time

import httpx

logger = logging.getLogger("nexadesk.loadgen")

LOGIN_PATH = "/api/v1/login"
REGISTER_PATH = "/api/v1/register"
PROJECTS_PATH = "/api/v1/projects"

WEIGHTS = {
    "list_tasks": 3,
    "read_board": 2,
    "create_task": 2,
    "transition_task": 2,
    "add_comment": 1,
    "read_notifications": 1,
}


class LoadSession:
    """Drives one authenticated traffic mix against the API."""

    def __init__(
        self,
        client: httpx.AsyncClient,
        email: str,
        password: str,
        project_key: str,
    ) -> None:
        """Prepare the session.

        Args:
            client: HTTP client with the API base URL configured.
            email: login email of the load account.
            password: password of the load account.
            project_key: key of the project the traffic works in.
        """
        self._client = client
        self._email = email
        self._password = password
        self._project_key = project_key
        self._token: str | None = None
        self._project_id: int | None = None

    async def start(self) -> None:
        """Log in and prepare the project used by the traffic.

        Returns:
            None
        """
        await self._login()
        response = await self._client.get(
            PROJECTS_PATH,
            params={"page": 1, "page_size": 100},
            headers=self._headers(),
        )
        response.raise_for_status()
        for item in response.json()["items"]:
            if item["key"] == self._project_key:
                self._project_id = item["id"]
                return

        response = await self._client.post(
            PROJECTS_PATH,
            json={"key": self._project_key, "name": "Load Generation"},
            headers=self._headers(),
        )
        response.raise_for_status()
        self._project_id = response.json()["id"]

    async def step(self) -> str:
        """Perform one weighted user action.

        Returns:
            str: name of the performed action.
        """
        action = random.choices(list(WEIGHTS), weights=list(WEIGHTS.values()))[0]
        try:
            await getattr(self, f"_{action}")()
        except httpx.HTTPError as exc:
            logger.warning("%s failed: %s", action, exc)
        return action

    async def _login(self) -> None:
        """Refresh the access token of the load account.

        Returns:
            None
        """
        response = await self._client.post(
            LOGIN_PATH,
            data={"username": self._email, "password": self._password},
        )
        if response.status_code == 401:
            await self._client.post(
                REGISTER_PATH,
                json={
                    "username": self._email.split("@")[0],
                    "email": self._email,
                    "password": self._password,
                },
            )
            response = await self._client.post(
                LOGIN_PATH,
                data={"username": self._email, "password": self._password},
            )
        response.raise_for_status()
        self._token = response.json()["access_token"]

    async def _list_tasks(self) -> None:
        """Read one page of tasks.

        Returns:
            None
        """
        response = await self._client.get(
            f"{PROJECTS_PATH}/{self._project_id}/tasks",
            params={"page": 1, "page_size": 20},
            headers=self._headers(),
        )
        response.raise_for_status()

    async def _read_board(self) -> None:
        """Read the project board.

        Returns:
            None
        """
        response = await self._client.get(
            f"{PROJECTS_PATH}/{self._project_id}/board",
            headers=self._headers(),
        )
        response.raise_for_status()

    async def _create_task(self) -> None:
        """Create one task.

        Returns:
            None
        """
        response = await self._client.post(
            f"{PROJECTS_PATH}/{self._project_id}/tasks",
            json={"title": f"Load task {int(time.time() * 1000)}"},
            headers=self._headers(),
        )
        response.raise_for_status()

    async def _transition_task(self) -> None:
        """Move one random task to an adjacent board column.

        Returns:
            None
        """
        response = await self._client.get(
            f"{PROJECTS_PATH}/{self._project_id}/tasks",
            params={"page": 1, "page_size": 20},
            headers=self._headers(),
        )
        response.raise_for_status()
        items = response.json()["items"]
        if not items:
            return
        task = random.choice(items)

        response = await self._client.get(
            f"{PROJECTS_PATH}/{self._project_id}/statuses",
            headers=self._headers(),
        )
        response.raise_for_status()
        statuses = sorted(response.json(), key=lambda item: item["position"])
        keys = [item["key"] for item in statuses]
        current = keys.index(task["status"]["key"])
        neighbour = current + 1 if current + 1 < len(statuses) else current - 1
        if neighbour < 0:
            return

        response = await self._client.post(
            f"/api/v1/tasks/{task['id']}/transition",
            json={"status_id": statuses[neighbour]["id"]},
            headers=self._headers(),
        )
        response.raise_for_status()

    async def _add_comment(self) -> None:
        """Comment on one random task.

        Returns:
            None
        """
        response = await self._client.get(
            f"{PROJECTS_PATH}/{self._project_id}/tasks",
            params={"page": 1, "page_size": 20},
            headers=self._headers(),
        )
        response.raise_for_status()
        items = response.json()["items"]
        if not items:
            return
        task = random.choice(items)

        response = await self._client.post(
            f"/api/v1/tasks/{task['id']}/comments",
            json={"body": "Load generation comment"},
            headers=self._headers(),
        )
        response.raise_for_status()

    async def _read_notifications(self) -> None:
        """Read one page of notifications.

        Returns:
            None
        """
        response = await self._client.get(
            "/api/v1/notifications",
            params={"page": 1, "page_size": 10},
            headers=self._headers(),
        )
        response.raise_for_status()

    def _headers(self) -> dict[str, str]:
        """Build the authorization header of the load account.

        Returns:
            dict[str, str]: bearer token headers.
        """
        return {"Authorization": f"Bearer {self._token or ''}"}


async def generate(args: argparse.Namespace) -> None:
    """Drive traffic until the requested duration is over.

    Args:
        args: command line arguments.

    Returns:
        None
    """
    async with httpx.AsyncClient(
        base_url=args.target, timeout=httpx.Timeout(10.0)
    ) as client:
        session = LoadSession(client, args.email, args.password, args.project_key)
        await session.start()
        logger.info("generating %.1f rps against %s", args.rps, args.target)

        deadline = time.perf_counter() + args.duration if args.duration else None
        delay = 1.0 / args.rps
        while deadline is None or time.perf_counter() < deadline:
            started = time.perf_counter()
            action = await session.step()
            logger.debug("performed %s", action)
            pause = delay - (time.perf_counter() - started)
            if pause > 0:
                await asyncio.sleep(pause)


def main() -> None:
    """Parse the arguments and run the generator.

    Returns:
        None
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", default="http://localhost:8080")
    parser.add_argument("--rps", type=float, default=5.0)
    parser.add_argument(
        "--duration",
        type=float,
        default=0.0,
        help="stop after this many seconds, 0 means run until interrupted",
    )
    parser.add_argument("--email", default="loadgen@nexadesk.local")
    parser.add_argument("--password", default="loadgen-strong-pass")
    parser.add_argument("--project-key", default="LOAD")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    try:
        asyncio.run(generate(args))
    except KeyboardInterrupt:
        logger.info("load generator stopped")


if __name__ == "__main__":
    main()
