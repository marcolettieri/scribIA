from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


@dataclass
class ContextNote:
    """A human-authored note capturing architectural intent or design rationale."""

    timestamp: str
    text: str
    source: str = "manual"  # "manual" | "session" | "hook"

    def to_dict(self) -> dict[str, Any]:
        return {"timestamp": self.timestamp, "text": self.text, "source": self.source}


class ChangeType(StrEnum):
    ADDED = "added"
    MODIFIED = "modified"
    DELETED = "deleted"
    RENAMED = "renamed"


class EntityType(StrEnum):
    API_ENDPOINT = "api_endpoint"
    SERVICE = "service"
    MODULE = "module"
    DATA_MODEL = "data_model"
    CONFIGURATION = "configuration"
    DEPENDENCY = "dependency"
    FUNCTION = "function"
    CLASS = "class"
    UNKNOWN = "unknown"


@dataclass
class FileChange:
    path: str
    change_type: ChangeType
    old_path: str | None = None
    additions: int = 0
    deletions: int = 0
    diff_content: str = ""

    def is_significant(self) -> bool:
        return self.additions + self.deletions >= 3

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "change_type": self.change_type.value,
            "old_path": self.old_path,
            "additions": self.additions,
            "deletions": self.deletions,
        }


@dataclass
class SemanticEntity:
    name: str
    entity_type: EntityType
    change_type: ChangeType
    file_path: str
    description: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "entity_type": self.entity_type.value,
            "change_type": self.change_type.value,
            "file_path": self.file_path,
            "description": self.description,
            "metadata": self.metadata,
        }


@dataclass
class ChangeSet:
    from_commit: str
    to_commit: str
    timestamp: str
    file_changes: list[FileChange] = field(default_factory=list)
    semantic_entities: list[SemanticEntity] = field(default_factory=list)
    raw_diff_stat: str = ""
    context_notes: list[ContextNote] = field(default_factory=list)

    def has_changes(self) -> bool:
        return bool(self.file_changes)

    def has_content(self) -> bool:
        return bool(self.file_changes or self.context_notes)

    def significant_changes(self) -> list[FileChange]:
        return [f for f in self.file_changes if f.is_significant()]

    def to_dict(self) -> dict[str, Any]:
        return {
            "from_commit": self.from_commit,
            "to_commit": self.to_commit,
            "timestamp": self.timestamp,
            "file_changes": [f.to_dict() for f in self.file_changes],
            "semantic_entities": [e.to_dict() for e in self.semantic_entities],
            "raw_diff_stat": self.raw_diff_stat,
            "context_notes": [n.to_dict() for n in self.context_notes],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)
