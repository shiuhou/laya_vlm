"""Environment adapter protocols.

Adapters isolate LIBERO/robosuite or MuJoCo-specific observation and action layouts
from the model-facing runtime. They can be implemented without changing the fusion or
decision code.
"""
from __future__ import annotations

from typing import Any, Protocol


class EnvironmentAdapter(Protocol):
    def reset(self, seed: int | None = None) -> Any: ...
    def observe(self) -> dict[str, Any]: ...
    def step(self, action: Any) -> Any: ...
    def success(self) -> bool: ...
    def close(self) -> None: ...


class ObservationBuilder(Protocol):
    def build(self, raw: dict[str, Any], sim_time: float) -> list[dict[str, Any]]: ...
