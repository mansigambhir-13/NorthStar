"""REST API routes wrapping PipelineManager."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from northstar.pipeline import PipelineManager

router = APIRouter(prefix="/api")


def _pm() -> PipelineManager:
    return PipelineManager()


class TaskCreate(BaseModel):
    description: str


class TaskStatusUpdate(BaseModel):
    status: str


class ConfigUpdate(BaseModel):
    value: str


class ReportRequest(BaseModel):
    report_type: str = "session"


class InitRequest(BaseModel):
    goals_path: str | None = None


# ── Endpoints ────────────────────────────────────────────────────────


@router.get("/status")
async def get_status() -> dict[str, Any]:
    pm = _pm()
    return await pm.get_status()


@router.post("/analyze")
async def run_analyze() -> dict[str, Any]:
    pm = _pm()
    return await pm.analyze()


@router.get("/check")
async def quick_check() -> dict[str, Any]:
    pm = _pm()
    return await pm.quick_check()


@router.get("/tasks")
async def get_tasks() -> dict[str, Any]:
    pm = _pm()
    return await pm.get_tasks()


@router.post("/tasks")
async def add_task(body: TaskCreate) -> dict[str, Any]:
    pm = _pm()
    return await pm.add_and_rank_task(task_description=body.description)


@router.patch("/tasks/{task_id}")
async def update_task(task_id: str, body: TaskStatusUpdate) -> dict[str, Any]:
    from northstar.analysis.models import TaskStatus
    from northstar.state.manager import StateManager

    valid = {"pending", "in_progress", "completed", "deferred", "cancelled"}
    if body.status not in valid:
        raise HTTPException(400, f"Invalid status. Must be one of: {sorted(valid)}")

    pm = _pm()
    sm = await pm._get_state_manager()
    try:
        await sm.update_task_status(task_id, TaskStatus(body.status))
        return {"success": True, "task_id": task_id, "status": body.status}
    finally:
        await pm._cleanup()


@router.get("/goals")
async def get_goals() -> dict[str, Any]:
    pm = _pm()
    sm = await pm._get_state_manager()
    try:
        ctx = await sm.load_context()
        if ctx is None:
            return {"goals": [], "error": "Not initialized"}
        goals = [
            {
                "id": g.id,
                "title": g.title,
                "description": g.description,
                "priority": g.priority,
                "status": g.status.value,
                "deadline": g.deadline,
            }
            for g in ctx.goals.goals
        ]
        return {"goals": goals}
    finally:
        await pm._cleanup()


@router.get("/pds")
async def get_pds() -> dict[str, Any]:
    pm = _pm()
    sm = await pm._get_state_manager()
    try:
        pds = await sm.get_latest_pds()
        if pds is None:
            return {"score": 0, "severity": "green", "message": "No PDS calculated yet"}
        return {
            "score": round(pds.score, 2),
            "severity": pds.severity,
            "diagnosis": pds.diagnosis,
            "recommendations": pds.recommendations,
        }
    finally:
        await pm._cleanup()


@router.get("/pds/history")
async def get_pds_history() -> dict[str, Any]:
    pm = _pm()
    sm = await pm._get_state_manager()
    try:
        history = await sm.get_pds_history()
        return {
            "history": [
                {
                    "score": round(h.score, 2),
                    "severity": h.severity,
                    "calculated_at": h.calculated_at.isoformat()
                    if hasattr(h.calculated_at, "isoformat")
                    else str(h.calculated_at),
                }
                for h in history
            ]
        }
    finally:
        await pm._cleanup()


@router.get("/decisions")
async def get_decisions(limit: int = 20) -> dict[str, Any]:
    pm = _pm()
    return await pm.get_decisions(limit=limit)


@router.post("/reports/{report_type}")
async def generate_report(report_type: str) -> dict[str, Any]:
    valid = ("session", "weekly", "retro")
    if report_type not in valid:
        raise HTTPException(400, f"Invalid report type. Choose from: {', '.join(valid)}")
    pm = _pm()
    return await pm.generate_report(report_type=report_type)


@router.get("/config")
async def get_config() -> dict[str, Any]:
    pm = _pm()
    return await pm.get_config()


@router.put("/config/{key:path}")
async def set_config(key: str, body: ConfigUpdate) -> dict[str, Any]:
    pm = _pm()
    await pm.set_config(key, body.value)
    return {"success": True, "key": key, "value": body.value}


@router.post("/init")
async def initialize(body: InitRequest | None = None) -> dict[str, Any]:
    from pathlib import Path

    pm = _pm()
    goals_path = Path(body.goals_path) if body and body.goals_path else None
    return await pm.initialize(goals_path=goals_path, interactive=False)
