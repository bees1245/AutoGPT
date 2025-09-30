"""Pydantic schemas for Codex orchestration endpoints."""

from __future__ import annotations

from typing import Iterable

from pydantic import BaseModel, Field, field_validator

from backend.server.training_loop import TrainingRecord


class RunTaskRequest(BaseModel):
    layer: str = Field(..., description="Layer to execute")
    feature: str = Field(..., description="Feature to execute")
    goal: str | None = Field(
        default=None,
        description="Optional override for the agent goal statement.",
    )


class SyncRepoRequest(BaseModel):
    message: str = Field(
        "chore(codex): manual sync",
        description="Commit message for the sync operation.",
    )


class TrainAllRequest(BaseModel):
    cycles: int = Field(
        1,
        ge=1,
        le=100,
        description="Number of full layer/feature cycles to run.",
    )
    layers: list[str] | None = Field(
        default=None,
        min_length=1,
        description=(
            "Optional subset of layers to include. Defaults to all configured layers."
        ),
    )
    features: list[str] | None = Field(
        default=None,
        min_length=1,
        description=(
            "Optional subset of features to include. Defaults to all configured features."
        ),
    )

    @field_validator("layers", "features", mode="before")
    @classmethod
    def _ensure_list(cls, value):  # noqa: D401
        """Allow iterables in addition to concrete lists."""

        if value is None or isinstance(value, list):
            return value
        return list(value)


class TrainingRecordModel(BaseModel):
    layer: str
    feature: str
    goal: str
    success: bool
    summary: str | None
    error: str | None
    timestamp: float

    @classmethod
    def from_record(cls, record: TrainingRecord) -> "TrainingRecordModel":
        return cls(
            layer=record.layer,
            feature=record.feature,
            goal=record.goal,
            success=record.success,
            summary=record.summary,
            error=str(record.error) if record.error else None,
            timestamp=record.timestamp,
        )


class RunTaskResponse(BaseModel):
    record: TrainingRecordModel


class TrainAllResponse(BaseModel):
    cycles: int
    records: list[TrainingRecordModel]


class LogResponse(BaseModel):
    history: list[TrainingRecordModel]


class StatusResponse(BaseModel):
    layers: list[str]
    features: list[str]
    total_runs: int
    repo_path: str | None

    @field_validator("layers", "features", mode="before")
    @classmethod
    def _ensure_list(cls, value: Iterable[str]):  # noqa: D401
        """Convert any iterable into a list for stable responses."""

        return list(value)
