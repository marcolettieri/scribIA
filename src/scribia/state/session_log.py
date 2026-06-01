from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from ..engine.models import ContextNote

_LOG = Path(".scribia") / "session_log.jsonl"


def append(text: str, source: str = "session", session_id: str = "") -> None:
    """Append a note captured from a Claude Code session."""
    entry = json.dumps(
        {
            "timestamp": datetime.now(UTC).isoformat(),
            "text": text,
            "source": source,
            "session_id": session_id,
        }
    )
    _LOG.parent.mkdir(parents=True, exist_ok=True)
    with _LOG.open("a", encoding="utf-8") as fh:
        fh.write(entry + "\n")


def read_all() -> list[ContextNote]:
    """Return all notes in the session log without clearing it."""
    if not _LOG.exists():
        return []
    notes: list[ContextNote] = []
    for line in _LOG.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
            notes.append(
                ContextNote(
                    timestamp=d["timestamp"],
                    text=d["text"],
                    source=d.get("source", "session"),
                )
            )
        except (json.JSONDecodeError, KeyError):
            continue
    return notes


def clear() -> int:
    """Delete the session log. Returns number of entries that were cleared."""
    if not _LOG.exists():
        return 0
    count = sum(1 for line in _LOG.read_text(encoding="utf-8").splitlines() if line.strip())
    _LOG.unlink()
    return count


def capture_from_hook() -> int:
    """
    Read Claude Code Stop hook JSON from stdin, extract session context,
    and append a summary entry to the session log.

    Hook stdin format:
        {"session_id": "...", "transcript_path": "/path/to/transcript.jsonl", "cwd": "..."}

    Returns number of turns captured (0 if nothing useful found).
    """
    try:
        raw = sys.stdin.read().strip()
        if not raw:
            return 0
        data = json.loads(raw)
    except (json.JSONDecodeError, OSError):
        return 0

    session_id = data.get("session_id", "")
    transcript_path = data.get("transcript_path", "")

    if not transcript_path or not Path(transcript_path).exists():
        return 0

    turns = _extract_turns(Path(transcript_path))
    if not turns:
        return 0

    text = "\n\n".join(turns)
    append(text, source="hook", session_id=session_id)
    return len(turns)


def _extract_turns(transcript: Path) -> list[str]:
    """Extract meaningful text content from the last session in a transcript JSONL."""
    turns: list[str] = []
    try:
        lines = transcript.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []

    # Walk transcript in reverse; collect up to last 20 meaningful turns
    for raw in reversed(lines[-60:]):
        raw = raw.strip()
        if not raw:
            continue
        try:
            entry = json.loads(raw)
        except json.JSONDecodeError:
            continue

        role = entry.get("role") or entry.get("type", "")
        content = entry.get("content") or entry.get("message", {})

        text = _extract_text(content)
        if text and len(text) > 30:
            prefix = "User: " if role == "user" else "Assistant: "
            turns.append(prefix + text[:1000])
            if len(turns) >= 20:
                break

    turns.reverse()
    return turns


def _extract_text(content: object) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(item.get("text", "").strip())
        return " ".join(parts)
    if isinstance(content, dict):
        return _extract_text(content.get("content", ""))
    return ""
