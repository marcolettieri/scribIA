# Changelog

All notable changes to ScribIA will be documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning: [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] — 2026-06-01

### Added
- **Conversational context capture** — Scribia now documents *why* code was built, not just *what* changed
- `scribia note "text"` (Approach A): queue an architectural note from the CLI or Claude Code session; notes are flushed into `docs/decisions/YYYY-MM-DD.md` on the next `scribia run`
- `scribia session show|apply|clear` (Approach B): manage a persistent session log populated by the Stop hook; `apply` pushes captured context into docs and clears the log
- `scribia session capture`: reads Claude Code Stop hook JSON from stdin and appends conversation context to `.scribia/session_log.jsonl`
- `ContextNote` data model: `timestamp`, `text`, `source` (manual/session/hook)
- `ContextQueue` — `.scribia/context_queue.jsonl` for Approach A staging
- `SessionLog` — `.scribia/session_log.jsonl` for Approach B persistence
- Markdown backend now writes `docs/decisions/` with per-day, per-commit sections
- LLM Wiki backend now writes `wiki/decisions.md` with session context
- `/scribia` Claude Code skill: new Step 2.5 auto-extracts architectural insights from the conversation before running the pipeline

## [0.1.0] — 2026-06-01

### Added
- Initial release of ScribIA (Scriba + IA)
- Incremental git-diff-based documentation pipeline
- Semantic entity extraction: APIs, classes, functions, data models, configuration
- Noise filter: ignores comment-only and whitespace-only diffs
- Markdown backend (default): writes `docs/api/`, `docs/architecture/`, `CHANGELOG.md`
- Graphify backend: queues `/graphify --update --wiki` after each run
- LLM Wiki backend: per-module summaries optimised for LLM context retrieval
- Dynamic plugin loader: drop a `.py` file in `plugins/` to add a custom backend
- `BackendPlugin` ABC with `init()`, `update()`, `persist()`, `query()` interface
- Safe write system: section markers (`<!-- scribia:start/end -->`) prevent overwriting unmanaged content
- Checkpoint storage in `.scribia/state.json`
- `scribia hook install/remove/show`: install Claude Code Stop or PostToolUse hooks for automatic runs
- Claude Code skill (`/scribia`) with full pipeline orchestration and graphify auto-invocation
- Interactive `install.sh`: backend selection, knowledge backends, update mode, hook setup
- `scribia.yaml` configuration with deep-merge defaults

[Unreleased]: https://github.com/mlettieri/scribia/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/mlettieri/scribia/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/mlettieri/scribia/releases/tag/v0.1.0
