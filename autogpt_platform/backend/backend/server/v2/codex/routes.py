"""FastAPI routes exposing Codex orchestration functionality."""

from __future__ import annotations

import fastapi

from .agent import NoOpAgentClient
from .schemas import (
    LogResponse,
    RunTaskRequest,
    RunTaskResponse,
    StatusResponse,
    SyncRepoRequest,
    TrainAllRequest,
    TrainAllResponse,
    TrainingRecordModel,
)
from .service import CodexOrchestrationService, DEFAULT_FEATURES, DEFAULT_LAYERS

router = fastapi.APIRouter(prefix="/codex", tags=["codex"])

_service: CodexOrchestrationService | None = None


def _build_default_service() -> CodexOrchestrationService:
    return CodexOrchestrationService(
        layers=DEFAULT_LAYERS,
        features=DEFAULT_FEATURES,
        agent=NoOpAgentClient(),
    )


def get_service() -> CodexOrchestrationService:
    global _service
    if _service is None:
        _service = _build_default_service()
    return _service


@router.post("/run-task", response_model=RunTaskResponse)
def run_task(
    request: RunTaskRequest,
    service: CodexOrchestrationService = fastapi.Depends(get_service),
) -> RunTaskResponse:
    try:
        record = service.run_task(request.layer, request.feature, goal=request.goal)
    except ValueError as exc:
        raise fastapi.HTTPException(status_code=400, detail=str(exc)) from exc
    return RunTaskResponse(record=TrainingRecordModel.from_record(record))


@router.post("/train-all", response_model=TrainAllResponse)
def train_all(
    request: TrainAllRequest,
    service: CodexOrchestrationService = fastapi.Depends(get_service),
) -> TrainAllResponse:
    records = service.train_all(request.cycles)
    return TrainAllResponse(
        cycles=request.cycles,
        records=[TrainingRecordModel.from_record(record) for record in records],
    )


@router.get("/log", response_model=LogResponse)
def get_log(
    service: CodexOrchestrationService = fastapi.Depends(get_service),
) -> LogResponse:
    return LogResponse(
        history=[TrainingRecordModel.from_record(record) for record in service.history]
    )


@router.get("/status", response_model=StatusResponse)
def get_status(
    service: CodexOrchestrationService = fastapi.Depends(get_service),
) -> StatusResponse:
    return StatusResponse(
        layers=list(service.layers),
        features=list(service.features),
        total_runs=len(service.history),
        repo_path=service.repo_path,
    )


@router.post("/sync-repo")
def sync_repo(
    request: SyncRepoRequest,
    service: CodexOrchestrationService = fastapi.Depends(get_service),
) -> dict[str, str]:
    try:
        service.sync_repo(request.message)
    except RuntimeError as exc:
        raise fastapi.HTTPException(status_code=400, detail=str(exc)) from exc
    return {"message": request.message}
