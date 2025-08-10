"""
Lightweight latency instrumentation for the bot.

Usage (minimal):
    from latency import LT
    LT.mark('capture_start')
    ... take screenshot ...
    LT.mark('capture_end')
    ... perception ...
    LT.mark('perception_end')
    ... decision ...
    LT.mark('decision_end')
    ... just before issuing tap/swipe ...
    LT.mark('action_issue')
    # optionally after detecting a UI change on screen
    LT.mark('effect_seen')
    LT.flush(extra={'phase':'pve'})

This will append a row into latency_metrics.csv with durations and timestamps.
"""
from __future__ import annotations

import csv
import os
import threading
import time
from dataclasses import dataclass, field
from typing import Dict, Optional, Iterable
from contextlib import contextmanager
from collections import deque


_HEADER = [
    'ts',
    'capture_start', 'capture_end',
    'perception_end', 'decision_end',
    'action_issue', 'effect_seen',
    # Derived
    'capture_ms', 'perception_ms', 'decision_ms', 'screenshot_to_action_ms', 'effect_ms',
    'phase'
]


def _now() -> float:
    return time.perf_counter()


@dataclass
class _State:
    marks: Dict[str, float] = field(default_factory=dict)


class LatencyTracker:
    def __init__(self, csv_path: str = 'latency_metrics.csv') -> None:
        self._csv_path = csv_path
        self._local = threading.local()
        self._ensure_header()
    # enable/disable via env
    self.enabled = os.getenv('LATENCY_ENABLED', '1') not in ('0', 'false', 'False')
    # rolling stats
    self._roll = deque(maxlen=int(os.getenv('LATENCY_ROLLING_N', '200')))
    self._flush_count = 0
    self._summary_every = int(os.getenv('LATENCY_SUMMARY_EVERY', '50'))
    self._summary_path = os.getenv('LATENCY_SUMMARY_PATH', 'latency_summary.txt')

    def _ensure_header(self) -> None:
        if not os.path.exists(self._csv_path):
            with open(self._csv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(_HEADER)

    def _get_state(self) -> _State:
        st: Optional[_State] = getattr(self._local, 'state', None)
        if st is None:
            st = _State()
            self._local.state = st
        return st

    def mark(self, name: str) -> None:
        if not self.enabled:
            return
        st = self._get_state()
        st.marks[name] = _now()

    @contextmanager
    def span(self, start_name: str, end_name: str):
        """Context manager to measure a span without manual marks."""
        if not self.enabled:
            yield
            return
        self.mark(start_name)
        try:
            yield
        finally:
            self.mark(end_name)

    def flush(self, extra: Optional[Dict[str, str]] = None) -> None:
        if not self.enabled:
            return
        st = self._get_state()
        m = st.marks
        ts = time.time()
        # Durations (ms)
        capture_ms = self._delta_ms(m, 'capture_start', 'capture_end')
        perception_ms = self._delta_ms(m, 'capture_end', 'perception_end')
        decision_ms = self._delta_ms(m, 'perception_end', 'decision_end')
        screenshot_to_action_ms = self._delta_ms(m, 'capture_end', 'action_issue')
        effect_ms = self._delta_ms(m, 'action_issue', 'effect_seen')

        row = [
            f'{ts:.3f}',
            self._fmt(m.get('capture_start')), self._fmt(m.get('capture_end')),
            self._fmt(m.get('perception_end')), self._fmt(m.get('decision_end')),
            self._fmt(m.get('action_issue')), self._fmt(m.get('effect_seen')),
            self._fmt(capture_ms), self._fmt(perception_ms), self._fmt(decision_ms),
            self._fmt(screenshot_to_action_ms), self._fmt(effect_ms),
            (extra or {}).get('phase', '')
        ]

        with open(self._csv_path, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(row)

        # update rolling stats with primary KPI (screenshot_to_action_ms)
        if screenshot_to_action_ms is not None:
            self._roll.append(float(screenshot_to_action_ms))
        self._flush_count += 1
        if self._summary_every > 0 and self._flush_count % self._summary_every == 0:
            self._write_summary()

        # Reset marks for next sample
        st.marks = {}

    @staticmethod
    def _delta_ms(marks: Dict[str, float], a: str, b: str) -> Optional[float]:
        va = marks.get(a)
        vb = marks.get(b)
        if va is None or vb is None:
            return None
        return (vb - va) * 1000.0

    @staticmethod
    def _fmt(v: Optional[float]) -> str:
        if v is None:
            return ''
        return f'{v:.3f}'

    # --- Extras ---
    def set_enabled(self, enabled: bool) -> None:
        self.enabled = enabled

    def rolling_stats(self) -> Dict[str, float]:
        """Return rolling stats for screenshot->action KPI over the recent window."""
        if not self._roll:
            return {'count': 0, 'avg_ms': 0.0, 'p50_ms': 0.0, 'p90_ms': 0.0, 'p99_ms': 0.0}
        data = sorted(self._roll)
        n = len(data)
        def q(p: float) -> float:
            if n == 0:
                return 0.0
            idx = min(n - 1, max(0, int(p * (n - 1))))
            return data[idx]
        avg = sum(data) / n
        return {
            'count': float(n),
            'avg_ms': float(avg),
            'p50_ms': float(q(0.50)),
            'p90_ms': float(q(0.90)),
            'p99_ms': float(q(0.99)),
        }

    def _write_summary(self) -> None:
        stats = self.rolling_stats()
        line = (
            f"count={int(stats['count'])} avg={stats['avg_ms']:.1f}ms "
            f"p50={stats['p50_ms']:.1f}ms p90={stats['p90_ms']:.1f}ms p99={stats['p99_ms']:.1f}ms\n"
        )
        try:
            with open(self._summary_path, 'a', encoding='utf-8') as f:
                f.write(line)
        except Exception:
            pass


# Singleton shortcut
LT = LatencyTracker()
