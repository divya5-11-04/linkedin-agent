"""Minimal retry-with-backoff helper for network calls.

No external dependency, deliberately small: this project makes at most
a handful of API calls per run, so a simple linear-backoff loop is enough.
"""

import time


def with_retries(fn, *, attempts: int = 3, base_delay: float = 2.0, on_retry=None):
    """Call fn() up to `attempts` times, backing off linearly between tries.

    fn should raise on failure (e.g. via requests' raise_for_status()).
    Re-raises the last exception if all attempts fail.
    """
    last_exc = None
    for attempt in range(1, attempts + 1):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001 - intentionally broad, this wraps arbitrary network calls
            last_exc = exc
            if attempt == attempts:
                break
            delay = base_delay * attempt
            if on_retry:
                on_retry(attempt, exc, delay)
            time.sleep(delay)
    raise last_exc
