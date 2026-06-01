"""
Example custom backend plugin.

To create your own backend:
1. Copy this file to plugins/your_name.py
2. Set `name` to a unique string matching what you put in scribia.yaml
3. Implement init(), update(), persist()
4. Set `backend: your_name` in scribia.yaml

No changes to scribia core code required.
"""
from __future__ import annotations

from scribia.backends.base import BackendPlugin
from scribia.engine.models import ChangeSet


class ExampleBackend(BackendPlugin):
    name = "example"

    def init(self, config: dict) -> None:
        print("[example] init called — connect to your service here")

    def update(self, changeset: ChangeSet) -> list[str]:
        print(f"[example] update called — {len(changeset.semantic_entities)} entities")
        for entity in changeset.semantic_entities:
            print(f"  {entity.change_type.value}: {entity.name} ({entity.entity_type.value})")
        return []

    def persist(self) -> None:
        print("[example] persist called — flush/commit writes here")

    def query(self, question: str) -> str:
        return f"[example] query not implemented: {question}"
