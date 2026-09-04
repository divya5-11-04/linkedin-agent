import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from retry import with_retries


def test_succeeds_first_try_no_retry_needed():
    calls = []

    def fn():
        calls.append(1)
        return "ok"

    result = with_retries(fn, attempts=3, base_delay=0)
    assert result == "ok"
    assert len(calls) == 1


def test_succeeds_after_transient_failures():
    calls = []

    def fn():
        calls.append(1)
        if len(calls) < 3:
            raise ConnectionError("transient")
        return "recovered"

    result = with_retries(fn, attempts=3, base_delay=0)
    assert result == "recovered"
    assert len(calls) == 3


def test_raises_last_exception_after_exhausting_attempts():
    calls = []

    def fn():
        calls.append(1)
        raise ConnectionError("still down")

    with pytest.raises(ConnectionError):
        with_retries(fn, attempts=3, base_delay=0)
    assert len(calls) == 3


def test_on_retry_callback_invoked_with_attempt_and_delay():
    seen = []

    def fn():
        if not seen:
            seen.append("first")
            raise ValueError("boom")
        return "done"

    retry_log = []
    with_retries(
        fn,
        attempts=2,
        base_delay=0,
        on_retry=lambda attempt, exc, delay: retry_log.append((attempt, str(exc))),
    )
    assert retry_log == [(1, "boom")]
