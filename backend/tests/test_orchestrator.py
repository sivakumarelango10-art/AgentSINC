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
    with pytest.raises(RuntimeError, match="between 1 and 5"):
        _validate_plan({"summary": "No tasks", "tasks": []})
    too_many = {
        "summary": "Too much work",
        "tasks": [
            {
                "agent_id": "researcher",
                "title": f"Research task number {index}",
                "instructions": "Inspect the relevant source files and provide evidence-backed findings.",
            }
            for index in range(6)
        ],
    }
    with pytest.raises(RuntimeError, match="between 1 and 5"):
        _validate_plan(too_many)



def test_github_release_request_is_ordered_developer_then_qa_then_developer() -> None:
    from app.orchestrator import _apply_github_release_sequence

    plan = {
        "summary": "Implement the requested change.",
        "tasks": [
            {
                "agent_id": "developer",
                "title": "Implement the change",
                "instructions": "Inspect and update the actual source files.",
            },
            {
                "agent_id": "designer",
                "title": "Review the UI",
                "instructions": "Review the actual interface and propose design improvements.",
            },
        ],
    }
    request = {
        "title": "Implement and push the fix to GitHub",
        "instructions": "Write the code, run QA, push the changes to GitHub and open a pull request.",
    }

    ordered = _apply_github_release_sequence(plan, request)
    assert [item["agent_id"] for item in ordered["tasks"]] == [
        "developer", "designer", "tester", "developer"
    ]
    assert "PIPELINE STAGE 1/3" in ordered["tasks"][0]["instructions"]
    assert "PIPELINE STAGE 2/3" in ordered["tasks"][2]["instructions"]
    assert "PIPELINE STAGE 3/3" in ordered["tasks"][3]["instructions"]


def test_github_release_sequence_is_not_added_to_read_only_research() -> None:
    from app.orchestrator import _apply_github_release_sequence

    plan = {"summary": "Research", "tasks": [{
        "agent_id": "researcher",
        "title": "Research GitHub Actions",
        "instructions": "Research official GitHub Actions documentation and report sources.",
    }]}
    result = _apply_github_release_sequence(plan, {
        "title": "Research GitHub Actions",
        "instructions": "Find official documentation about GitHub Actions.",
    })
    assert result["tasks"] == plan["tasks"]
