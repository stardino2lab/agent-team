"""Escalation derivation (S14c).

Pure, read-time projection over the S14a health snapshot + the task board — no
polling, no new stored state. Three rungs:
  teammate — a member is dead or stale (S14a health).
  task     — an in_progress task whose assignee is dead/stale (work is stuck).
  user     — a spawn that exhausted its retries (S14b) and cannot self-resolve.
The lead already sees the teammate/user signals on the event bus (S14b emits a
terminal `error` on retry exhaustion); this surfaces the full set in
`agent-team status` for a human/Hermes to act on.
"""

from __future__ import annotations

from dataclasses import dataclass

from agent_team.health import SessionHealth
from agent_team.tasks import Task

EscalationLevel = str  # "teammate" | "task" | "user"


@dataclass
class Escalation:
    level: EscalationLevel
    subject: str  # member name, task id, or request id
    reason: str


def derive_escalations(health: SessionHealth, tasks: list[Task]) -> list[Escalation]:
    out: list[Escalation] = []
    unhealthy: dict[str, str] = {
        m.name: m.health for m in health.members if m.health in ("dead", "stale")
    }

    for name, state in unhealthy.items():
        out.append(Escalation(level="teammate", subject=name, reason=f"member {state}"))

    for task in tasks:
        if task.state == "in_progress" and task.assignee in unhealthy:
            out.append(
                Escalation(
                    level="task",
                    subject=task.id,
                    reason=f"in_progress; assignee {task.assignee} {unhealthy[task.assignee]}",
                )
            )

    for se in health.spawn_errors:
        out.append(
            Escalation(
                level="user",
                subject=se.request_id or "?",
                reason=f"spawn failed and exhausted retries ({se.kind})",
            )
        )

    return out
