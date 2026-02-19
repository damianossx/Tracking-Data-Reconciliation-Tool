# src/ups_rma_reconciliation/logging_audit.py

"""
Audit & session logging utilities.

Goals:
- Provide a single, centralized audit logger for the whole application.
- Write human-readable logs to a rotating file handler.
- Optionally emit structured (JSON/NDJSON-style) session logs for analysis.

Principles:
- DO NOT hardcode paths; the caller passes a base directory.
- Keep logging setup simple and explicit.
"""

from __future__ import annotations

import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any


DEFAULT_LOG_FILE_NAME = "ups_rma_recon.log"
DEFAULT_SESSION_LOG_PREFIX = "session_"
MAX_BYTES = 1_000_000  # ~1 MB per file
BACKUP_COUNT = 5       # keep last 5 files


def setup_audit_logger(
    name: str = "ups_rma_recon",
    log_dir: Optional[Path] = None,
    level: int = logging.INFO,
) -> logging.Logger:
    """
    Configure and return a global audit logger.

    Parameters
    ----------
    name:
        Logger name to use across the application.
    log_dir:
        Base directory for log files. If None, the current working directory is used.
    level:
        Minimum log level to capture (default: INFO).

    Returns
    -------
    logging.Logger
        Configured logger instance.
    """
    if log_dir is None:
        log_dir = Path.cwd()

    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / DEFAULT_LOG_FILE_NAME

    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Avoid adding duplicate handlers if called multiple times.
    if not logger.handlers:
        handler = RotatingFileHandler(
            log_path, maxBytes=MAX_BYTES, backupCount=BACKUP_COUNT, encoding="utf-8"
        )
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        # Also log to stdout for convenience during development
        console = logging.StreamHandler()
        console.setFormatter(formatter)
        logger.addHandler(console)

    return logger


class SessionLogger:
    """
    Lightweight NDJSON-style session logger.

    For each application run, you can create a new SessionLogger which:
    - writes one JSON object per line,
    - can be inspected later (e.g. in Power BI / pandas),
    - is decoupled from the audit logger.

    Typical usage:
        session_logger = SessionLogger.create(base_dir=Path("logs"))
        session_logger.log("INFO", "Pipeline started", {"context": "CLI"})
        ...
        session_logger.close()
    """

    def __init__(self, file_path: Path, session_id: str) -> None:
        self.file_path = file_path
        self.session_id = session_id
        self._file = self.file_path.open("a", encoding="utf-8")

    @classmethod
    def create(cls, base_dir: Path) -> "SessionLogger":
        """
        Factory method to build a SessionLogger with a timestamp-based session id.

        Parameters
        ----------
        base_dir:
            Directory where session logs should be written.

        Returns
        -------
        SessionLogger
        """
        base_dir.mkdir(parents=True, exist_ok=True)
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = f"{DEFAULT_SESSION_LOG_PREFIX}{session_id}.ndjson"
        file_path = base_dir / file_name
        return cls(file_path=file_path, session_id=session_id)

    def log(
        self,
        level: str,
        message: str,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Write a structured line to the session log.

        Parameters
        ----------
        level:
            Textual level, e.g. 'INFO', 'WARNING', 'ERROR'.
        message:
            Human-readable message.
        extra:
            Optional dictionary with additional context (e.g. file paths, counts).
        """
        record = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "session_id": self.session_id,
            "level": level.upper(),
            "message": message,
        }
        if extra:
            record["extra"] = extra

        json_line = json.dumps(record, ensure_ascii=False)
        self._file.write(json_line + "\n")
        self._file.flush()

    def close(self) -> None:
        """
        Close the underlying file handle.
        """
        try:
            self._file.close()
        except Exception:
            pass