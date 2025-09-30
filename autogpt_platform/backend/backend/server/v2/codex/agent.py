"""Agent client abstractions used by the Codex orchestration service."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from backend.server.training_loop import AgentRunResult


class AgentClient(Protocol):
    """Protocol that represents the minimal agent operations we rely on."""

    @property
    def repo_path(self) -> str | None:  # pragma: no cover - simple delegation
        """Return the repository path associated with the agent, if any."""

    def run_task(self, goal: str, repo_path: str | None = None) -> AgentRunResult:
        """Execute a task and return the resulting metadata."""

    def commit(self, message: str) -> None:
        """Persist repository changes with the provided commit message."""


@dataclass(slots=True)
class RecordingAgentClient:
    """In-memory agent client that records invocations for testing."""

    repo_path: str | None = None
    responses: list[AgentRunResult] = field(default_factory=list)
    commits: list[str] = field(default_factory=list)
    _run_calls: list[str] = field(default_factory=list)

    def run_task(self, goal: str, repo_path: str | None = None) -> AgentRunResult:
        self._run_calls.append(goal)
        if self.responses:
            return self.responses.pop(0)
        return AgentRunResult(summary=f"No-op for {goal}")

    def commit(self, message: str) -> None:
        self.commits.append(message)

    @property
    def run_calls(self) -> list[str]:  # pragma: no cover - trivial accessor
        return list(self._run_calls)


@dataclass(slots=True)
class NoOpAgentClient:
    """Agent client that reports success without producing side effects."""

    repo_path: str | None = None

    def run_task(self, goal: str, repo_path: str | None = None) -> AgentRunResult:
        return AgentRunResult(summary=f"Completed: {goal}")

    def commit(self, message: str) -> None:  # pragma: no cover - intentionally raises
        msg = "commit support is not configured for the no-op agent"
        raise RuntimeError(msg)
