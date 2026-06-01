from __future__ import annotations

import re
from pathlib import Path

_START = "<!-- scribia:start:{section} -->"
_END = "<!-- scribia:end:{section} -->"


class SafeWriter:
    """
    All write operations are additive or in-place replacements of named sections.
    Files are never truncated unless a section is explicitly replaced.
    """

    @staticmethod
    def write_new(path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    @staticmethod
    def update_section(path: Path, section: str, new_content: str) -> bool:
        """
        Replace the content between autodoc markers for `section`.
        Returns True if the section existed and was updated, False if not found.
        """
        if not path.exists():
            return False

        existing = path.read_text(encoding="utf-8")
        start_marker = _START.format(section=section)
        end_marker = _END.format(section=section)
        pattern = re.compile(
            re.escape(start_marker) + r".*?" + re.escape(end_marker),
            re.DOTALL,
        )
        replacement = f"{start_marker}\n{new_content.strip()}\n{end_marker}"

        if pattern.search(existing):
            path.write_text(pattern.sub(replacement, existing), encoding="utf-8")
            return True
        return False

    @staticmethod
    def append_section(path: Path, section: str, content: str) -> None:
        """Append a new marked section. Creates file if it does not exist."""
        path.parent.mkdir(parents=True, exist_ok=True)
        start_marker = _START.format(section=section)
        end_marker = _END.format(section=section)
        block = f"\n{start_marker}\n{content.strip()}\n{end_marker}\n"

        if path.exists():
            path.write_text(path.read_text(encoding="utf-8") + block, encoding="utf-8")
        else:
            path.write_text(block, encoding="utf-8")

    @staticmethod
    def prepend_to_changelog(changelog_path: Path, entry: str) -> None:
        """Prepend a changelog entry after the first heading, preserving all existing content."""
        changelog_path.parent.mkdir(parents=True, exist_ok=True)

        if changelog_path.exists():
            lines = changelog_path.read_text(encoding="utf-8").splitlines(keepends=True)
            insert_at = 0
            for i, line in enumerate(lines):
                if line.startswith("# ") or line.startswith("## "):
                    insert_at = i + 1
                    break
            lines.insert(insert_at, "\n" + entry.strip() + "\n\n")
            changelog_path.write_text("".join(lines), encoding="utf-8")
        else:
            changelog_path.write_text(f"# Changelog\n\n{entry.strip()}\n", encoding="utf-8")
