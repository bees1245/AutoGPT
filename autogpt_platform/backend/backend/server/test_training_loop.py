from __future__ import annotations

from collections import deque
from typing import Callable

import pytest

from backend.server.training_loop import AgentRunResult, RecursiveTrainer


def _build_runner(history: deque[tuple[str, str | None]], *, modified: bool = False) -> Callable[[str, str | None], AgentRunResult]:
    def _runner(goal: str, repo_path: str | None) -> AgentRunResult:
        history.append((goal, repo_path))
        return AgentRunResult(modified=modified, summary=f"Completed {goal}")

    return _runner


def test_train_for_cycles_runs_every_combination():
    layers = ("book", "cubit")
    features = ("measurement", "action")
    calls: deque[tuple[str, str | None]] = deque()
    trainer = RecursiveTrainer(layers, features, _build_runner(calls), repo_path="/repo")

    trainer.train_for_cycles(1)

    assert len(calls) == len(layers) * len(features)
    goals = [call[0] for call in calls]
    assert goals[0].startswith("Improve book for measurement")
    assert goals[-1].startswith("Improve cubit for action")
    assert all(call[1] == "/repo" for call in calls)


def test_train_for_cycles_raises_on_negative_cycles():
    trainer = RecursiveTrainer(("layer",), ("feature",), _build_runner(deque()))

    with pytest.raises(ValueError):
        trainer.train_for_cycles(-1)


def test_train_cycle_records_failures_and_continues():
    calls: deque[tuple[str, str | None]] = deque()

    def failing_runner(goal: str, repo_path: str | None) -> AgentRunResult:
        calls.append((goal, repo_path))
        if "cubit" in goal:
            raise RuntimeError("boom")
        return AgentRunResult(summary="ok")

    trainer = RecursiveTrainer(("book", "cubit"), ("measurement",), failing_runner)
    trainer.train_for_cycles(1)

    assert len(trainer.history) == 2
    first, second = trainer.history
    assert first.success is True
    assert second.success is False
    assert isinstance(second.error, RuntimeError)


def test_train_cycle_commits_when_modified():
    calls: deque[tuple[str, str | None]] = deque()
    commits: deque[str] = deque()

    def commit(message: str) -> None:
        commits.append(message)

    trainer = RecursiveTrainer(
        ("book",),
        ("measurement",),
        _build_runner(calls, modified=True),
        commit=commit,
    )

    trainer.train_for_cycles(1)

    assert commits
    assert commits[0] == "chore(training): sync book measurement updates"
