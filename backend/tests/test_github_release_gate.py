from __future__ import annotations

from app.harness import AgentHarness


def _harness_with_events(events: list[dict]) -> AgentHarness:
    harness = AgentHarness(
        {"id": "release-task", "agent_id": "developer", "orchestration_id": "orchestration-1"},
        client=None,
        progress=lambda *_: None,
        cancelled=lambda: False,
    )
    harness._related_tool_events = lambda: events  # type: ignore[method-assign]
    return harness


def _qa_pass() -> dict:
    return {
        "agent_id": "tester",
        "task_id": "qa-task",
        "event_type": "tool_completed",
        "message": "tests.run: python-tests: PASSED; exit=0; 22 passed in 0.8s",
    }


def _push_completed(branch: str = "feat/verified-change") -> dict:
    return {
        "agent_id": "developer",
        "task_id": "release-task",
        "event_type": "tool_completed",
        "message": f"mcp.github.push_files: Pushed 3 file(s) to branch '{branch}'.",
    }


def test_github_push_is_blocked_without_a_persisted_qa_pass() -> None:
    harness = _harness_with_events([])
    error = harness._github_mutation_policy_error("push_files", {"branch": "feat/verified-change", "files": []})
    assert error is not None
    assert "QA Agent's successful test run" in error


def test_github_push_is_allowed_after_qa_only_on_feature_branches() -> None:
    harness = _harness_with_events([_qa_pass()])
    assert harness._github_mutation_policy_error(
        "push_files", {"branch": "feat/verified-change", "files": []}
    ) is None
    protected = harness._github_mutation_policy_error("push_files", {"branch": "main", "files": []})
    assert protected is not None
    assert "protected/default branch" in protected


def test_github_pr_requires_successful_push_on_matching_branch() -> None:
    harness = _harness_with_events([_qa_pass()])
    before_push = harness._github_mutation_policy_error(
        "create_pull_request",
        {"head": "owner/repo:feat/verified-change", "base": "main"},
    )
    assert before_push is not None
    assert "successful GitHub file push" in before_push

    harness._related_tool_events = lambda: [_qa_pass(), _push_completed()]  # type: ignore[method-assign]
    assert harness._latest_pushed_branch() == "feat/verified-change"
    assert harness._github_mutation_policy_error(
        "create_pull_request",
        {"head": "owner/repo:feat/verified-change", "base": "main"},
    ) is None


def test_pending_push_approval_does_not_count_as_a_completed_push() -> None:
    harness = _harness_with_events([
        _qa_pass(),
        {**_push_completed(), "event_type": "tool_awaiting_approval"},
    ])
    assert harness._latest_pushed_branch() is None
    assert harness._github_mutation_policy_error(
        "create_pull_request",
        {"head": "owner/repo:feat/verified-change", "base": "main"},
    ) is not None


def test_agents_cannot_merge_pull_requests() -> None:
    harness = _harness_with_events([_qa_pass(), _push_completed()])
    error = harness._github_mutation_policy_error("merge_pull_request", {"pull_number": 99})
    assert error is not None
    assert "founder must merge manually" in error
