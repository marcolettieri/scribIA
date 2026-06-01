from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

_STATE_DIR = ".scribia"
_STATE_FILE = "state.json"


class StateManager:
    """
    Manages the local checkpoint stored in .autodoc/state.json.

    The checkpoint records:
    - last processed commit hash   (used as diff start point)
    - timestamp of last run
    - summary of processed changes
    - which backends were active
    - total run count
    """

    def __init__(self, repo_path: str = ".") -> None:
        self._path = Path(repo_path) / _STATE_DIR / _STATE_FILE
        self._state = self._load()

    def _load(self) -> dict:
        if self._path.exists():
            try:
                return json.loads(self._path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                return {}
        return {}

    def last_commit(self) -> str | None:
        return self._state.get("last_commit")

    def save(self, commit: str, summary: str, backend_config: dict) -> None:
        self._state = {
            "last_commit": commit,
            "last_run": datetime.now(timezone.utc).isoformat(),
            "last_summary": summary,
            "backend_config": backend_config,
            "run_count": self._state.get("run_count", 0) + 1,
            "schema_version": 1,
        }
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(self._state, indent=2), encoding="utf-8")

    def reset(self, commit: str) -> None:
        self.save(commit, "Manual reset", self._state.get("backend_config", {}))

    def to_dict(self) -> dict:
        return dict(self._state)
