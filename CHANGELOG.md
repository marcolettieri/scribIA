# Changelog

All notable changes to ScribIA will be documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning: [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/mlettieri/scribia/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/mlettieri/scribia/releases/tag/v0.1.0
