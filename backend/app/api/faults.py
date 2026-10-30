"""Demo fault injection control API.

The endpoints switch request degradation on and off during the SLI/SLO
screencast. They are mounted only when the application runs with
FAULTS_ENABLED=true, so production builds do not expose the toggle at all.
"""

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.core.faults import (
    DEFAULT_LATENCY_MS,
    DEFAULT_RATE,
    MODE_OFF,
    FaultConfig,
    configure,
    fault_state,
)

router = APIRouter(prefix="/internal/faults", tags=["Faults"])


class FaultConfigRead(BaseModel):
    """Currently active fault injection configuration.

    Attributes:
        mode: one of off, errors, latency or degraded.
        rate: share of requests affected by the injected errors, 0..1.
        latency_ms: extra delay added to every affected request, in ms.
        active: whether the mode degrades request handling.
    """

    mode: str
    rate: float
    latency_ms: int
    active: bool


class FaultConfigUpdate(BaseModel):
    """Requested fault injection configuration.

    Attributes:
        mode: one of off, errors, latency or degraded.
        rate: share of requests affected by the injected errors, 0..1.
        latency_ms: extra delay added to every affected request, in ms.
    """

    mode: Literal["off", "errors", "latency", "degraded"] = MODE_OFF
    rate: float = Field(default=DEFAULT_RATE, ge=0.0, le=1.0)
    latency_ms: int = Field(default=DEFAULT_LATENCY_MS, ge=0, le=60_000)


def _read(config: FaultConfig) -> FaultConfigRead:
    """Project the internal configuration onto the response schema.

    Args:
        config: active fault configuration.

    Returns:
        FaultConfigRead: response payload.
    """
    return FaultConfigRead(
        mode=config.mode,
        rate=config.rate,
        latency_ms=config.latency_ms,
        active=config.active,
    )


@router.get("", response_model=FaultConfigRead)
async def read_faults():
    """Report the active fault injection configuration.

    Returns:
        FaultConfigRead: the configuration currently in effect.
    """
    return _read(fault_state.config)


@router.post("", response_model=FaultConfigRead)
async def set_faults(data: FaultConfigUpdate):
    """Switch fault injection to the requested configuration.

    Args:
        data: requested fault configuration.

    Returns:
        FaultConfigRead: the configuration that is now active.
    """
    return _read(configure(data.mode, data.rate, data.latency_ms))


@router.delete("", response_model=FaultConfigRead)
async def reset_faults():
    """Switch fault injection off.

    Returns:
        FaultConfigRead: the off configuration that is now active.
    """
    return _read(fault_state.reset())
