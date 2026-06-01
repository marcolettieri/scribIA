from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from ..engine.models import ContextNote

_QUEUE = Path(".scribia") / "context_queue.jsonl"


def append(text: str, source: str = "manual") -> None:
    """Append a single note to the context queue."""
    entry = json.dumps({"timestamp": datetime.now(UTC).isoformat(), "text": text, "source": source})
    _QUEUE.parent.mkdir(parents=True, exist_ok=True)
    with _QUEUE.open("a", encoding="utf-8") as fh:
        fh.write(entry + "\n")


def read_and_clear() -> list[ContextNote]:
    """Read all queued notes and remove the queue file."""
    if not _QUEUE.exists():
        return []
    notes: list[ContextNote] = []
    for line in _QUEUE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
            notes.append(
                ContextNote(
                    timestamp=d["timestamp"],
                    text=d["text"],
                    source=d.get("source", "manual"),
                )
            )
        except (json.JSONDecodeError, KeyError):
            continue
    _QUEUE.unlink(missing_ok=True)
    return notes
