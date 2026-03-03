"""Metric utilities for benchmark and runtime observability."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class MetricSnapshot:
    """Aggregated metrics for orchestrator runs."""

    total_runs: int = 0
    successful_runs: int = 0
    total_latency_ms: float = 0.0
    total_cost_usd: float = 0.0
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    latencies_ms: list[float] = field(default_factory=list)

    def record_run(
        self,
        *,
        latency_ms: float,
        success: bool,
        cost_usd: float,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> None:
        """Record one workflow execution."""
        self.total_runs += 1
        self.successful_runs += int(success)
        self.total_latency_ms += latency_ms
        self.total_cost_usd += cost_usd
        self.total_prompt_tokens += prompt_tokens
        self.total_completion_tokens += completion_tokens
        self.latencies_ms.append(latency_ms)

    @property
    def mean_latency_ms(self) -> float:
        return self.total_latency_ms / self.total_runs if self.total_runs else 0.0

    @property
    def success_rate(self) -> float:
        return self.successful_runs / self.total_runs if self.total_runs else 0.0

    @property
    def total_tokens(self) -> int:
        return self.total_prompt_tokens + self.total_completion_tokens


class MetricsCollector:
    """Simple façade around MetricSnapshot for service-level composition."""

    def __init__(self) -> None:
        self._snapshot = MetricSnapshot()

    def observe(
        self,
        *,
        latency_ms: float,
        success: bool,
        cost_usd: float = 0.0,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
    ) -> None:
        self._snapshot.record_run(
            latency_ms=latency_ms,
            success=success,
            cost_usd=cost_usd,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )

    def snapshot(self) -> MetricSnapshot:
        """Return current metric snapshot."""
        return self._snapshot
