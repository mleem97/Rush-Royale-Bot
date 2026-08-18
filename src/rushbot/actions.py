"""Pure, serializable action plans separated from perception and transport."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TypeAlias

from rushbot.target import AndroidTarget, Point


@dataclass(frozen=True, slots=True)
class TapAction:
    point: Point


@dataclass(frozen=True, slots=True)
class SwipeAction:
    start: Point
    end: Point
    duration_ms: int = 300

    def __post_init__(self) -> None:
        if self.duration_ms < 0:
            raise ValueError("Swipe duration must not be negative.")


@dataclass(frozen=True, slots=True)
class KeyEventAction:
    keycode: int | str


@dataclass(frozen=True, slots=True)
class StartPackageAction:
    package_name: str


@dataclass(frozen=True, slots=True)
class StopPackageAction:
    package_name: str


@dataclass(frozen=True, slots=True)
class WaitAction:
    seconds: float

    def __post_init__(self) -> None:
        if self.seconds < 0:
            raise ValueError("Wait duration must not be negative.")


Action: TypeAlias = (
    TapAction
    | SwipeAction
    | KeyEventAction
    | StartPackageAction
    | StopPackageAction
    | WaitAction
)


@dataclass(frozen=True, slots=True)
class ActionPlan:
    """Decision output that can be replayed without importing perception code."""

    actions: tuple[Action, ...]
    reason: str
    confidence: float
    source_frame_id: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.reason.strip():
            raise ValueError("Action plan reason must not be empty.")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Action plan confidence must be between 0 and 1.")


@dataclass(frozen=True, slots=True)
class ExecutionReport:
    attempted: int
    executed: int
    cancelled: bool


CancellationCheck: TypeAlias = Callable[[], bool]
Sleeper: TypeAlias = Callable[[float], None]


def execute_plan(
    target: AndroidTarget,
    plan: ActionPlan,
    *,
    should_cancel: CancellationCheck = lambda: False,
    sleep: Sleeper = time.sleep,
) -> ExecutionReport:
    """Execute a previously produced plan in order with a cancellation gate."""

    executed = 0
    for action in plan.actions:
        if should_cancel():
            return ExecutionReport(
                attempted=len(plan.actions),
                executed=executed,
                cancelled=True,
            )
        if isinstance(action, TapAction):
            target.tap_reference(action.point)
        elif isinstance(action, SwipeAction):
            target.swipe_reference(
                action.start,
                action.end,
                duration_ms=action.duration_ms,
            )
        elif isinstance(action, KeyEventAction):
            target.keyevent(action.keycode)
        elif isinstance(action, StartPackageAction):
            target.start_package(action.package_name)
        elif isinstance(action, StopPackageAction):
            target.force_stop_package(action.package_name)
        elif isinstance(action, WaitAction):
            sleep(action.seconds)
        else:  # pragma: no cover - impossible with the closed Action union
            raise TypeError(f"Unsupported action type: {type(action).__name__}")
        executed += 1
    return ExecutionReport(
        attempted=len(plan.actions),
        executed=executed,
        cancelled=False,
    )
