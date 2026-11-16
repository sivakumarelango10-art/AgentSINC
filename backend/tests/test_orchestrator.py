from __future__ import annotations

import pytest

from app.orchestrator import _json_object, _validate_plan


def test_json_object_parses_plain_json_and_fenced_json() -> None:
    plain = '{"summary":"Plan","tasks":[]}'
    fenced = chr(96) * 3 + 'json\n{"summary":"Plan","tasks":[]}\n' + chr(96) * 3
    assert _json_object(plain)["summary"] == "Plan"
    assert _json_object(fenced)["summary"] == "Plan"


def test_ceo_plan_accepts_only_known_specialist_agents() -> None:
    plan = _validate_plan({
        "summary": "Research and review the request.",
        "tasks": [
            {
                "agent_id": "researcher",
                "title": "Research current implementation",
                "instructions": "Inspect relevant files and list evidence-backed findings and unknowns.",
            },
            {
                "agent_id": "tester",
                "title": "Prepare validation checklist",
                "instructions": "Review the proposed deliverables and prepare a clear manual validation checklist.",
            },
        ],
    })
    assert len(plan["tasks"]) == 2
    assert plan["tasks"][0]["agent_id"] == "researcher"


@pytest.mark.parametrize("agent_id", ["ceo", "admin", "unknown"])
def test_ceo_plan_rejects_non_specialist_delegation(agent_id: str) -> None:
    with pytest.raises(RuntimeError, match="only to Developer"):
        _validate_plan({
            "summary": "Plan",
            "tasks": [
                {
                    "agent_id": agent_id,
                    "title": "Prepare a specialist deliverable",
                    "instructions": "Inspect the request and provide an evidence-backed specialist deliverable.",
                }
            ],
        })


def test_ceo_plan_rejects_empty_or_excessive_task_lists() -> None:
    with pytest.raises(RuntimeError, match="between 1 and 4"):
        _validate_plan({"summary": "No tasks", "tasks": []})
    too_many = {
        "summary": "Too much work",
        "tasks": [
            {
                "agent_id": "researcher",
                "title": f"Research task number {index}",
                "instructions": "Inspect the relevant source files and provide evidence-backed findings.",
            }
            for index in range(5)
        ],
    }
    with pytest.raises(RuntimeError, match="between 1 and 4"):
        _validate_plan(too_many)
