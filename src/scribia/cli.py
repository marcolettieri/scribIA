from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from .backends.loader import list_available, load_backend
from .config import load_config
from .engine.analyzer import SemanticAnalyzer
from .engine.diff import DiffEngine
from .engine.models import ChangeSet
from .state import context_queue as ContextQueue
from .state import session_log as SessionLog
from .state.manager import StateManager

_GRAPHIFY_MARKER = Path(".scribia") / ".run_graphify"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="scribia",
        description="Scribia — incremental AI documentation system (Scriba + IA)",
    )
    sub = parser.add_subparsers(dest="command")

    # -- run (default when no subcommand) --
    run_p = sub.add_parser("run", help="Run the documentation update pipeline")
    run_p.add_argument(
        "--from-commit", metavar="SHA", help="Override start commit (default: last checkpoint)"
    )
    run_p.add_argument(
        "--dry-run", action="store_true", help="Print changeset JSON without writing anything"
    )
    run_p.add_argument(
        "--force", action="store_true", help="Process even if already at latest checkpoint"
    )

    # -- init --
    sub.add_parser("init", help="Scaffold docs structure and set initial checkpoint")

    # -- state --
    state_p = sub.add_parser("state", help="Inspect or reset checkpoint state")
    state_p.add_argument("action", choices=["show", "reset"])

    # -- config --
    sub.add_parser("config", help="Print effective configuration (merged defaults + scribia.yaml)")

    # -- backends --
    sub.add_parser("backends", help="List all discoverable backends")

    # -- note --
    note_p = sub.add_parser(
        "note", help="Queue an architectural note for the next documentation run"
    )
    note_p.add_argument("text", help="The note text to queue")
    note_p.add_argument(
        "--source",
        default="manual",
        help="Source tag stored with the note (default: manual)",
    )

    # -- session --
    session_p = sub.add_parser("session", help="Manage session-captured context notes (Approach B)")
    session_sub = session_p.add_subparsers(dest="session_action")
    session_sub.add_parser("show", help="Print current session log contents")
    session_sub.add_parser(
        "apply",
        help="Process session log as context notes and update docs, then clear the log",
    )
    session_sub.add_parser("clear", help="Clear the session log without processing it")
    session_sub.add_parser(
        "capture",
        help=(
            "Read Claude Code Stop hook JSON from stdin and append session context "
            "to the session log (called automatically by the Stop hook)"
        ),
    )

    # -- hook --
    hook_p = sub.add_parser("hook", help="Install or remove Claude Code automatic hook")
    hook_p.add_argument(
        "action",
        choices=["install", "remove", "show"],
        help=(
            "install: add Stop hook to ~/.claude/settings.json so scribia runs "
            "automatically after each Claude response; "
            "remove: undo; show: print current hook status"
        ),
    )
    hook_p.add_argument(
        "--trigger",
        choices=["stop", "post-edit"],
        default="stop",
        help=(
            "stop (default): run once when Claude finishes responding; "
            "post-edit: run after every file edit/write by Claude"
        ),
    )
    hook_p.add_argument(
        "--global",
        dest="global_settings",
        action="store_true",
        help="Write to ~/.claude/settings.json (user-global) instead of .claude/settings.json (project-local)",
    )

    args = parser.parse_args(argv)

    dispatch = {
        None: lambda: _cmd_run(None, dry_run=False, force=False),
        "run": lambda: _cmd_run(
            args.from_commit if hasattr(args, "from_commit") else None,
            dry_run=getattr(args, "dry_run", False),
            force=getattr(args, "force", False),
        ),
        "init": _cmd_init,
        "state": lambda: _cmd_state(args.action),
        "config": _cmd_config,
        "backends": _cmd_backends,
        "hook": lambda: _cmd_hook(
            args.action,
            trigger=args.trigger,
            global_settings=args.global_settings,
        ),
        "note": lambda: _cmd_note(args.text, args.source),
        "session": lambda: _cmd_session(getattr(args, "session_action", None)),
    }
    return dispatch[args.command]()


# ---------------------------------------------------------------------------
# Subcommand implementations
# ---------------------------------------------------------------------------


def _cmd_run(from_commit_override: str | None, *, dry_run: bool, force: bool) -> int:
    config = load_config()
    state = StateManager()
    diff_engine = DiffEngine()
    analyzer = SemanticAnalyzer()

    to_commit = diff_engine.current_commit()
    from_commit = from_commit_override or state.last_commit()

    if not from_commit:
        print(
            "[scribia] No checkpoint found.\n"
            "         Run `scribia init` first, or use --from-commit <sha>.",
            file=sys.stderr,
        )
        return 1

    if from_commit == to_commit and not force:
        print(f"[scribia] Already up to date at {to_commit[:7]}. Nothing to document.")
        return 0

    print(f"[scribia] Diff range: {from_commit[:7]}..{to_commit[:7]}")

    changeset = diff_engine.get_changeset(from_commit, to_commit)
    if not changeset.has_changes():
        print("[scribia] No file changes in range.")
        _save_checkpoint(state, to_commit, "no changes", config)
        return 0

    sig = changeset.significant_changes()
    print(f"[scribia] {len(changeset.file_changes)} files changed ({len(sig)} significant)")

    changeset = analyzer.analyze(changeset)
    print(f"[scribia] {len(changeset.semantic_entities)} semantic entities extracted")

    # Attach any queued context notes (from `scribia note` calls)
    queued_notes = ContextQueue.read_and_clear()
    if queued_notes:
        changeset.context_notes = queued_notes
        print(f"[scribia] {len(queued_notes)} context note(s) queued")

    if dry_run:
        print("\n[scribia] DRY RUN — changeset:\n")
        print(changeset.to_json())
        return 0

    # Collect active backends (primary + knowledge)
    backend_names: list[str] = [config["backend"]]
    for kb in config.get("knowledge_backends", []):
        if kb and kb not in backend_names:
            backend_names.append(kb)

    all_updated: list[str] = []
    for name in backend_names:
        try:
            backend = load_backend(name)
            backend.init(config)
            print(f"[scribia] Running backend: {name}")
            updated = backend.update(changeset)
            backend.persist()
            all_updated.extend(updated)
        except ValueError as exc:
            print(f"[scribia] Warning: {exc}", file=sys.stderr)

    summary = f"{len(changeset.file_changes)} files, {len(changeset.semantic_entities)} entities"
    _save_checkpoint(state, to_commit, summary, config, backend_names)

    if all_updated:
        print(f"\n[scribia] Updated {len(all_updated)} document(s):")
        for path in all_updated:
            print(f"  {path}")
    else:
        print("\n[scribia] No documentation sections required updating.")

    # Surface graphify invocation if queued
    if _GRAPHIFY_MARKER.exists():
        target, flags = _GRAPHIFY_MARKER.read_text(encoding="utf-8").strip().split("\n", 1)
        _GRAPHIFY_MARKER.unlink(missing_ok=True)
        print(f"\n[scribia] Graphify queued — run in Claude Code:\n  /graphify {target} {flags}")

    return 0


def _cmd_init() -> int:
    config = load_config()
    print("[scribia] Initializing documentation structure...")

    backend_name = config["backend"]
    try:
        backend = load_backend(backend_name)
        backend.init(config)
        print(f"[scribia] Backend '{backend_name}' initialized")
    except ValueError as exc:
        print(f"[scribia] Error: {exc}", file=sys.stderr)
        return 1

    state_dir = Path(".scribia")
    state_dir.mkdir(exist_ok=True)
    gitignore = state_dir / ".gitignore"
    gitignore.write_text(".run_graphify\n", encoding="utf-8")

    # Copy scribia.yaml.example → scribia.yaml if not present
    example = Path(__file__).parent.parent.parent / "scribia.yaml.example"
    if not example.exists():
        example = Path(__file__).parent.parent.parent / "scribia.yaml.example"
    if example.exists() and not Path("scribia.yaml").exists() and not Path("autodoc.yaml").exists():
        shutil.copy(example, "scribia.yaml")
        print("[scribia] Created scribia.yaml from template")

    diff_engine = DiffEngine()
    current = diff_engine.current_commit()
    StateManager().save(current, "Initial checkpoint", {"backends": [backend_name]})
    print(f"[scribia] Checkpoint set to HEAD: {current[:7]}")
    print("[scribia] Ready. Run `scribia run` (or /scribia in Claude Code) to generate docs.")
    return 0


def _cmd_state(action: str) -> int:
    state = StateManager()
    if action == "show":
        print(json.dumps(state.to_dict(), indent=2))
    elif action == "reset":
        current = DiffEngine().current_commit()
        state.reset(current)
        print(f"[scribia] Checkpoint reset to HEAD: {current[:7]}")
    return 0


def _cmd_config() -> int:
    print(json.dumps(load_config(), indent=2))
    return 0


def _cmd_backends() -> int:
    available = list_available()
    print("Available backends:")
    for name, source in available.items():
        print(f"  {name:<16} {source}")
    return 0


def _cmd_hook(action: str, *, trigger: str, global_settings: bool) -> int:
    """Install or remove a Claude Code hook that auto-runs scribia."""
    settings_path = (
        Path.home() / ".claude" / "settings.json"
        if global_settings
        else Path(".claude") / "settings.json"
    )

    # Safe run command: only executes if .scribia/state.json exists in cwd
    guard = "[ -f .scribia/state.json ]"
    run_cmd = f"{guard} && scribia run 2>/dev/null || true"

    if trigger == "stop":
        hook_event = "Stop"
        hook_matcher = ""
    else:  # post-edit
        hook_event = "PostToolUse"
        hook_matcher = "Edit|Write"

    new_hook = {"type": "command", "command": run_cmd}
    new_entry = {"matcher": hook_matcher, "hooks": [new_hook]}

    if action == "show":
        if not settings_path.exists():
            print(f"[scribia] No settings file at {settings_path}")
            return 0
        settings = json.loads(settings_path.read_text(encoding="utf-8"))
        hooks = settings.get("hooks", {}).get(hook_event, [])
        scribia_hooks = [
            h
            for h in hooks
            if any("scribia" in str(sh.get("command", "")) for sh in h.get("hooks", []))
        ]
        if scribia_hooks:
            print(f"[scribia] Hook installed ({hook_event}) in {settings_path}")
        else:
            print(f"[scribia] No hook found in {settings_path}")
        return 0

    # Load or create settings
    if settings_path.exists():
        settings = json.loads(settings_path.read_text(encoding="utf-8"))
    else:
        settings = {}
        settings_path.parent.mkdir(parents=True, exist_ok=True)

    hooks = settings.setdefault("hooks", {})
    event_hooks: list[dict] = hooks.setdefault(hook_event, [])

    # Remove any existing scribia entries first
    event_hooks[:] = [
        h
        for h in event_hooks
        if not any("scribia" in str(sh.get("command", "")) for sh in h.get("hooks", []))
    ]

    if action == "install":
        event_hooks.append(new_entry)
        settings_path.write_text(json.dumps(settings, indent=2), encoding="utf-8")
        scope = "global" if global_settings else "project-local"
        print(f"[scribia] Hook installed ({hook_event}, {scope}): {settings_path}")
        print("[scribia] Scribia will run automatically after each Claude response.")
        if not global_settings:
            print("[scribia] Tip: use --global to apply to all projects.")

    elif action == "remove":
        settings_path.write_text(json.dumps(settings, indent=2), encoding="utf-8")
        print(f"[scribia] Hook removed from {settings_path}")

    return 0


def _cmd_note(text: str, source: str = "manual") -> int:
    """Queue a context note for the next `scribia run`."""
    if not Path(".scribia").exists():
        print(
            "[scribia] No .scribia directory found. Run `scribia init` first.",
            file=sys.stderr,
        )
        return 1
    ContextQueue.append(text, source=source)
    print(f"[scribia] Note queued (will be included in next `scribia run`):\n  {text}")
    return 0


def _cmd_session(action: str | None) -> int:
    """Dispatch session subcommands."""
    if action is None or action == "show":
        return _cmd_session_show()
    if action == "apply":
        return _cmd_session_apply()
    if action == "clear":
        return _cmd_session_clear()
    if action == "capture":
        return _cmd_session_capture()
    print(f"[scribia] Unknown session action: {action}", file=sys.stderr)
    return 1


def _cmd_session_show() -> int:
    notes = SessionLog.read_all()
    if not notes:
        print("[scribia] Session log is empty.")
        return 0
    print(f"[scribia] Session log — {len(notes)} note(s):\n")
    for i, note in enumerate(notes, 1):
        ts = note.timestamp[:16].replace("T", " ")
        print(f"[{i}] ({ts}) [{note.source}]\n{note.text}\n")
    return 0


def _cmd_session_apply() -> int:
    """Process all session log notes into documentation, then clear the log."""
    notes = SessionLog.read_all()
    if not notes:
        print("[scribia] Session log is empty. Nothing to apply.")
        return 0

    config = load_config()
    state = StateManager()
    diff_engine = DiffEngine()

    to_commit = diff_engine.current_commit()
    from_commit = state.last_commit() or to_commit

    import datetime as _dt

    changeset = ChangeSet(
        from_commit=from_commit,
        to_commit=to_commit,
        timestamp=_dt.datetime.now(_dt.UTC).isoformat(),
        context_notes=notes,
    )

    print(f"[scribia] Applying {len(notes)} session note(s) to documentation...")

    backend_names: list[str] = [config["backend"]]
    for kb in config.get("knowledge_backends", []):
        if kb and kb not in backend_names:
            backend_names.append(kb)

    all_updated: list[str] = []
    for name in backend_names:
        try:
            backend = load_backend(name)
            backend.init(config)
            updated = backend.update(changeset)
            backend.persist()
            all_updated.extend(updated)
        except ValueError as exc:
            print(f"[scribia] Warning: {exc}", file=sys.stderr)

    cleared = SessionLog.clear()
    print(f"[scribia] Session log cleared ({cleared} entries).")

    if all_updated:
        print(f"\n[scribia] Updated {len(all_updated)} document(s):")
        for path in all_updated:
            print(f"  {path}")
    else:
        print("\n[scribia] No documentation sections required updating.")

    return 0


def _cmd_session_clear() -> int:
    count = SessionLog.clear()
    if count:
        print(f"[scribia] Session log cleared ({count} entries).")
    else:
        print("[scribia] Session log was already empty.")
    return 0


def _cmd_session_capture() -> int:
    """Called by the Stop hook — reads hook JSON from stdin, writes to session log."""
    count = SessionLog.capture_from_hook()
    if count:
        print(f"[scribia] Session captured ({count} turns → session log).")
    return 0


def _save_checkpoint(
    state: StateManager, commit: str, summary: str, config: dict, backends: list[str] | None = None
) -> None:
    state.save(
        commit=commit,
        summary=summary,
        backend_config={"backends": backends or [config.get("backend", "markdown")]},
    )
