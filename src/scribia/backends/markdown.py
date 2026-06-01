from __future__ import annotations

from datetime import datetime
from pathlib import Path

from .base import BackendPlugin
from ..engine.models import ChangeSet, ChangeType, EntityType, SemanticEntity
from ..updater.safe_write import SafeWriter


class MarkdownBackend(BackendPlugin):
    """
    Default backend. Writes plain Markdown files into a docs/ directory.
    No external dependencies or build step required.

    Structure produced:
        docs/
          index.md
          api/<module>.md
          features/
          architecture/data-models.md
          configuration.md
        CHANGELOG.md
    """

    name = "markdown"

    def __init__(self) -> None:
        self._docs_dir = Path("docs")
        self._changelog = Path("CHANGELOG.md")
        self._updated: list[str] = []

    def init(self, config: dict) -> None:
        self._docs_dir = Path(config.get("docs_dir", "docs"))
        self._changelog = Path(config.get("changelog", "CHANGELOG.md"))

        for sub in ("api", "features", "architecture"):
            (self._docs_dir / sub).mkdir(parents=True, exist_ok=True)

        index = self._docs_dir / "index.md"
        if not index.exists():
            SafeWriter.write_new(
                index,
                "# Documentation\n\n"
                "- [API Reference](api/)\n"
                "- [Features](features/)\n"
                "- [Architecture](architecture/)\n"
                "- [Configuration](configuration.md)\n"
                "- [Changelog](../CHANGELOG.md)\n",
            )

    def update(self, changeset: ChangeSet) -> list[str]:
        self._updated = []

        by_type: dict[str, list[SemanticEntity]] = {
            "api": [],
            "model": [],
            "config": [],
            "service": [],
        }

        for e in changeset.semantic_entities:
            if e.entity_type in (EntityType.API_ENDPOINT, EntityType.FUNCTION, EntityType.CLASS):
                by_type["api"].append(e)
            elif e.entity_type == EntityType.DATA_MODEL:
                by_type["model"].append(e)
            elif e.entity_type == EntityType.CONFIGURATION:
                by_type["config"].append(e)
            elif e.entity_type == EntityType.SERVICE:
                by_type["service"].append(e)

        if by_type["api"] or by_type["service"]:
            self._update_api_docs(by_type["api"] + by_type["service"], changeset)
        if by_type["model"]:
            self._update_model_docs(by_type["model"], changeset)
        if by_type["config"]:
            self._update_config_docs(by_type["config"])

        self._update_changelog(changeset)

        return self._updated

    def _update_api_docs(self, entities: list[SemanticEntity], changeset: ChangeSet) -> None:
        by_file: dict[str, list[SemanticEntity]] = {}
        for e in entities:
            by_file.setdefault(e.file_path, []).append(e)

        for file_path, file_entities in by_file.items():
            module = Path(file_path).stem
            doc_path = self._docs_dir / "api" / f"{module}.md"
            section = self._render_entity_table(file_entities)
            section_id = f"api-{module}"

            if not SafeWriter.update_section(doc_path, section_id, section):
                header = (
                    f"# API: `{module}`\n\n"
                    f"> Source: `{file_path}`\n\n"
                )
                SafeWriter.write_new(doc_path, header)
                SafeWriter.append_section(doc_path, section_id, section)

            self._updated.append(str(doc_path))

    def _update_model_docs(self, entities: list[SemanticEntity], changeset: ChangeSet) -> None:
        doc_path = self._docs_dir / "architecture" / "data-models.md"
        section = self._render_entity_table(entities)
        if not SafeWriter.update_section(doc_path, "data-models", section):
            SafeWriter.write_new(doc_path, "# Data Models\n\n")
            SafeWriter.append_section(doc_path, "data-models", section)
        self._updated.append(str(doc_path))

    def _update_config_docs(self, entities: list[SemanticEntity]) -> None:
        doc_path = self._docs_dir / "configuration.md"
        section = self._render_entity_table(entities)
        if not SafeWriter.update_section(doc_path, "configuration", section):
            SafeWriter.write_new(doc_path, "# Configuration Reference\n\n")
            SafeWriter.append_section(doc_path, "configuration", section)
        self._updated.append(str(doc_path))

    def _render_entity_table(self, entities: list[SemanticEntity]) -> str:
        lines = [
            "| Name | Type | Change | File |",
            "|------|------|--------|------|",
        ]
        for e in entities:
            icon = "🆕" if e.change_type == ChangeType.ADDED else "✏️"
            lines.append(
                f"| `{e.name}` | {e.entity_type.value} | {icon} {e.change_type.value} | `{e.file_path}` |"
            )
        return "\n".join(lines)

    def _update_changelog(self, changeset: ChangeSet) -> None:
        added = [e for e in changeset.semantic_entities if e.change_type == ChangeType.ADDED]
        modified = [e for e in changeset.semantic_entities if e.change_type == ChangeType.MODIFIED]
        deleted = [e for e in changeset.file_changes if e.change_type == ChangeType.DELETED]

        if not (added or modified or deleted):
            return

        date = datetime.now().strftime("%Y-%m-%d")
        short = changeset.to_commit[:7]
        lines = [f"## [{date}] — `{short}`"]

        if added:
            lines.append("\n### Added")
            for e in added:
                lines.append(f"- `{e.name}` ({e.entity_type.value}) in `{e.file_path}`")
        if modified:
            lines.append("\n### Changed")
            for e in modified:
                lines.append(f"- `{e.name}` updated in `{e.file_path}`")
        if deleted:
            lines.append("\n### Removed")
            for fc in deleted:
                lines.append(f"- `{fc.path}`")

        SafeWriter.prepend_to_changelog(self._changelog, "\n".join(lines))
        self._updated.append(str(self._changelog))

    def persist(self) -> None:
        pass  # All writes are immediate
