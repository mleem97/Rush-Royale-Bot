from __future__ import annotations

import pytest

from rushbot.actions import (
    ActionPlan,
    KeyEventAction,
    StartPackageAction,
    StopPackageAction,
    SwipeAction,
    TapAction,
    WaitAction,
    execute_plan,
)
from rushbot.target import Point, ScreenGeometry, Size


class FakeTarget:
    serial = "fixture"
    geometry = ScreenGeometry.from_frame(Size(900, 1600))

    def __init__(self) -> None:
        self.calls: list[tuple[object, ...]] = []

    def capture_png(self, output_path: object = None) -> bytes:
        return b""

    def tap_reference(self, point: Point) -> object:
        self.calls.append(("tap", point))
        return point

    def swipe_reference(
        self,
        start: Point,
        end: Point,
        *,
        duration_ms: int = 300,
    ) -> object:
        self.calls.append(("swipe", start, end, duration_ms))
        return start, end

    def keyevent(self, keycode: int | str) -> None:
        self.calls.append(("keyevent", keycode))

    def start_package(self, package_name: str) -> str:
        self.calls.append(("start", package_name))
        return "started"

    def force_stop_package(self, package_name: str) -> None:
        self.calls.append(("stop", package_name))


def complete_plan() -> ActionPlan:
    return ActionPlan(
        actions=(
            TapAction(Point(10, 20)),
            SwipeAction(Point(1, 2), Point(3, 4), duration_ms=500),
            KeyEventAction("BACK"),
            StartPackageAction("com.example.game"),
            WaitAction(0.25),
            StopPackageAction("com.example.game"),
        ),
        reason="replay fixture",
        confidence=0.95,
        source_frame_id="sha256:test",
    )


def test_execute_complete_plan() -> None:
    target = FakeTarget()
    sleeps: list[float] = []

    report = execute_plan(target, complete_plan(), sleep=sleeps.append)

    assert report.attempted == 6
    assert report.executed == 6
    assert not report.cancelled
    assert sleeps == [0.25]
    assert target.calls == [
        ("tap", Point(10, 20)),
        ("swipe", Point(1, 2), Point(3, 4), 500),
        ("keyevent", "BACK"),
        ("start", "com.example.game"),
        ("stop", "com.example.game"),
    ]


def test_execute_plan_honors_cancellation_before_next_action() -> None:
    target = FakeTarget()
    checks = iter([False, True])
    plan = ActionPlan(
        actions=(TapAction(Point(1, 1)), TapAction(Point(2, 2))),
        reason="cancellation test",
        confidence=1.0,
    )

    report = execute_plan(target, plan, should_cancel=lambda: next(checks))

    assert report.executed == 1
    assert report.cancelled
    assert target.calls == [("tap", Point(1, 1))]


@pytest.mark.parametrize(
    "constructor",
    [
        lambda: SwipeAction(Point(0, 0), Point(1, 1), duration_ms=-1),
        lambda: WaitAction(-0.1),
        lambda: ActionPlan(actions=(), reason="", confidence=1.0),
        lambda: ActionPlan(actions=(), reason="test", confidence=-0.1),
        lambda: ActionPlan(actions=(), reason="test", confidence=1.1),
    ],
)
def test_action_validation(constructor: object) -> None:
    with pytest.raises(ValueError):
        constructor()  # type: ignore[operator]
