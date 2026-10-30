"""Fault injection for reliability demos.

The module backs the SLI/SLO screencast: it can degrade request handling on
demand so that the RED metrics, the SLI dashboards and the SLO alerts react to
a controlled change of application behaviour. The active configuration is a
plain process-wide state that the fault API updates and the fault guard reads.

The guard is mounted as a router-level dependency, so it runs after routing and
before the domain layer: metrics keep the real route template of the request
and no domain side effects happen for the requests it fails. Health probes and
the fault API itself never see injected faults.
"""

import asyncio
import random
import threading
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Literal

from fastapi import HTTPException, status

from app.core.metrics import (
    FAULT_INJECTED_TOTAL,
    FAULT_INJECTION_ACTIVE,
)

MODE_OFF: Literal["off"] = "off"
MODE_ERRORS: Literal["errors"] = "errors"
MODE_LATENCY: Literal["latency"] = "latency"
MODE_DEGRADED: Literal["degraded"] = "degraded"
FAULT_MODES = (MODE_OFF, MODE_ERRORS, MODE_LATENCY, MODE_DEGRADED)

DEFAULT_RATE = 1.0
DEFAULT_LATENCY_MS = 2000

INJECTED_ERROR_STATUS = status.HTTP_503_SERVICE_UNAVAILABLE
INJECTED_ERROR_DETAIL = "injected fault"


@dataclass(frozen=True)
class FaultConfig:
    """Active fault injection configuration.

    Attributes:
        mode: one of off, errors, latency or degraded.
        rate: share of requests affected by the injected errors, 0..1.
        latency_ms: extra delay added to every affected request, in ms.
    """

    mode: str = MODE_OFF
    rate: float = DEFAULT_RATE
    latency_ms: int = DEFAULT_LATENCY_MS

    @property
    def active(self) -> bool:
        """Tell whether the configuration degrades request handling.

        Returns:
            bool: True when a fault mode other than off is selected.
        """
        return self.mode != MODE_OFF


class FaultState:
    """Thread-safe holder of the fault configuration of the process."""

    def __init__(self) -> None:
        """Start with injection switched off."""
        self._lock = threading.Lock()
        self._config = FaultConfig()

    @property
    def config(self) -> FaultConfig:
        """Read the current configuration.

        Returns:
            FaultConfig: immutable snapshot of the active configuration.
        """
        with self._lock:
            return self._config

    def set(self, config: FaultConfig) -> FaultConfig:
        """Replace the current configuration.

        Args:
            config: new fault configuration.

        Returns:
            FaultConfig: the configuration that is now active.
        """
        with self._lock:
            self._config = config
        FAULT_INJECTION_ACTIVE.set(1.0 if config.active else 0.0)
        return self._config

    def reset(self) -> FaultConfig:
        """Switch injection off.

        Returns:
            FaultConfig: the off configuration that is now active.
        """
        return self.set(FaultConfig())


fault_state = FaultState()

_rng: Callable[[], float] = random.random
_sleeper: Callable[[float], Awaitable[None]] = asyncio.sleep


def configure(
    mode: str,
    rate: float = DEFAULT_RATE,
    latency_ms: int = DEFAULT_LATENCY_MS,
) -> FaultConfig:
    """Update the fault state after validating the request values.

    Args:
        mode: one of off, errors, latency or degraded.
        rate: share of requests affected by the injected errors, 0..1.
        latency_ms: extra delay added to every affected request, in ms.

    Returns:
        FaultConfig: the configuration that is now active.
    """
    config = FaultConfig(
        mode=mode if mode in FAULT_MODES else MODE_OFF,
        rate=min(max(rate, 0.0), 1.0),
        latency_ms=max(int(latency_ms), 0),
    )
    return fault_state.set(config)


def degrade(config: FaultConfig, rng: Callable[[], float]) -> str:
    """Pick the fault that applies to one request.

    Args:
        config: active fault configuration.
        rng: source of randomness in [0, 1).

    Returns:
        str: injected fault kind, "error", "latency" or "none".
    """
    if not config.active:
        return "none"
    if config.mode in (MODE_ERRORS, MODE_DEGRADED) and rng() < config.rate:
        return "error"
    if config.mode in (MODE_LATENCY, MODE_DEGRADED):
        return "latency"
    return "none"


async def fault_guard() -> None:
    """Fail or delay one request according to the active fault state.

    Raises:
        HTTPException: 503 for the requests selected for error injection.

    Returns:
        None
    """
    config = fault_state.config
    kind = degrade(config, _rng)
    if kind == "error":
        FAULT_INJECTED_TOTAL.labels(kind="error").inc()
        raise HTTPException(
            status_code=INJECTED_ERROR_STATUS, detail=INJECTED_ERROR_DETAIL
        )
    if kind == "latency":
        FAULT_INJECTED_TOTAL.labels(kind="latency").inc()
        await _sleeper(config.latency_ms / 1000)
