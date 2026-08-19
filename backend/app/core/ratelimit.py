from __future__ import annotations

import threading
import time
from abc import ABC, abstractmethod
from collections import OrderedDict
from dataclasses import dataclass

DEFAULT_MAX_TRACKED_CLIENTS = 50_000


class RateLimiter(ABC):
    @abstractmethod
    def allow(self, key: str) -> bool: ...


@dataclass
class _Bucket:
    tokens: float
    last_refilled_at: float


class InProcessTokenBucketRateLimiter(RateLimiter):
    """Token bucket held in this process's memory only.

    A multi-process or multi-instance deployment needs a shared store for this
    to be a real limit rather than a per-worker one. Replacing this
    implementation is a production-hardening concern; the interface is what
    callers depend on.
    """

    def __init__(
        self,
        *,
        rate_per_minute: int,
        burst: int,
        max_tracked_clients: int = DEFAULT_MAX_TRACKED_CLIENTS,
        clock=time.monotonic,
    ) -> None:
        if rate_per_minute <= 0 or burst <= 0:
            raise ValueError("rate_per_minute and burst must both be positive")
        self._refill_per_second = rate_per_minute / 60.0
        self._capacity = float(burst)
        self._max_tracked_clients = max_tracked_clients
        self._clock = clock
        self._buckets: OrderedDict[str, _Bucket] = OrderedDict()
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = self._clock()
        with self._lock:
            bucket = self._buckets.get(key)
            if bucket is None:
                bucket = _Bucket(tokens=self._capacity, last_refilled_at=now)
                self._buckets[key] = bucket
                while len(self._buckets) > self._max_tracked_clients:
                    self._buckets.popitem(last=False)
            else:
                self._buckets.move_to_end(key)
                elapsed = max(0.0, now - bucket.last_refilled_at)
                bucket.tokens = min(
                    self._capacity, bucket.tokens + elapsed * self._refill_per_second
                )
                bucket.last_refilled_at = now

            if bucket.tokens < 1.0:
                return False
            bucket.tokens -= 1.0
            return True


class AllowAllRateLimiter(RateLimiter):
    def allow(self, key: str) -> bool:
        return True
