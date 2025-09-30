from __future__ import annotations

import pytest


from backend.server.training_loop import AgentRunResult

from .agent import RecordingAgentClient
from .service import CodexOrchestrationService


@pytest.fixture(scope="session")
async def server():
    """Override heavy backend fixtures required by unrelated tests."""

    yield None


@pytest.fixture(scope="session", autouse=True)
def graph_cleanup():
    """Disable database cleanup when exercising pure unit tests."""

    yield


@pytest.fixture()
def recording_agent() -> RecordingAgentClient:
    responses = [
        AgentRunResult(modified=True, summary="updated"),
        AgentRunResult(summary="steady"),
    ]
    return RecordingAgentClient(repo_path="/repo", responses=responses)


def test_run_task_records_history(recording_agent: RecordingAgentClient):
    service = CodexOrchestrationService(
        layers=("book",), features=("measurement",), agent=recording_agent
    )

    record = service.run_task("book", "measurement")

    assert record.summary == "updated"
    assert len(service.history) == 1
    assert recording_agent.commits == ["chore(training): sync book measurement updates"]


def test_train_all_runs_every_pair(recording_agent: RecordingAgentClient):
    service = CodexOrchestrationService(
        layers=("book", "cubit"), features=("measurement",), agent=recording_agent
    )

    records = service.train_all(1)

    assert len(records) == 2
    assert any(rec.summary == "updated" for rec in records)


def test_sync_repo_raises_without_commit_support():
    service = CodexOrchestrationService(layers=("book",), features=("measurement",))

    with pytest.raises(RuntimeError):
        service.sync_repo("message")
