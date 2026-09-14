"""Request feed: the only path by which requests reach the simulation.

The feed releases a request only once the clock has reached its ``time``. The
scheduler never holds a reference to the feed, so "no peek-ahead" (A16) is a
property of the structure, not of discipline.
"""

from __future__ import annotations

from collections.abc import Iterable

from .model import Request


class RequestFeed:
    def __init__(self, requests: Iterable[Request]) -> None:
        # Stable sort: file order is preserved within a tick (A14).
        self._pending: list[Request] = sorted(requests, key=lambda r: r.time)
        self._cursor = 0

    @property
    def exhausted(self) -> bool:
        return self._cursor >= len(self._pending)

    @property
    def next_time(self) -> int | None:
        """Time of the next unreleased request, or ``None``. Used only to know when to stop."""
        return None if self.exhausted else self._pending[self._cursor].time

    def release(self, now: int) -> list[Request]:
        """Return every request with ``time <= now`` that has not been released yet."""
        released: list[Request] = []
        while not self.exhausted and self._pending[self._cursor].time <= now:
            released.append(self._pending[self._cursor])
            self._cursor += 1
        return released
