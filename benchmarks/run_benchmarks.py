"""Benchmark harness for determinism, success rate, and cost tracking.

By default this script runs a reproducible simulator so community members can
re-run the same benchmark without needing private infra.
"""

from __future__ import annotations

import argparse
import json
import random
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parent


@dataclass(slots=True)
class ScenarioResult:
    scenario_id: str
    run_index: int
    success: bool
    latency_ms: float
    cost_usd: float
    prompt_tokens: int
    completion_tokens: int
    recovered_from_failure: bool


def load_scenarios(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def simulate_run(scenario: dict, run_index: int, seed: int) -> ScenarioResult:
    # deterministic pseudo-simulator for reproducible baselines
    rng = random.Random(f"{seed}:{scenario['id']}:{run_index}")
    transient_failure = scenario["name"] in {"retry_after_tool_failure", "degraded_fallback"}
    recovered = transient_failure and rng.random() < 0.9
    base_success = 0.95 if scenario["expected_success"] else 0.05
    success = recovered or (rng.random() < base_success)

    latency_ms = round(rng.uniform(450, 2400), 2)
    prompt_tokens = rng.randint(400, 2200)
    completion_tokens = rng.randint(120, 700)
    cost_usd = round((prompt_tokens * 0.0000015) + (completion_tokens * 0.000002), 5)

    return ScenarioResult(
        scenario_id=scenario["id"],
        run_index=run_index,
        success=success,
        latency_ms=latency_ms,
        cost_usd=cost_usd,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        recovered_from_failure=recovered,
    )


def evaluate(results: list[ScenarioResult]) -> dict:
    total = len(results)
    successes = sum(int(r.success) for r in results)
    deterministic_hash = hash(tuple((r.scenario_id, r.run_index, r.success) for r in results))
    recovery_cases = [r for r in results if r.scenario_id in {"wf-04", "wf-05"}]

    return {
        "total_runs": total,
        "task_completion_rate": round(successes / total, 4) if total else 0,
        "mean_latency_ms": round(mean(r.latency_ms for r in results), 2) if results else 0,
        "mean_cost_usd": round(mean(r.cost_usd for r in results), 5) if results else 0,
        "mean_tokens": round(mean(r.prompt_tokens + r.completion_tokens for r in results), 2) if results else 0,
        "determinism_signature": deterministic_hash,
        "tool_failure_resilience": round(
            sum(int(r.recovered_from_failure) for r in recovery_cases) / len(recovery_cases), 4
        )
        if recovery_cases
        else 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario-file", type=Path, default=ROOT / "scenarios.json")
    parser.add_argument("--runs-per-scenario", type=int, default=20)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--output", type=Path, default=ROOT / "baseline_results.json")
    args = parser.parse_args()

    scenarios = load_scenarios(args.scenario_file)
    results: list[ScenarioResult] = []

    for scenario in scenarios:
        for run_idx in range(args.runs_per_scenario):
            results.append(simulate_run(scenario, run_idx, args.seed))

    summary = evaluate(results)
    detailed_results = [asdict(r) for r in results]
    payload = {"summary": summary, "runs_per_scenario": args.runs_per_scenario, "results": detailed_results}
    args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(json.dumps(summary, indent=2))
    print(f"Saved full benchmark report to: {args.output}")


if __name__ == "__main__":
    main()
