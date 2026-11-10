"""Synthetic prober entrypoint.

Runs the user journey scenario on a fixed interval and publishes the outcome
of every run as Prometheus metrics on a dedicated port, where the monitoring
stack scrapes them the same way it scrapes the application itself.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from dataclasses import dataclass

from prometheus_client import Counter, Gauge, Histogram, start_http_server

from prober.scenario import (
    DEFAULT_PROJECT_KEY,
    REQUEST_TIMEOUT_S,
    SCENARIO_NAME,
    SCENARIO_STEPS,
    ScenarioError,
    StepTiming,
    UserJourney,
)

logger = logging.getLogger("nexadesk.prober")

PROBE_RUNS_TOTAL = Counter(
    "nexadesk_probe_runs_total",
    "Synthetic probe runs by scenario and result.",
    ["scenario", "result"],
)
PROBE_SUCCESS = Gauge(
    "nexadesk_probe_success",
    "Whether the last synthetic probe run succeeded.",
    ["scenario"],
)
PROBE_DURATION_SECONDS = Histogram(
    "nexadesk_probe_duration_seconds",
    "Duration of a full synthetic probe run.",
    ["scenario"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0),
)
PROBE_STEP_DURATION_SECONDS = Histogram(
    "nexadesk_probe_step_duration_seconds",
    "Duration of one synthetic probe step.",
    ["scenario", "step"],
    buckets=(0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)
PROBE_STEP_FAILURES_TOTAL = Counter(
    "nexadesk_probe_step_failures_total",
    "Failed synthetic probe steps by scenario and step.",
    ["scenario", "step"],
)
PROBE_LAST_SUCCESS_TIMESTAMP = Gauge(
    "nexadesk_probe_last_success_timestamp_seconds",
    "Unix time of the last successful synthetic probe run.",
    ["scenario"],
)

DEFAULT_INTERVAL_S = 30.0
DEFAULT_METRICS_PORT = 9102


def init_step_failure_counters() -> None:
    """Create zero-valued failure counters for every scenario step.

    A prometheus_client Counter child is registered on first use. Publishing
    all steps at startup keeps their series present, so rate() returns 0
    instead of no data while the scenario is healthy.

    Returns:
        None
    """
    for step in SCENARIO_STEPS:
        PROBE_STEP_FAILURES_TOTAL.labels(scenario=SCENARIO_NAME, step=step)


@dataclass(frozen=True)
class Settings:
    """Configuration of the prober process.

    Attributes:
        target_url: root URL of the NexaDesk API.
        email: login email of the probe account.
        password: password of the probe account.
        username: username of the probe account, used for registration.
        project_key: key of the project the journey works in.
        interval_s: pause between two runs, in seconds.
        timeout_s: per-request timeout, in seconds.
        metrics_port: port serving the /metrics payload.
    """

    target_url: str
    email: str
    password: str
    username: str
    project_key: str = DEFAULT_PROJECT_KEY
    interval_s: float = DEFAULT_INTERVAL_S
    timeout_s: float = REQUEST_TIMEOUT_S
    metrics_port: int = DEFAULT_METRICS_PORT

    @classmethod
    def from_env(cls) -> Settings:
        """Read the configuration from PROBE_* environment variables.

        Returns:
            Settings: configuration of the prober process.
        """
        return cls(
            target_url=os.environ.get("PROBE_TARGET_URL", "http://localhost:8000"),
            email=os.environ.get("PROBE_EMAIL", "prober@nexadesk.dev"),
            password=os.environ.get("PROBE_PASSWORD", "prober-strong-pass"),
            username=os.environ.get("PROBE_USERNAME", "prober"),
            project_key=os.environ.get("PROBE_PROJECT_KEY", DEFAULT_PROJECT_KEY),
            interval_s=float(
                os.environ.get("PROBE_INTERVAL_S", DEFAULT_INTERVAL_S)
            ),
            timeout_s=float(
                os.environ.get("PROBE_TIMEOUT_S", REQUEST_TIMEOUT_S)
            ),
            metrics_port=int(
                os.environ.get("PROBE_METRICS_PORT", DEFAULT_METRICS_PORT)
            ),
        )


def record_run(
    report: list[StepTiming] | None,
    failed_step: str | None,
    duration_s: float,
) -> None:
    """Publish the outcome of one probe run.

    Args:
        report: durations of the completed steps, None on failure.
        failed_step: name of the failing step, None on success.
        duration_s: wall time of the whole run, in seconds.

    Returns:
        None
    """
    result = "error" if failed_step else "success"
    PROBE_RUNS_TOTAL.labels(scenario=SCENARIO_NAME, result=result).inc()
    PROBE_SUCCESS.labels(scenario=SCENARIO_NAME).set(0.0 if failed_step else 1.0)
    PROBE_DURATION_SECONDS.labels(scenario=SCENARIO_NAME).observe(duration_s)
    for timing in report or ():
        PROBE_STEP_DURATION_SECONDS.labels(
            scenario=SCENARIO_NAME, step=timing.step
        ).observe(timing.duration_s)
    if failed_step:
        PROBE_STEP_FAILURES_TOTAL.labels(
            scenario=SCENARIO_NAME, step=failed_step
        ).inc()
    else:
        PROBE_LAST_SUCCESS_TIMESTAMP.labels(scenario=SCENARIO_NAME).set(time.time())


async def run_forever(settings: Settings) -> None:
    """Probe the API in a loop until the process is stopped.

    The probe account is prepared before the first run; while the API is not
    reachable yet the loop keeps retrying, so the prober may start together
    with the rest of the stack.

    Args:
        settings: configuration of the prober process.

    Returns:
        None
    """
    journey = UserJourney(
        base_url=settings.target_url,
        email=settings.email,
        password=settings.password,
        username=settings.username,
        project_key=settings.project_key,
        timeout_s=settings.timeout_s,
    )
    try:
        while True:
            try:
                await journey.ensure_account()
                break
            except ScenarioError as exc:
                logger.warning("probe account is not ready yet: %s", exc)
                await asyncio.sleep(settings.interval_s)

        while True:
            started = time.perf_counter()
            try:
                report = await journey.run()
                record_run(report, None, time.perf_counter() - started)
                logger.info("probe run ok in %.3fs", time.perf_counter() - started)
            except ScenarioError as exc:
                record_run(exc.completed, exc.step, time.perf_counter() - started)
                logger.warning("probe run failed at %s: %s", exc.step, exc.detail)
            await asyncio.sleep(settings.interval_s)
    finally:
        await journey.close()


def main() -> None:
    """Start the metrics endpoint and the probe loop.

    Returns:
        None
    """
    logging.basicConfig(
        level=os.environ.get("PROBE_LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    settings = Settings.from_env()
    init_step_failure_counters()
    start_http_server(settings.metrics_port)
    logger.info(
        "probing %s every %.0fs, metrics on :%d",
        settings.target_url,
        settings.interval_s,
        settings.metrics_port,
    )
    try:
        asyncio.run(run_forever(settings))
    except KeyboardInterrupt:
        logger.info("prober stopped")


if __name__ == "__main__":
    main()
