from __future__ import annotations

import threading
import time
from collections.abc import Callable
from typing import Any


class EffectiveTimer:
    """Thread-safe solve timer that excludes evaluator runtime."""

    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._condition = threading.Condition(threading.RLock())
        self.started_at: float | None = None
        self.timeout_seconds: float | None = None
        self.total_paused = 0.0
        self.pause_started_at: float | None = None
        self.active_evals = 0
        self.frozen_elapsed: float | None = None

    def start(self, timeout_seconds: float) -> dict[str, Any]:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        with self._condition:
            if self.started_at is not None:
                raise RuntimeError("timer has already started")
            self.started_at = self._clock()
            self.timeout_seconds = float(timeout_seconds)
            self._condition.notify_all()
            return self._snapshot_locked()

    def begin_evaluation(self) -> None:
        with self._condition:
            self.active_evals += 1
            if self.active_evals == 1:
                self.pause_started_at = self._clock()
            self._condition.notify_all()

    def end_evaluation(self) -> None:
        with self._condition:
            if self.active_evals <= 0:
                raise RuntimeError("evaluation pause is not active")
            self.active_evals -= 1
            if self.active_evals == 0 and self.pause_started_at is not None:
                self.total_paused += self._clock() - self.pause_started_at
                self.pause_started_at = None
            self._condition.notify_all()

    def _effective_elapsed_locked(self, now: float | None = None) -> float:
        if self.frozen_elapsed is not None:
            return self.frozen_elapsed
        if self.started_at is None:
            return 0.0
        current = self._clock() if now is None else now
        paused = self.total_paused
        if self.pause_started_at is not None:
            paused += current - self.pause_started_at
        return max(0.0, current - self.started_at - paused)

    def _total_paused_locked(self, now: float | None = None) -> float:
        current = self._clock() if now is None else now
        paused = self.total_paused
        if self.pause_started_at is not None:
            paused += current - self.pause_started_at
        return max(0.0, paused)

    @staticmethod
    def _rounded(value: float | None) -> float | None:
        return round(value, 3) if value is not None else None

    def _snapshot_locked(self) -> dict[str, Any]:
        now = self._clock()
        elapsed = self._effective_elapsed_locked(now)
        remaining = (
            max(0.0, self.timeout_seconds - elapsed)
            if self.timeout_seconds is not None
            else None
        )
        return {
            "elapsed_seconds": self._rounded(elapsed),
            "remaining_seconds": self._rounded(remaining),
            "timeout_seconds": self._rounded(self.timeout_seconds),
            "is_paused": self.active_evals > 0,
            "total_paused_seconds": self._rounded(
                self._total_paused_locked(now)
            ),
            "is_started": self.started_at is not None,
            "is_stopped": self.frozen_elapsed is not None,
        }

    def snapshot(self) -> dict[str, Any]:
        with self._condition:
            return self._snapshot_locked()

    def stop(self) -> dict[str, Any]:
        with self._condition:
            if self.started_at is None:
                raise RuntimeError("timer has not started")
            changed = self.frozen_elapsed is None
            if changed:
                self.frozen_elapsed = self._effective_elapsed_locked()
            self._condition.notify_all()
            return {"changed": changed, **self._snapshot_locked()}

    def wait_expired(self) -> dict[str, Any]:
        """Block until effective time expires, then atomically freeze it."""
        with self._condition:
            while self.started_at is None:
                self._condition.wait()
            while self.frozen_elapsed is None:
                if self.timeout_seconds is None:
                    self._condition.wait()
                    continue
                remaining = self.timeout_seconds - self._effective_elapsed_locked()
                if remaining <= 0:
                    self.frozen_elapsed = self.timeout_seconds
                    self._condition.notify_all()
                    break
                self._condition.wait(timeout=remaining)
            return {"expired": True, **self._snapshot_locked()}
