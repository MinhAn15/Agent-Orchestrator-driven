"""Test skeleton for runtime retry policy."""

from antigravity.workflow import should_retry


def test_retry_policy_respects_max_retries() -> None:
    assert should_retry(attempt=1, max_retries=3)
    assert not should_retry(attempt=3, max_retries=3)
