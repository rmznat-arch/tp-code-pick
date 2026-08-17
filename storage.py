from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
LATEST_PATH = DATA_DIR / "posts.json"
HISTORY_DIR = DATA_DIR / "history"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def save_result(payload: dict[str, Any]) -> None:
    fetched_at = payload.get("fetchedAt") or utc_now().isoformat()
    payload["fetchedAt"] = fetched_at
    # Preserve the last good JSON when a public fetch is blocked or empty.
    if payload.get("posts") or not LATEST_PATH.exists():
        atomic_write_json(LATEST_PATH, payload)
        site_data = ROOT / "site" / "data" / "posts.json"
        site_api = ROOT / "site" / "api" / "posts.json"
        atomic_write_json(site_data, payload)
        atomic_write_json(site_api, payload)


def load_latest() -> dict[str, Any]:
    if not LATEST_PATH.exists():
        return {"runStatus": "not_found", "posts": [], "warnings": ["No fetch has completed yet."]}
    return json.loads(LATEST_PATH.read_text(encoding="utf-8"))
