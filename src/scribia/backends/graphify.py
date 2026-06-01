from __future__ import annotations

import shutil
from pathlib import Path

from .base import BackendPlugin
from ..engine.models import ChangeSet

_MARKER = Path(".scribia") / ".run_graphify"


class GraphifyBackend(BackendPlugin):
    """
    Graphify knowledge-graph backend.

    Does not call graphify directly during update() — instead it writes a
    marker file that the /scribia skill reads to trigger the graphify
    invocation in the correct Claude Code context.

    If graphify is invoked standalone (no skill), the marker is printed as
    a shell command the user can copy-paste.
    """

    name = "graphify"

    def __init__(self) -> None:
        self._available = False
        self._flags = "--update --wiki --no-viz"
        self._target = "."

    def init(self, config: dict) -> None:
        g = config.get("graphify", {})
        self._flags = g.get("flags", "--update --wiki --no-viz")
        self._target = g.get("target_path", ".")

        skill_path = Path.home() / ".claude" / "skills" / "graphify" / "SKILL.md"
        graphify_bin = shutil.which("graphify")
        self._available = skill_path.exists() or graphify_bin is not None

        if not self._available:
            print("[scribia/graphify] graphify not found — skipping knowledge graph update")

    def update(self, changeset: ChangeSet) -> list[str]:
        if not self._available:
            return []
        return [f"graphify:{self._target}"]

    def persist(self) -> None:
        if not self._available:
            return
        _MARKER.parent.mkdir(parents=True, exist_ok=True)
        _MARKER.write_text(f"{self._target}\n{self._flags}\n", encoding="utf-8")
        print(f"[scribia/graphify] Queued: /graphify {self._target} {self._flags}")

    def query(self, question: str) -> str:
        raise NotImplementedError(
            "Use /graphify query '<question>' directly in Claude Code to query the graph."
        )
