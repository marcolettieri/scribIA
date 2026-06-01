from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path

from .models import ChangeSet, ChangeType, FileChange

IGNORED_EXTENSIONS = {".lock", ".sum", ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".woff", ".woff2"}
IGNORED_DIRS = {"node_modules", ".git", "__pycache__", ".venv", "venv", "dist", "build", ".autodoc"}
MAX_DIFF_LINES = 300


class DiffEngine:
    def __init__(self, repo_path: str = "."):
        self.repo_path = Path(repo_path)

    def current_commit(self) -> str:
        return self._run(["git", "rev-parse", "HEAD"]).strip() or "unknown"

    def get_changeset(self, from_commit: str, to_commit: str = "HEAD") -> ChangeSet:
        to = self._run(["git", "rev-parse", to_commit]).strip() or to_commit
        diff_stat = self._run(["git", "diff", "--stat", from_commit, to])
        file_changes = self._collect_file_changes(from_commit, to)

        return ChangeSet(
            from_commit=from_commit,
            to_commit=to,
            timestamp=datetime.now(timezone.utc).isoformat(),
            file_changes=file_changes,
            raw_diff_stat=diff_stat,
        )

    def _collect_file_changes(self, from_commit: str, to_commit: str) -> list[FileChange]:
        name_status = self._run(["git", "diff", "--name-status", from_commit, to_commit])
        num_stat = self._run(["git", "diff", "--numstat", from_commit, to_commit])

        numstat_map: dict[str, tuple[int, int]] = {}
        for line in num_stat.splitlines():
            parts = line.split("\t")
            if len(parts) == 3:
                try:
                    add = int(parts[0]) if parts[0] != "-" else 0
                    delete = int(parts[1]) if parts[1] != "-" else 0
                    numstat_map[parts[2]] = (add, delete)
                except ValueError:
                    pass

        changes: list[FileChange] = []
        for line in name_status.splitlines():
            if not line.strip():
                continue
            parts = line.split("\t")
            status = parts[0][0]

            if status == "A" and len(parts) >= 2:
                path = parts[1]
                if self._should_include(path):
                    add, delete = numstat_map.get(path, (0, 0))
                    changes.append(FileChange(
                        path=path,
                        change_type=ChangeType.ADDED,
                        additions=add,
                        deletions=delete,
                        diff_content=self._get_file_diff(path, from_commit, to_commit),
                    ))

            elif status == "M" and len(parts) >= 2:
                path = parts[1]
                if self._should_include(path):
                    add, delete = numstat_map.get(path, (0, 0))
                    changes.append(FileChange(
                        path=path,
                        change_type=ChangeType.MODIFIED,
                        additions=add,
                        deletions=delete,
                        diff_content=self._get_file_diff(path, from_commit, to_commit),
                    ))

            elif status == "D" and len(parts) >= 2:
                path = parts[1]
                if self._should_include(path):
                    changes.append(FileChange(path=path, change_type=ChangeType.DELETED))

            elif status == "R" and len(parts) >= 3:
                old_path, new_path = parts[1], parts[2]
                if self._should_include(new_path):
                    add, delete = numstat_map.get(new_path, (0, 0))
                    changes.append(FileChange(
                        path=new_path,
                        change_type=ChangeType.RENAMED,
                        old_path=old_path,
                        additions=add,
                        deletions=delete,
                    ))

        return changes

    def _get_file_diff(self, path: str, from_commit: str, to_commit: str) -> str:
        output = self._run(["git", "diff", "-U3", from_commit, to_commit, "--", path])
        lines = output.splitlines()
        if len(lines) > MAX_DIFF_LINES:
            truncated = len(lines) - MAX_DIFF_LINES
            lines = lines[:MAX_DIFF_LINES] + [f"... ({truncated} lines truncated)"]
        return "\n".join(lines)

    def _should_include(self, path: str) -> bool:
        p = Path(path)
        if p.suffix in IGNORED_EXTENSIONS:
            return False
        return not any(part in IGNORED_DIRS for part in p.parts)

    def _run(self, cmd: list[str]) -> str:
        try:
            result = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=30,
            )
            return result.stdout
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return ""
