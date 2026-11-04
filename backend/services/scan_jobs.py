"""In-memory registry of running scans, so the client can poll progress.

State lives in this process only. That matches the deployment (one uvicorn
process on Render) and keeps trial results, which are never written to the
database, out of durable storage. Running more than one process/instance
would need a shared store (e.g. Redis) because a poll could land on a
process that doesn't know the scan.
"""
from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

# Pipeline stages, in order. The frontend Loader renders the same list.
STAGES = ("reading", "extracting", "finalizing")

# How long a finished scan's result stays available for polling.
RESULT_TTL_SECONDS = 10 * 60
# Safety net for a scan whose worker thread died without reporting.
MAX_RUNNING_SECONDS = 30 * 60


@dataclass
class Scan:
    id: str
    user_id: str | None
    status: str = "running"  # running | done | error
    stage: str = STAGES[0]
    chunk: int | None = None
    chunks: int | None = None
    result: dict[str, Any] | None = None
    error: dict[str, Any] | None = None  # {"status_code": int, "detail": str | dict}
    created_at: float = field(default_factory=time.monotonic)
    finished_at: float | None = None

    def public(self) -> dict[str, Any]:
        out: dict[str, Any] = {"scan_id": self.id, "status": self.status, "stage": self.stage}
        if self.chunks:
            out["chunk"] = self.chunk
            out["chunks"] = self.chunks
        if self.status == "done":
            out["result"] = self.result
        elif self.status == "error":
            out["error"] = self.error
        return out


_lock = threading.Lock()
_scans: dict[str, Scan] = {}


def _purge_expired(now: float) -> None:
    for scan_id, s in list(_scans.items()):
        if s.finished_at is not None and now - s.finished_at > RESULT_TTL_SECONDS:
            del _scans[scan_id]
        elif s.finished_at is None and now - s.created_at > MAX_RUNNING_SECONDS:
            del _scans[scan_id]


def create_scan(user_id: str | None) -> Scan:
    scan = Scan(id=uuid.uuid4().hex, user_id=user_id)
    with _lock:
        _purge_expired(time.monotonic())
        _scans[scan.id] = scan
    return scan


def get_scan(scan_id: str) -> Scan | None:
    with _lock:
        _purge_expired(time.monotonic())
        return _scans.get(scan_id)


def set_stage(scan_id: str, stage: str, chunk: int | None = None, chunks: int | None = None) -> None:
    with _lock:
        s = _scans.get(scan_id)
        if s and s.status == "running":
            s.stage, s.chunk, s.chunks = stage, chunk, chunks


def finish_scan(scan_id: str, result: dict[str, Any]) -> None:
    with _lock:
        s = _scans.get(scan_id)
        if s:
            s.status, s.result, s.finished_at = "done", result, time.monotonic()


def fail_scan(scan_id: str, status_code: int, detail: Any) -> None:
    with _lock:
        s = _scans.get(scan_id)
        if s:
            s.status, s.finished_at = "error", time.monotonic()
            s.error = {"status_code": status_code, "detail": detail}


def clear_all() -> None:
    """Test helper."""
    with _lock:
        _scans.clear()
