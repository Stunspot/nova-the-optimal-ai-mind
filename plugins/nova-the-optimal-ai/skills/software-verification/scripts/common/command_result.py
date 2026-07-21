from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Optional


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class CommandResult:
    format_version: str
    command: list[str]
    working_directory: str
    started_at: str
    finished_at: str
    duration_seconds: float
    exit_code: Optional[int]
    timed_out: bool
    stdout: str
    stderr: str
    status: str

    def to_dict(self):
        return asdict(self)
