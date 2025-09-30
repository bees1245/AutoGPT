"""Service layer that orchestrates recursive Codex training."""

from __future__ import annotations

import logging
from typing import Sequence

from backend.server.training_loop import RecursiveTrainer, TrainingRecord

from .agent import AgentClient, NoOpAgentClient

logger = logging.getLogger(__name__)


DEFAULT_LAYERS: tuple[str, ...] = (
    "book",
    "cubit",
    "gap",
    "quantum",
    "annotation",
    "coda",
)

DEFAULT_FEATURES: tuple[str, ...] = (
    "measurement",
    "action",
    "training",
    "logging",
    "api",
)


class CodexOrchestrationService:
    """High level service that coordinates recursive agent execution."""

    def __init__(
        self,
        *,
        layers: Sequence[str] = DEFAULT_LAYERS,
        features: Sequence[str] = DEFAULT_FEATURES,
        agent: AgentClient | None = None,
    ) -> None:
        self._agent = agent or NoOpAgentClient()
        self._trainer = RecursiveTrainer(
            tuple(layers),
            tuple(features),
            self._agent.run_task,
            repo_path=self._agent.repo_path,
            commit=self._agent.commit,
        )

    @property
    def layers(self) -> Sequence[str]:
        return self._trainer.layers

    @property
    def features(self) -> Sequence[str]:
        return self._trainer.features

    @property
    def repo_path(self) -> str | None:
        return self._trainer.repo_path

    @property
    def history(self) -> Sequence[TrainingRecord]:
        return self._trainer.history

    def run_task(
        self, layer: str, feature: str, goal: str | None = None
    ) -> TrainingRecord:
        logger.info("Executing manual Codex task for %s/%s", layer, feature)
        return self._trainer.run_once(layer, feature, goal=goal)

    def train_all(self, cycles: int) -> list[TrainingRecord]:
        logger.info("Running %d Codex training cycles", cycles)
        before = len(self._trainer.history)
        self._trainer.train_for_cycles(cycles)
        return list(self._trainer.history[before:])

    def sync_repo(self, message: str) -> None:
        logger.info("Syncing repository with message: %s", message)
        self._trainer.commit(message)
