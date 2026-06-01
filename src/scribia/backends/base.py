from __future__ import annotations

from abc import ABC, abstractmethod

from ..engine.models import ChangeSet


class BackendPlugin(ABC):
    """
    Interface every documentation backend must implement.

    Implementations must be registered in backends/loader.py or placed as
    standalone .py files in the project's plugins/ directory.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique backend identifier (lowercase, no spaces, no hyphens)."""

    @abstractmethod
    def init(self, config: dict) -> None:
        """
        Called once before update().
        Create directories, connect to services, validate prerequisites.
        Must be idempotent — safe to call on an already-initialized backend.
        """

    @abstractmethod
    def update(self, changeset: ChangeSet) -> list[str]:
        """
        Apply documentation changes for the given changeset.

        Returns a list of resource identifiers (file paths, URLs, node IDs)
        that were created or updated.
        """

    @abstractmethod
    def persist(self) -> None:
        """
        Flush buffered writes and finalize any pending operations.
        Called once after update() completes.
        """

    def query(self, question: str) -> str:
        """
        Query the knowledge base for a natural-language question.
        Optional — backends that do not support querying raise NotImplementedError.
        """
        raise NotImplementedError(f"Backend '{self.name}' does not implement query().")
