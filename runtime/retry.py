"""Retry policy and backoff helpers for runtime and tool execution."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from random import uniform
from typing import Callable, TypeVar


class ErrorType(str, Enum):
    TOOL_TIMEOUT = "tool_timeout"
    VALIDATION_FAIL = "validation_fail"
    TRANSIENT = "transient"


@dataclass(frozen=True, slots=True)
class RetryProfile:
    max_attempts: int
    base_delay_seconds: float
    multiplier: float = 2.0
    max_delay_seconds: float = 30.0
    jitter: float = 0.1

    def delay_for(self, attempt: int) -> float:
        raw = min(self.base_delay_seconds * (self.multiplier ** max(attempt - 1, 0)), self.max_delay_seconds)
        return max(0.0, raw + uniform(-self.jitter, self.jitter) * raw)


DEFAULT_PROFILES: dict[ErrorType, RetryProfile] = {
    ErrorType.TOOL_TIMEOUT: RetryProfile(max_attempts=4, base_delay_seconds=1.0, multiplier=2.0),
    ErrorType.VALIDATION_FAIL: RetryProfile(max_attempts=2, base_delay_seconds=0.2, multiplier=1.0),
    ErrorType.TRANSIENT: RetryProfile(max_attempts=5, base_delay_seconds=0.5, multiplier=1.8),
}


T = TypeVar("T")


def should_retry(error_type: ErrorType, attempt: int, *, profiles: dict[ErrorType, RetryProfile] | None = None) -> bool:
    profile = (profiles or DEFAULT_PROFILES)[error_type]
    return attempt < profile.max_attempts


def next_backoff(error_type: ErrorType, attempt: int, *, profiles: dict[ErrorType, RetryProfile] | None = None) -> float:
    profile = (profiles or DEFAULT_PROFILES)[error_type]
    return profile.delay_for(attempt)


def with_retry(
    fn: Callable[[], T],
    *,
    error_type: ErrorType,
    sleep_fn: Callable[[float], None],
    profiles: dict[ErrorType, RetryProfile] | None = None,
) -> T:
    """Execute callback with retry/backoff logic for a classified error type."""

    profile_map = profiles or DEFAULT_PROFILES
    attempt = 1
    while True:
        try:
            return fn()
        except Exception:
            if not should_retry(error_type, attempt, profiles=profile_map):
                raise
            sleep_fn(next_backoff(error_type, attempt, profiles=profile_map))
            attempt += 1
