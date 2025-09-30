"""Utilities for running recursive training loops indefinitely.

The helper exposed here allows the platform to continuously iterate across
combinations of layers and features, executing a provided agent callback for
each pair.  The default ``train_forever`` entry point intentionally never
returns so that operators can start it as a long running background process.

Tests rely on ``train_for_cycles`` which performs a finite number of cycles.
"""

from __future__ import annotations

import itertools
import logging
import time
from dataclasses import dataclass, field
from typing import Callable, Iterable, Sequence

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class AgentRunResult:
    """Result returned by an agent run."""

    modified: bool = False
    summary: str | None = None
    details: dict[str, object] | None = None


@dataclass(slots=True)
class TrainingRecord:
    """Represents a single training attempt for a layer/feature pair."""

    layer: str
    feature: str
    goal: str
    success: bool
    summary: str | None
    error: Exception | None = None
    timestamp: float = field(default_factory=time.time)


class RecursiveTrainer:
    """Run recursive training loops for every layer/feature combination."""

    def __init__(
        self,
        layers: Sequence[str],
        features: Sequence[str],
        run_task: Callable[[str, str | None], AgentRunResult],
        *,
        repo_path: str | None = None,
        commit: Callable[[str], None] | None = None,
        sleep_seconds: float = 0.0,
    ) -> None:
        if not layers:
            raise ValueError("layers must not be empty")
        if not features:
            raise ValueError("features must not be empty")

        self._layers = tuple(layers)
        self._features = tuple(features)
        self._run_task = run_task
        self._repo_path = repo_path
        self._commit = commit
        self._sleep_seconds = sleep_seconds
        self._history: list[TrainingRecord] = []

    @property
    def history(self) -> Sequence[TrainingRecord]:
        return tuple(self._history)

    @property
    def layers(self) -> Sequence[str]:
        return self._layers

    @property
    def features(self) -> Sequence[str]:
        return self._features

    def train_forever(self) -> None:
        """Continuously run training cycles until interrupted."""

        logger.info(
            "Starting infinite training loop across %d layers and %d features",
            len(self._layers),
            len(self._features),
        )
        try:
            while True:
                self._run_cycle()
        except KeyboardInterrupt:
            logger.info("Training interrupted by operator; exiting loop.")

    def train_for_cycles(self, cycles: int) -> None:
        """Run a finite number of training cycles (used for tests)."""

        if cycles < 0:
            raise ValueError("cycles must be non-negative")
        for _ in range(cycles):
            self._run_cycle()

    def _run_cycle(self) -> None:
        for layer, feature in itertools.product(self._layers, self._features):
            goal = (
                f"Improve {layer} for {feature} in codebase"
                if not self._repo_path
                else f"Improve {layer} for {feature} in codebase at {self._repo_path}."
            )
            logger.debug("Running agent for goal: %s", goal)
            start_time = time.time()
            try:
                result = self._run_task(goal, self._repo_path)
            except Exception as exc:  # noqa: BLE001
                logger.exception("Agent execution failed for %s/%s", layer, feature)
                self._history.append(
                    TrainingRecord(
                        layer=layer,
                        feature=feature,
                        goal=goal,
                        success=False,
                        summary=None,
                        error=exc,
                        timestamp=start_time,
                    )
                )
                continue

            summary = result.summary if isinstance(result, AgentRunResult) else None
            modified = bool(result.modified) if isinstance(result, AgentRunResult) else False

            self._history.append(
                TrainingRecord(
                    layer=layer,
                    feature=feature,
                    goal=goal,
                    success=True,
                    summary=summary,
                    error=None,
                    timestamp=start_time,
                )
            )

            if modified and self._commit:
                commit_message = f"chore(training): sync {layer} {feature} updates"
                logger.debug("Auto-committing changes with message: %s", commit_message)
                try:
                    self._commit(commit_message)
                except Exception:  # noqa: BLE001
                    logger.exception("Failed to commit changes after %s/%s run", layer, feature)

            if self._sleep_seconds > 0:
                time.sleep(self._sleep_seconds)


def train_infinitely(
    *,
    layers: Iterable[str],
    features: Iterable[str],
    run_task: Callable[[str, str | None], AgentRunResult],
    repo_path: str | None = None,
    commit: Callable[[str], None] | None = None,
    sleep_seconds: float = 0.0,
) -> None:
    """Helper to construct a trainer and run it indefinitely."""

    trainer = RecursiveTrainer(
        tuple(layers),
        tuple(features),
        run_task,
        repo_path=repo_path,
        commit=commit,
        sleep_seconds=sleep_seconds,
    )
    trainer.train_forever()
