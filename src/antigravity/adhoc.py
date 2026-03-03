"""Ad-hoc orchestration runtime built from existing Antigravity primitives.

This module turns Markdown templates into a runnable workflow that can be used
immediately from scripts or CLI:

1) Load a template from ``templates/gallery.py``
2) Render variables
3) Extract actionable checklist steps
4) Gate each step with ``PolicyEngine``
5) Persist execution records into ``MemoryBackend``
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import re
from typing import Any

from antigravity.memory import InMemoryBackend, MemoryBackend
from antigravity.policy import Effect, PolicyDecision, PolicyEngine, create_default_engine

import sys
from pathlib import Path

try:
    from templates.gallery import get_gallery
except ModuleNotFoundError:  # pragma: no cover - fallback for editable/import-path edge cases
    repo_root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(repo_root))
    from templates.gallery import get_gallery


@dataclass(frozen=True)
class AdHocStep:
    """Single action extracted from a Markdown workflow template."""

    id: str
    title: str
    action_type: str


@dataclass(frozen=True)
class StepResult:
    """Policy + execution outcome for one step."""

    step: AdHocStep
    decision: PolicyDecision
    status: str
    detail: str


@dataclass(frozen=True)
class RunSummary:
    """High-level execution summary."""

    workflow_slug: str
    namespace: str
    total_steps: int
    allowed: int
    denied: int
    needs_approval: int


class AdHocOrchestrator:
    """Run markdown templates as practical ad-hoc agent workflows."""

    def __init__(
        self,
        policy_engine: PolicyEngine | None = None,
        memory: MemoryBackend | None = None,
    ) -> None:
        self.policy_engine = policy_engine or create_default_engine()
        self.memory = memory or InMemoryBackend()

    def run_template(
        self,
        slug: str,
        *,
        namespace: str,
        variables: dict[str, str] | None = None,
        base_context: dict[str, Any] | None = None,
    ) -> tuple[RunSummary, list[StepResult]]:
        """Execute one template and persist full history to memory."""
        template = get_gallery().get(slug)
        rendered = template.render(variables or {})
        steps = parse_markdown_steps(rendered)

        results: list[StepResult] = []
        for step in steps:
            context = {
                "workflow": slug,
                "step_id": step.id,
                "step_title": step.title,
                "action_type": step.action_type,
                **(base_context or {}),
            }
            decision = self.policy_engine.evaluate(context)
            result = StepResult(
                step=step,
                decision=decision,
                status=_status_for(decision.effect),
                detail=_detail_for(step, decision),
            )
            results.append(result)
            self.memory.set(namespace, f"step:{step.id}", _serialize_result(result))

        summary = RunSummary(
            workflow_slug=slug,
            namespace=namespace,
            total_steps=len(results),
            allowed=sum(1 for r in results if r.status == "executed"),
            denied=sum(1 for r in results if r.status == "blocked"),
            needs_approval=sum(1 for r in results if r.status == "needs_approval"),
        )
        self.memory.set(namespace, "summary", _serialize_summary(summary))
        return summary, results


def parse_markdown_steps(markdown: str) -> list[AdHocStep]:
    """Extract checklist items (``- [ ]``/``- [x]``) as executable steps."""
    steps: list[AdHocStep] = []
    index = 1
    in_workflow_section = False
    for raw_line in markdown.splitlines():
        line = raw_line.strip()
        if line.startswith("##"):
            heading = line.lstrip("#").strip().lower()
            in_workflow_section = heading.startswith("workflow")
            continue
        if not in_workflow_section:
            continue

        title = ""

        if line.startswith("- ["):
            try:
                _, remainder = line.split("]", maxsplit=1)
            except ValueError:
                continue
            title = remainder.strip().lstrip("-").strip()
        else:
            numbered = re.match(r"^(?:\d+[.)]|[-*])\s+(?P<title>.+)$", line)
            if numbered:
                title = numbered.group("title").strip()

        if not title:
            continue
        steps.append(
            AdHocStep(
                id=f"{index:02d}",
                title=title,
                action_type=infer_action_type(title),
            )
        )
        index += 1
    return steps


def infer_action_type(step_title: str) -> str:
    """Map human step text to coarse policy action types."""
    text = step_title.lower()
    if any(token in text for token in ("delete", "remove", "drop", "purge")):
        return "delete"
    if any(token in text for token in ("external", "public", "vendor", "partner")):
        return "send_external"
    if any(token in text for token in ("write", "update", "notify", "sync", "post")):
        return "write"
    return "read"


def _status_for(effect: Effect) -> str:
    if effect == Effect.DENY:
        return "blocked"
    if effect == Effect.REQUIRE_APPROVAL:
        return "needs_approval"
    return "executed"


def _detail_for(step: AdHocStep, decision: PolicyDecision) -> str:
    if decision.effect == Effect.ALLOW:
        return f"Executed: {step.title}"
    if decision.effect == Effect.REQUIRE_APPROVAL:
        return f"Paused for approval: {decision.reason or step.title}"
    return f"Blocked: {decision.reason or step.title}"


def _serialize_result(result: StepResult) -> dict[str, Any]:
    return {
        "step": {
            "id": result.step.id,
            "title": result.step.title,
            "action_type": result.step.action_type,
        },
        "decision": {
            "effect": result.decision.effect.value,
            "matched_rule_id": result.decision.matched_rule_id,
            "reason": result.decision.reason,
        },
        "status": result.status,
        "detail": result.detail,
        "recorded_at": datetime.now(tz=timezone.utc).isoformat(),
    }


def _serialize_summary(summary: RunSummary) -> dict[str, Any]:
    return {
        "workflow_slug": summary.workflow_slug,
        "namespace": summary.namespace,
        "total_steps": summary.total_steps,
        "allowed": summary.allowed,
        "denied": summary.denied,
        "needs_approval": summary.needs_approval,
        "recorded_at": datetime.now(tz=timezone.utc).isoformat(),
    }
