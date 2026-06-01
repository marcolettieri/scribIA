from __future__ import annotations

from datetime import datetime
from pathlib import Path

from ..engine.models import ChangeSet, ChangeType, SemanticEntity
from ..updater.safe_write import SafeWriter
from .base import BackendPlugin


class LLMWikiBackend(BackendPlugin):
    """
    LLM-readable wiki backend.

    Generates one structured Markdown summary per module under wiki/.
    Designed so that future LLM API calls can read these files for fast
    context retrieval without traversing the full source tree.

    Structure:
        wiki/
          index.md          — list of all modules with one-line summaries
          <module>.md       — per-module entity table + metadata
    """

    name = "llm_wiki"

    def __init__(self) -> None:
        self._output_dir = Path("wiki")
        self._updated: list[str] = []

    def init(self, config: dict) -> None:
        w = config.get("llm_wiki", {})
        self._output_dir = Path(w.get("output_dir", "wiki"))
        self._output_dir.mkdir(parents=True, exist_ok=True)

        index = self._output_dir / "index.md"
        if not index.exists():
            SafeWriter.write_new(
                index,
                "# LLM Wiki Index\n\n"
                "Auto-generated module summaries for LLM context retrieval.\n\n"
                "<!-- autodoc:start:index -->\n"
                "<!-- autodoc:end:index -->\n",
            )

    def update(self, changeset: ChangeSet) -> list[str]:
        self._updated = []
        by_file: dict[str, list[SemanticEntity]] = {}
        for e in changeset.semantic_entities:
            by_file.setdefault(e.file_path, []).append(e)

        index_rows: list[str] = []
        for file_path, entities in by_file.items():
            module = Path(file_path).stem
            wiki_path = self._output_dir / f"{module}.md"
            section_id = f"module-{module}"
            content = self._render_module(file_path, entities, changeset)

            if not SafeWriter.update_section(wiki_path, section_id, content):
                header = f"# Module: `{module}`\n\nSource: `{file_path}`\n\n"
                SafeWriter.write_new(wiki_path, header)
                SafeWriter.append_section(wiki_path, section_id, content)

            self._updated.append(str(wiki_path))
            count = len(entities)
            index_rows.append(f"- [`{module}`]({module}.md) — {count} entities in `{file_path}`")

        if index_rows:
            index_path = self._output_dir / "index.md"
            SafeWriter.update_section(index_path, "index", "\n".join(index_rows))

        return self._updated

    def _render_module(
        self, file_path: str, entities: list[SemanticEntity], changeset: ChangeSet
    ) -> str:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M UTC")
        lines = [
            f"**Updated**: {ts}  ",
            f"**Commit**: `{changeset.to_commit[:7]}`",
            "",
            "| Name | Type | Change |",
            "|------|------|--------|",
        ]
        for e in entities:
            verb = "added" if e.change_type == ChangeType.ADDED else "modified"
            lines.append(f"| `{e.name}` | {e.entity_type.value} | {verb} |")
        lines.append("")
        return "\n".join(lines)

    def persist(self) -> None:
        pass  # Writes are immediate
