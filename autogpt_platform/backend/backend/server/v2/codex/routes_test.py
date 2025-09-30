"""Tests for the Codex orchestration API routes."""

from __future__ import annotations

import fastapi
import pytest
from fastapi.testclient import TestClient

from backend.server.training_loop import AgentRunResult

from .agent import RecordingAgentClient
from .routes import get_service, router
from .service import CodexOrchestrationService


@pytest.fixture(scope="session")
async def server():
    """Stub the global server fixture required by unrelated integration suites."""

    yield None


@pytest.fixture(scope="session", autouse=True)
def graph_cleanup():
    """Prevent database access in isolated API unit tests."""

    yield


@pytest.fixture()
def app(recording_agent: RecordingAgentClient) -> fastapi.FastAPI:
    application = fastapi.FastAPI()
    application.include_router(router)

    service = CodexOrchestrationService(
        layers=("book",),
        features=("measurement",),
        agent=recording_agent,
    )

    def _service_override() -> CodexOrchestrationService:
        return service

    application.dependency_overrides[get_service] = _service_override
    return application


@pytest.fixture()
def recording_agent() -> RecordingAgentClient:
    responses = [
        AgentRunResult(modified=True, summary="updated"),
        AgentRunResult(summary="steady"),
    ]
    return RecordingAgentClient(repo_path="/repo", responses=responses)


@pytest.fixture()
def client(app: fastapi.FastAPI) -> TestClient:
    return TestClient(app)


def test_run_task_endpoint_returns_record(client: TestClient) -> None:
    response = client.post(
        "/codex/run-task",
        json={"layer": "book", "feature": "measurement", "goal": "Custom"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["record"]["goal"] == "Custom"
    assert payload["record"]["summary"] == "updated"


def test_train_all_endpoint_runs_cycle(client: TestClient) -> None:
    response = client.post("/codex/train-all", json={"cycles": 1})

    assert response.status_code == 200
    payload = response.json()
    assert payload["cycles"] == 1
    assert len(payload["records"]) == 1


def test_log_and_status_endpoints(client: TestClient) -> None:
    client.post("/codex/run-task", json={"layer": "book", "feature": "measurement"})

    log_response = client.get("/codex/log")
    status_response = client.get("/codex/status")

    assert log_response.status_code == 200
    assert status_response.status_code == 200

    log_payload = log_response.json()
    status_payload = status_response.json()

    assert log_payload["history"]
    assert status_payload["total_runs"] == len(log_payload["history"])
    assert status_payload["repo_path"] == "/repo"


def test_sync_repo_endpoint_uses_agent(
    client: TestClient, recording_agent: RecordingAgentClient
) -> None:
    response = client.post("/codex/sync-repo", json={"message": "sync"})

    assert response.status_code == 200
    assert recording_agent.commits == ["sync"]
