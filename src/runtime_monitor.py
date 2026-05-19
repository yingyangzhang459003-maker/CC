from __future__ import annotations

import json
import time
import uuid
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import desc, select

from src.database import RuntimeRun, SystemLog


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def write_system_log(session, level: str, module: str, message: str) -> SystemLog:
    entry = SystemLog(level=level.upper(), module=module, message=message, created_at=utc_now_iso())
    session.add(entry)
    session.flush()
    return entry


def record_runtime_run(
    session,
    command: str,
    fn: Callable[[], dict[str, Any]],
) -> dict[str, Any]:
    """Run a callable and persist success/failure metadata in runtime_runs.

    The callable should execute idempotent application logic and return a JSON-serializable
    dictionary. Exceptions are re-raised after being recorded so callers can decide whether
    to back off, retry, or terminate.
    """
    started_at = utc_now_iso()
    monotonic_start = time.monotonic()
    run = RuntimeRun(
        run_id=f"run_{uuid.uuid4().hex[:20]}",
        command=command,
        status="running",
        started_at=started_at,
        finished_at=None,
        duration_seconds=None,
        result_json=None,
        error_message=None,
    )
    session.add(run)
    session.flush()
    try:
        result = fn()
    except Exception as exc:
        finished_at = utc_now_iso()
        run.status = "failed"
        run.finished_at = finished_at
        run.duration_seconds = round(time.monotonic() - monotonic_start, 3)
        run.error_message = f"{type(exc).__name__}: {exc}"
        write_system_log(session, "ERROR", command, run.error_message)
        session.flush()
        raise
    finished_at = utc_now_iso()
    run.status = "success"
    run.finished_at = finished_at
    run.duration_seconds = round(time.monotonic() - monotonic_start, 3)
    run.result_json = json.dumps(result or {}, ensure_ascii=False, sort_keys=True)
    write_system_log(session, "INFO", command, f"completed in {run.duration_seconds}s: {run.result_json}")
    session.flush()
    return result


def latest_runtime_runs(session, limit: int = 10) -> list[dict[str, Any]]:
    rows = session.execute(select(RuntimeRun).order_by(desc(RuntimeRun.started_at)).limit(limit)).scalars().all()
    return [
        {
            "run_id": row.run_id,
            "command": row.command,
            "status": row.status,
            "started_at": row.started_at,
            "finished_at": row.finished_at,
            "duration_seconds": row.duration_seconds,
            "result": json.loads(row.result_json) if row.result_json else None,
            "error_message": row.error_message,
        }
        for row in rows
    ]


def runtime_health(session) -> dict[str, Any]:
    latest = latest_runtime_runs(session, limit=5)
    failed_recently = sum(1 for item in latest if item["status"] == "failed")
    latest_success = next((item for item in latest if item["status"] == "success"), None)
    latest_failure = next((item for item in latest if item["status"] == "failed"), None)
    return {
        "latest_runs": latest,
        "recent_failure_count": failed_recently,
        "latest_success_at": latest_success["finished_at"] if latest_success else None,
        "latest_failure_at": latest_failure["finished_at"] if latest_failure else None,
        "health_status": "degraded" if failed_recently else "ok",
    }
