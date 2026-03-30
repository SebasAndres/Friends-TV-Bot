"""AI provider client implementations."""

from __future__ import annotations

import time
from functools import wraps
from logging import getLogger
from typing import Callable, TypeVar

logger = getLogger(__name__)
F = TypeVar("F", bound=Callable)

_TRANSIENT_ERRORS = (ConnectionError, TimeoutError, OSError)


def retry_on_transient(
    max_retries: int = 2,
    delay: float = 2.0,
) -> Callable[[F], F]:
    """Decorator that retries a function on transient network errors."""
    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args, **kwargs):  # type: ignore[no-untyped-def]
            last_exc: Exception | None = None
            for attempt in range(1 + max_retries):
                try:
                    return func(*args, **kwargs)
                except _TRANSIENT_ERRORS as exc:
                    last_exc = exc
                    if attempt < max_retries:
                        logger.warning(
                            "%s failed (attempt %d/%d): %s — retrying in %.1fs",
                            func.__qualname__, attempt + 1, 1 + max_retries, exc, delay,
                        )
                        time.sleep(delay)
                    else:
                        logger.error(
                            "%s failed after %d attempts: %s",
                            func.__qualname__, 1 + max_retries, exc,
                        )
            raise last_exc  # type: ignore[misc]
        return wrapper  # type: ignore[return-value]
    return decorator
